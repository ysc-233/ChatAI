"""WebSocket chat endpoint."""
import json
import time
import asyncio
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.db.models import Message, ChatSession, Character, UserPersona, CharacterState, User
from app.core.auth import verify_ws_token
from app.core.logging import logger, LogCategory
from app.config import get_settings

# SQLAlchemy eager loading for relationships
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/ws", tags=["WebSocket"])
settings = get_settings()

# Active connections manager
active_connections: Dict[int, Set[WebSocket]] = {}
# Per-connection user mapping: {websocket_id: user_id}
connection_users: Dict[int, int] = {}
_ws_id_counter = 0


class ConnectionManager:
    """Manage WebSocket connections per session."""

    def _get_ws_id(self, websocket: WebSocket) -> int:
        """Get or assign a unique ID for a websocket connection."""
        global _ws_id_counter
        if not hasattr(websocket, '_ws_uid'):
            _ws_id_counter += 1
            websocket._ws_uid = _ws_id_counter
        return websocket._ws_uid

    async def connect(self, session_id: int, websocket: WebSocket, user_id: int | None = None):
        await websocket.accept()
        if session_id not in active_connections:
            active_connections[session_id] = set()
        active_connections[session_id].add(websocket)
        if user_id is not None:
            ws_id = self._get_ws_id(websocket)
            connection_users[ws_id] = user_id
        logger.websocket_event("connected", session_id, {"client": str(websocket.client)})

    def disconnect(self, session_id: int, websocket: WebSocket):
        if session_id in active_connections:
            active_connections[session_id].discard(websocket)
            if not active_connections[session_id]:
                del active_connections[session_id]
        logger.websocket_event("disconnected", session_id)

    async def send_to_session(self, session_id: int, message: dict):
        """Send message to all clients in a session."""
        if session_id not in active_connections:
            return
        disconnected = set()
        for ws in active_connections[session_id]:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.add(ws)
        for ws in disconnected:
            active_connections[session_id].discard(ws)


manager = ConnectionManager()


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        return session


@router.websocket("/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: int):
    """WebSocket chat endpoint."""
    await manager.connect(session_id, websocket)
    authenticated = False
    ws_user_id = None
    current_message_id = None
    stop_requested = False

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "auth":
                token = data.get("token")
                if not token:
                    await websocket.send_json({"type": "error", "error": "认证失败：缺少 token", "code": "auth_failed"})
                    await websocket.close()
                    break

                async with AsyncSessionLocal() as db:
                    user = await verify_ws_token(token, db)
                    if user:
                        authenticated = True
                        ws_user_id = user.id
                        # Verify session ownership
                        session = (await db.execute(select(ChatSession).where(ChatSession.id == session_id))).scalar_one_or_none()
                        if session and session.user_id is not None and session.user_id != user.id:
                            await websocket.send_json({"type": "error", "error": "无权访问此会话", "code": "forbidden"})
                            logger.security_event("ws_session_forbidden", str(websocket.client), {"session_id": session_id, "user_id": user.id})
                            await websocket.close()
                            break
                        await websocket.send_json({"type": "auth_success", "message": "认证成功"})
                        logger.websocket_event("auth_success", session_id, {"user_id": user.id})
                        continue
                    else:
                        await websocket.send_json({"type": "error", "error": "认证失败：Token 无效", "code": "auth_failed"})
                        logger.security_event("auth_failed", str(websocket.client), {"session_id": session_id})
                        await websocket.close()
                        break
                continue

            if not authenticated:
                await websocket.send_json({"type": "error", "error": "未认证", "code": "auth_failed"})
                continue

            if msg_type == "chat":
                content = data.get("content", "").strip()
                if not content:
                    await websocket.send_json({"type": "error", "error": "消息内容不能为空", "code": "empty_message"})
                    continue
                if len(content) > 4000:
                    await websocket.send_json({"type": "error", "error": "消息内容超过 4000 字符", "code": "message_too_long"})
                    continue

                stop_requested = False
                msg_id = data.get("message_id")
                client_time = data.get("client_time")

                # Save user message
                async with AsyncSessionLocal() as db:
                    user_msg = Message(
                        session_id=session_id,
                        role="user",
                        content=content,
                        parent_message_id=msg_id,
                    )
                    db.add(user_msg)
                    await db.commit()
                    await db.refresh(user_msg)
                    current_message_id = user_msg.id

                    # Update session message count
                    session = (await db.execute(select(ChatSession).where(ChatSession.id == session_id))).scalar_one_or_none()
                    if session:
                        session.message_count = (session.message_count or 0) + 1
                        # Auto-set user_id if session has none (legacy compatibility)
                        if session.user_id is None and ws_user_id is not None:
                            session.user_id = ws_user_id
                        await db.commit()

                # Echo user message to all clients (optional)
                await manager.send_to_session(session_id, {
                    "type": "user_message",
                    "message_id": current_message_id,
                    "content": content,
                })

                # Generate LLM response (async)
                asyncio.create_task(generate_llm_response(session_id, current_message_id, content, websocket, msg_id, client_time))

            elif msg_type == "stop":
                stop_requested = True
                await manager.send_to_session(session_id, {"type": "stop_ack", "message_id": current_message_id})

    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)
    except Exception as e:
        logger.error(LogCategory.WEBSOCKET, f"WebSocket error: {e}", {"session_id": session_id})
        manager.disconnect(session_id, websocket)


