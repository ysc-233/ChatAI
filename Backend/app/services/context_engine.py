"""Context Engine - assemble 5-layer prompt with token budget."""
import json
from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta

from app.config import get_settings
from app.core.logging import logger, LogCategory

settings = get_settings()

# Beijing timezone
_BEIJING_TZ = timezone(timedelta(hours=8))
_WEEKDAY_NAMES = ['一', '二', '三', '四', '五', '六', '日']


def _parse_utc_to_beijing(iso_str: Optional[str]) -> Optional[datetime]:
    """Parse an ISO 8601 datetime string to a Beijing-timezone datetime.

    Handles:
      - UTC strings ending with 'Z'    (from DB: "2026-07-04T02:09:00Z")
      - UTC strings with '+00:00'      (normalized form)
      - Offset strings                  (from frontend: "2026-07-04T10:09:00+08:00")

    Returns None on empty / unparseable input.
    """
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        return dt.astimezone(_BEIJING_TZ)
    except (ValueError, TypeError):
        return None


def _fmt_beijing(dt: datetime) -> str:
    """Format a Beijing datetime for the system prompt header."""
    return (
        f"{dt.strftime('%Y年%m月%d日 %H:%M')}"
        f"（周{_WEEKDAY_NAMES[dt.weekday()]}，北京时间）"
    )


