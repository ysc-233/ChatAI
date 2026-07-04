"""Sessions API - CRUD + activate/clear."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import ChatSession, Character, UserPersona, Message, CharacterState, MemorySummary, User, _to_iso
from app.core.auth import get_current_user
from app.core.exceptions import ERR_SESSION_NOT_FOUND, ERR_CHARACTER_NOT_FOUND, SessionNotFound, CharacterNotFound, PersonaNotFound
from app.core.logging import logger, LogCategory

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.get("")
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    include_character: int = Query(1),
    include_persona: int = Query(1),
    include_last_message: int = Query(0),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Get session list."""
    query = select(ChatSession).where(ChatSession.user_id == current_user.id).order_by(desc(ChatSession.updated_at))
    count_result = await db.execute(
        select(func.count()).select_from(ChatSession).where(ChatSession.user_id == current_user.id)
    )
    total = count_result.scalar() or 0
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = []
    for row in result.scalars().all():
        item = row.to_dict(include_character=bool(include_character), include_persona=bool(include_persona))
        if include_last_message:
            # 查询最后一条消息
            msg_result = await db.execute(
                select(Message)
                .where(Message.session_id == row.id)
                .order_by(desc(Message.created_at))
                .limit(1)
            )
            last_msg = msg_result.scalar_one_or_none()
            if last_msg:
                item["last_message"] = last_msg.content
                item["last_message_time"] = _to_iso(last_msg.created_at)
            else:
                item["last_message"] = None
                item["last_message_time"] = None
        items.append(item)
    return {"code": 0, "message": "success", "data": {"items": items, "total": total, "page": page, "page_size": page_size}}


@router.get("/by_character/{character_id}")
async def get_or_create_session_by_character(
    character_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get or create session by character_id (1:1 mapping)."""
    # Find the most recent session for this character AND this user
    result = await db.execute(
        select(ChatSession)
        .where(
            ChatSession.character_id == character_id,
            ChatSession.user_id == current_user.id,  # Bug fix: was missing user_id filter
        )
        .order_by(desc(ChatSession.updated_at))
        .limit(1)
    )
    session = result.scalar_one_or_none()
    if session:
        return {"code": 0, "message": "success", "data": session.to_dict(include_character=True, include_persona=True)}

    # Get character - must be accessible to user (own or system)
    char_result = await db.execute(select(Character).where(Character.id == character_id))
    char = char_result.scalar_one_or_none()
    if not char:
        raise CharacterNotFound()
    if char.user_id != current_user.id:
        raise HTTPException(status_code=403, detail={
            "code": 40306, "message": "无权使用此角色", "data": None
        })

    # Get default persona for this user
    persona_result = await db.execute(
        select(UserPersona).where(
            UserPersona.is_default == 1,
            UserPersona.user_id == current_user.id
        )
    )
    default_persona = persona_result.scalars().first()

    # Create new session
    new_session = ChatSession(
        name=f"与 {char.name} 的对话",
        character_id=character_id,
        user_persona_id=default_persona.id if default_persona else 1,
        user_id=current_user.id,
        is_active=0
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    logger.info(LogCategory.API, f"Created session by character {character_id}", {"session_id": new_session.id})
    return {"code": 0, "message": "success", "data": new_session.to_dict(include_character=True, include_persona=True)}


@router.get("/active")
async def get_active_session(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get currently active session."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.is_active == 1,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        return {"code": 0, "message": "success", "data": None}
    return {"code": 0, "message": "success", "data": session.to_dict(include_character=True, include_persona=True)}


@router.get("/{id}")
async def get_session(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get session detail."""
    result = await db.execute(select(ChatSession).where(ChatSession.id == id))
    session = result.scalar_one_or_none()
    if not session:
        raise SessionNotFound()
    if session.user_id is not None and session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail={
            "code": 40306, "message": "无权访问此会话", "data": None
        })
    return {"code": 0, "message": "success", "data": session.to_dict(include_character=True, include_persona=True)}