async def generate_llm_response(session_id: int, user_message_id: int, content: str, websocket: WebSocket, regenerate_msg_id: int = None, client_time: str = None):
    """Generate LLM response (non-streaming) and send to client."""
    from app.services.llm_adapter import LLMAdapter

    start_time = time.time()
    adapter = LLMAdapter()
    assistant_msg_id = None

    async with AsyncSessionLocal() as db:
        # Get session context with eager-loaded relationships
        session = (await db.execute(
            select(ChatSession)
            .options(
                selectinload(ChatSession.character),
                selectinload(ChatSession.user_persona),
                selectinload(ChatSession.states),
            )
            .where(ChatSession.id == session_id)
        )).unique().scalar_one_or_none()
        if not session:
            await manager.send_to_session(session_id, {
                "type": "error",
                "error": "会话不存在",
                "code": "invalid_session"
            })
            return

        # Get recent history
        history_result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id, Message.role != "system")
            .order_by(desc(Message.created_at))
            .limit(20)
        )
        history = [row.to_dict() for row in history_result.scalars().all()]
        history.reverse()

        # Create assistant message placeholder
        assistant_msg = Message(
            session_id=session_id,
            role="assistant",
            content="",
            parent_message_id=regenerate_msg_id or user_message_id,
        )
        db.add(assistant_msg)
        await db.commit()
        await db.refresh(assistant_msg)
        assistant_msg_id = assistant_msg.id

    # Notify frontend that LLM is generating
    await manager.send_to_session(session_id, {
        "type": "typing",
        "message_id": assistant_msg_id,
    })

    # === Search flow (if character has search enabled) ===
    search_results_text = None
    if session.character and getattr(session.character, 'search_enabled', 0) == 1:
        try:
            char_brief = (
                f"{session.character.name}，"
                f"{session.character.background or ''}"
            )[:200]
            need_search, query = await adapter.judge_search_intent(
                content, char_brief
            )
            if need_search and query:
                logger.info(
                    LogCategory.LLM,
                    f"Search triggered: \"{query[:50]}\" for session {session_id}"
                )
                # Notify frontend search started
                await manager.send_to_session(session_id, {
                    "type": "search_status",
                    "status": "searching",
                    "query": query,
                })

                from app.services.search_service import SearchService
                searcher = SearchService()
                results = await searcher.search(query)

                if results:
                    search_results_text = searcher.format_for_llm(results)
                    await manager.send_to_session(session_id, {
                        "type": "search_status",
                        "status": "done",
                        "count": len(results),
                    })
                else:
                    await manager.send_to_session(session_id, {
                        "type": "search_status",
                        "status": "empty",
                    })
        except Exception as e:
            logger.warning(
                LogCategory.LLM,
                f"Search failed (fallback to normal chat): {e}"
            )
            await manager.send_to_session(session_id, {
                "type": "search_status",
                "status": "error",
            })

    try:
        # Wait for full LLM response (non-streaming)
        full_content = await adapter.complete_chat(
            session, content, history,
            search_results=search_results_text,
            client_time=client_time
        )

        if not active_connections.get(session_id):
            return

        # Send complete message at once
        await manager.send_to_session(session_id, {
            "type": "message",
            "message_id": assistant_msg_id,
            "content": full_content,
            "role": "assistant",
        })

        # Update message content in DB
        async with AsyncSessionLocal() as db:
            msg = (await db.execute(select(Message).where(Message.id == assistant_msg_id))).scalar_one_or_none()
            if msg:
                msg.content = full_content
                msg.token_count = len(full_content) // 2
                await db.commit()

        # Fire-and-forget: extract memories from this exchange
        _schedule_memory_extraction(session_id, session, content, full_content, history)

        # Fire-and-forget: update affection based on conversation
        _schedule_affection_update(session_id, session, content, full_content)

        duration = (time.time() - start_time) * 1000
        logger.llm_call(
            model=settings.LLM_MODEL_NAME,
            prompt_tokens=len(content) // 2,
            completion_tokens=len(full_content) // 2,
            duration_ms=duration,
            success=True,
        )

    except Exception as e:
        logger.error(LogCategory.LLM, f"LLM generation failed: {e}", {"session_id": session_id})
        await manager.send_to_session(session_id, {
            "type": "error",
            "error": f"LLM API 调用失败: {str(e)}",
            "code": "llm_error",
            "message_id": assistant_msg_id,
        })