class ContextEngine:
    """Build context from 5 layers: user persona, character, state, memory, history."""

    def __init__(self):
        self._memory_engine = None  # Lazy init

    def _get_memory_engine(self):
        """Lazy-init memory engine to avoid import cycles."""
        if self._memory_engine is None:
            from app.services.memory_engine import MemoryEngine
            self._memory_engine = MemoryEngine()
        return self._memory_engine

    @staticmethod
    def _safe_json(value, default=None):
        """Safely parse a JSON string or return the value as-is if already parsed.
        
        Handles: None, already-parsed dict/list, valid JSON string, invalid JSON string.
        Never raises — returns default on parse failure.
        """
        if value is None:
            return default
        if isinstance(value, (dict, list)):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return default
        return default

    async def build_prompt(self, session, user_message: str, history: List[Dict],
                           search_results: Optional[str] = None,
                           client_time: Optional[str] = None) -> List[Dict]:
        """Build OpenAI-style messages list.

        Args:
            client_time: ISO 8601 string from the frontend representing the
                user's local time when they sent the message (eg. "2026-07-04T10:09:00+08:00").
                When provided, this is used as 【当前时间】 for the character.
        """
        system_parts = []

        # Layer -1: Session time context
        # Priority: frontend client_time > history[-1].created_at > server wall clock
        now = datetime.now(_BEIJING_TZ)  # last-resort fallback
        if client_time:
            msg_time = _parse_utc_to_beijing(client_time)
            if msg_time:
                now = msg_time
        elif history:
            msg_time = _parse_utc_to_beijing(history[-1].get("created_at"))
            if msg_time:
                now = msg_time
        system_parts.append(f"【当前时间】{_fmt_beijing(now)}")

        # Layer 0: User persona
        if session.user_persona:
            persona = session.user_persona
            system_parts.append(self._user_persona_prompt(persona))

        # Layer 1: Character card
        if session.character:
            char = session.character
            system_parts.append(self._character_prompt(char))

        # Layer 2: Dynamic state
        system_parts.append(self._state_prompt(session))

        # Layer 3: Long-term memory (vector recall from Qdrant)
        memory_text = await self._build_memory_prompt(session, user_message)
        if memory_text:
            system_parts.append(memory_text)

        # Layer 3.5: Search results (injected when character has search enabled)
        if search_results:
            system_parts.append(search_results)

        system_content = "\n\n".join(system_parts)

        messages = [{"role": "system", "content": system_content}]

        # Layer 4: Recent history (raw content, no timestamps)
        # Exclude the last entry if it duplicates the current user message
        history_msgs = history[-settings.RECENT_HISTORY_ROUNDS:]
        if history_msgs:
            last = history_msgs[-1]
            if last["role"] == "user" and last.get("content", "") == user_message:
                history_msgs = history_msgs[:-1]
        for msg in history_msgs:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Current user message
        messages.append({"role": "user", "content": user_message})
        return messages

    def _user_persona_prompt(self, persona) -> str:
        parts = ["【用户身份设定】"]
        parts.append(f"当前用户的名字是：{persona.name}")
        if persona.background:
            parts.append(f"背景：{persona.background}")
        if persona.personality:
            personality = self._safe_json(persona.personality, [])
            parts.append(f"性格：{', '.join(personality) if isinstance(personality, list) else personality}")
        if persona.speaking_style:
            parts.append(f"说话风格：{persona.speaking_style}")
        parts.append("请根据以上设定，以这个角色身份来进行对话。")
        return "\n".join(parts)

    def _character_prompt(self, char) -> str:
        parts = [f"【角色设定 - {char.name}】"]
        if char.background:
            parts.append(f"背景：{char.background}")
        if char.appearance:
            parts.append(f"外貌：{char.appearance}")
        if char.personality:
            personality = self._safe_json(char.personality, [])
            parts.append(f"性格：{', '.join(personality) if isinstance(personality, list) else personality}")
        if char.speaking_style:
            parts.append(f"说话风格：{char.speaking_style}")
        if char.emotional_triggers:
            triggers = self._safe_json(char.emotional_triggers, {})
            parts.append(f"情感触发：{json.dumps(triggers, ensure_ascii=False)}")
        if char.taboos:
            taboos = self._safe_json(char.taboos, [])
            parts.append(f"禁忌话题：{', '.join(taboos) if isinstance(taboos, list) else taboos}")
        if char.examples:
            examples = self._safe_json(char.examples, [])
            if examples:
                parts.append("示例对话：")
                for ex in examples[:3]:
                    parts.append(f"  用户：{ex.get('user', '')}")
                    parts.append(f"  {char.name}：{ex.get('assistant', '')}")
        if char.world_setting:
            parts.append(f"世界观：{char.world_setting}")
        return "\n".join(parts)

    def _state_prompt(self, session) -> str:
        """Build character state prompt from character_states table."""
        parts = ["【角色状态】"]
        # Try to get real state from the session's states relationship
        if hasattr(session, 'states') and session.states:
            state = session.states[0] if isinstance(session.states, list) else session.states
            parts.append(f"当前心情：{state.mood or '平静'}")
            parts.append(f"好感度：{state.affection or 50}/100")
            if state.state_json:
                extra = self._safe_json(state.state_json, {})
                if isinstance(extra, dict):
                    for k, v in extra.items():
                        parts.append(f"{k}：{v}")
        else:
            parts.append("当前心情：平静")
            parts.append("好感度：50/100")
        return "\n".join(parts)

    async def _build_memory_prompt(self, session, user_message: str) -> Optional[str]:
        """Layer 3: Recall relevant long-term memories from Qdrant."""
        try:
            engine = self._get_memory_engine()
            character_id = session.character_id if hasattr(session, 'character_id') else session.character.id
            user_persona_id = session.user_persona_id if hasattr(session, 'user_persona_id') else (
                session.user_persona.id if session.user_persona else None
            )

            memories = await engine.recall(
                query=user_message,
                character_id=character_id,
                user_persona_id=user_persona_id,
            )

            if memories:
                lines = ["【长期记忆】以下是你对该用户的已知信息："]
                for m in memories:
                    icon = {"fact": "📌", "preference": "💚", "event": "📅"}.get(
                        m.get("memory_type", "fact"), "📌"
                    )
                    lines.append(f"{icon} {m['content']}")
                return "\n".join(lines)
            return None
        except Exception as e:
            logger.warning(LogCategory.MEMORY, f"Memory recall skipped: {e}")
            return None