@router.post("")
async def create_session(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create new session with character + persona pair."""
    character_id = data.get("character_id")
    if not character_id:
        raise HTTPException(status_code=400, detail={"code": 40000, "message": "character_id 不能为空", "data": None})

    char_result = await db.execute(select(Character).where(Character.id == character_id))
    char = char_result.scalar_one_or_none()
    if not char:
        raise CharacterNotFound()
    if char.user_id != current_user.id:
        raise HTTPException(status_code=403, detail={
            "code": 40306, "message": "无权使用此角色", "data": None
        })

    user_persona_id = data.get("user_persona_id")
    persona_name = "你自己"
    if user_persona_id:
        persona_result = await db.execute(select(UserPersona).where(UserPersona.id == user_persona_id))
        persona = persona_result.scalar_one_or_none()
        if not persona:
            raise PersonaNotFound()
        persona_name = persona.name
    else:
        # Use default persona for this user
        persona_result = await db.execute(
            select(UserPersona).where(
                UserPersona.is_default == 1,
                UserPersona.user_id == current_user.id
            )
        )
        default_persona = persona_result.scalars().first()
        if default_persona:
            user_persona_id = default_persona.id
            persona_name = default_persona.name

    # Auto name
    name = data.get("name")
    if not name:
        name = f"{persona_name} 与 {char.name} 的对话"

    session = ChatSession(
        name=name,
        character_id=character_id,
        user_persona_id=user_persona_id,
        user_id=current_user.id,
        is_active=0,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    logger.info(LogCategory.API, f"Created session {session.id}", {"name": name})
    return {"code": 0, "message": "success", "data": session.to_dict(include_character=True, include_persona=True)}


@router.put("/{id}")
async def update_session(
    id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update session (name, character_id, user_persona_id)."""
    result = await db.execute(select(ChatSession).where(ChatSession.id == id))
    session = result.scalar_one_or_none()
    if not session:
        raise SessionNotFound()
    if session.user_id is not None and session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail={
            "code": 40306, "message": "无权修改此会话", "data": None
        })

    role_changed = False
    if "character_id" in data and data["character_id"] != session.character_id:
        new_char = (await db.execute(
            select(Character).where(Character.id == data["character_id"])
        )).scalar_one_or_none()
        if not new_char:
            raise CharacterNotFound()
        if new_char.user_id != current_user.id:
            raise HTTPException(status_code=403, detail={
                "code": 40306, "message": "无权使用此角色", "data": None
            })
        session.character_id = data["character_id"]
        role_changed = True
    if "user_persona_id" in data and data["user_persona_id"] != session.user_persona_id:
        persona_result = await db.execute(select(UserPersona).where(UserPersona.id == data["user_persona_id"]))
        if not persona_result.scalar_one_or_none():
            raise PersonaNotFound()
        session.user_persona_id = data["user_persona_id"]
        role_changed = True
    if "name" in data:
        session.name = data["name"]

    if role_changed:
        # Clear messages
        await db.execute(delete(Message).where(Message.session_id == id))
        session.message_count = 0

    await db.commit()
    await db.refresh(session)
    return {"code": 0, "message": "success", "data": {**session.to_dict(), "history_cleared": role_changed}}


@router.delete("/{id}")
async def delete_session(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete session and cascade messages, memories, states."""
    result = await db.execute(select(ChatSession).where(ChatSession.id == id))
    session = result.scalar_one_or_none()
    if not session:
        raise SessionNotFound()
    if session.user_id is not None and session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail={
            "code": 40306, "message": "无权删除此会话", "data": None
        })

    # Cascade count
    msg_result = await db.execute(select(func.count()).select_from(Message).where(Message.session_id == id))
    msg_count = msg_result.scalar() or 0
    summary_result = await db.execute(select(func.count()).select_from(MemorySummary).where(MemorySummary.session_id == id))
    summary_count = summary_result.scalar() or 0

    await db.execute(delete(Message).where(Message.session_id == id))
    await db.execute(delete(CharacterState).where(CharacterState.session_id == id))
    await db.execute(delete(MemorySummary).where(MemorySummary.session_id == id))
    await db.delete(session)
    await db.commit()

    return {"code": 0, "message": "success", "data": {"deleted_id": id, "cascade_deleted": {"messages": msg_count, "memories": summary_count, "summaries": summary_count}}}


@router.put("/{id}/activate")
async def activate_session(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Activate session (set as current)."""
    result = await db.execute(select(ChatSession).where(ChatSession.id == id))
    session = result.scalar_one_or_none()
    if not session:
        raise SessionNotFound()
    if session.user_id is not None and session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail={
            "code": 40306, "message": "无权操作此会话", "data": None
        })
    # Deactivate all sessions for this user only (bug fix: was global)
    await db.execute(
        update(ChatSession).values(is_active=0)
        .where(ChatSession.user_id == current_user.id)
    )
    session.is_active = 1
    await db.commit()
    return {"code": 0, "message": "success", "data": {"id": id, "is_active": 1}}


@router.post("/{id}/clear")
async def clear_session(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Clear all messages in session."""
    result = await db.execute(select(ChatSession).where(ChatSession.id == id))
    session = result.scalar_one_or_none()
    if not session:
        raise SessionNotFound()
    if session.user_id is not None and session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail={
            "code": 40306, "message": "无权操作此会话", "data": None
        })

    msg_result = await db.execute(select(func.count()).select_from(Message).where(Message.session_id == id))
    cleared = msg_result.scalar() or 0
    await db.execute(delete(Message).where(Message.session_id == id))
    session.message_count = 0
    await db.commit()
    return {"code": 0, "message": "success", "data": {"session_id": id, "cleared_messages": cleared}}