def _schedule_memory_extraction(session_id: int, session, user_content: str, assistant_content: str, history: list):
    """Fire-and-forget memory extraction from the latest exchange.
    
    Runs as a background task so it never blocks the chat response.
    """
    async def _do_extract():
        try:
            from app.services.memory_engine import MemoryEngine

            # Collect recent dialogue context for extraction
            dialogue = []
            for m in history[-4:]:  # Last 4 messages of history
                dialogue.append({"role": m.get("role"), "content": m.get("content", "")[:500]})
            dialogue.append({"role": "user", "content": user_content[:500]})
            dialogue.append({"role": "assistant", "content": assistant_content[:500]})

            engine = MemoryEngine()
            count = await engine.extract(
                dialogue=dialogue,
                character_id=session.character_id,
                user_persona_id=session.user_persona_id,
                session_id=session_id,
            )
            if count > 0:
                logger.info(
                    LogCategory.MEMORY,
                    f"Background memory extraction: {count} facts stored for session {session_id}"
                )
        except Exception as e:
            logger.debug(LogCategory.MEMORY, f"Background memory extraction skipped: {e}")

    asyncio.create_task(_do_extract())


AFFECTION_ANALYSIS_PROMPT = """根据以下对话，分析用户的行为对角色的好感度影响。返回 JSON 格式。

角色设定：{character_brief}

对话内容：
用户：{user_msg}
角色：{assistant_msg}

请判断用户在这轮对话中的言行，返回 JSON：
{{"delta": 整数, "reason": "简短原因"}}

规则：
- delta 范围 -5 到 +5
- 用户关心/夸奖/温暖/逗笑角色 → +1~5
- 用户冷漠/冒犯/挖苦/伤害角色 → -1~5  
- 普通闲聊/事实询问 → 0
- 请站在角色的立场，考虑角色性格和情感触发点

只输出 JSON，不要其他内容。"""


def _schedule_affection_update(session_id: int, session, user_content: str, assistant_content: str):
    """Fire-and-forget: analyze conversation and update character affection.

    Runs as a background task so it never blocks the chat response.
    """
    async def _do_update():
        try:
            from app.services.llm_adapter import LLMAdapter
            from app.services.character_service import CharacterService

            # Build character brief for context
            char = session.character
            char_brief = f"{char.name}"
            if char.personality:
                try:
                    import json as _json
                    p = _json.loads(char.personality) if isinstance(char.personality, str) else char.personality
                    char_brief += f"，性格：{', '.join(p) if isinstance(p, list) else p}"
                except Exception:
                    pass
            if char.emotional_triggers:
                try:
                    import json as _json
                    t = _json.loads(char.emotional_triggers) if isinstance(char.emotional_triggers, str) else char.emotional_triggers
                    if isinstance(t, dict):
                        triggers_text = '；'.join(f'{k}:{v}' for k, v in t.items())
                        char_brief += f"。情感触发：{triggers_text}"
                except Exception:
                    pass

            prompt = AFFECTION_ANALYSIS_PROMPT.format(
                character_brief=char_brief[:400],
                user_msg=user_content[:300],
                assistant_msg=assistant_content[:300],
            )

            adapter = LLMAdapter()
            raw = await adapter.cheap_completion(prompt, max_tokens=100)
            if not raw:
                return

            import json as _json
            raw = raw.strip()
            if raw.startswith('```'):
                raw = raw.split('\n', 1)[-1].rsplit('```', 1)[0] if '```' in raw[3:] else raw[3:]
            result = _json.loads(raw)
            delta = int(result.get('delta', 0))
            reason = result.get('reason', '')

            if delta == 0:
                return

            # Update state in DB
            db = AsyncSessionLocal()
            try:
                state = await CharacterService.update_state(
                    db,
                    character_id=session.character_id,
                    user_persona_id=session.user_persona_id,
                    user_id=session.user_id,
                    affection_delta=delta,
                )
                await db.commit()

                old_affection = state.affection - delta
                old_affection = max(0, min(100, old_affection))

                logger.info(
                    LogCategory.SYSTEM,
                    f"Affection update: {old_affection} → {state.affection} "
                    f"(delta={delta:+d}) reason={reason}",
                    {"session_id": session_id}
                )

                # Notify frontend
                await manager.send_to_session(session_id, {
                    "type": "affection_update",
                    "old_value": old_affection,
                    "new_value": state.affection,
                    "delta": delta,
                    "reason": reason,
                })
            finally:
                await db.close()

        except Exception as e:
            logger.debug(LogCategory.SYSTEM, f"Affection update skipped: {e}")

    asyncio.create_task(_do_update())
