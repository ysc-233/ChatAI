"""Characters API - CRUD + avatar for AI conversation roles."""
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query
from sqlalchemy import select, desc, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Character, ChatSession, Message, CharacterState, User, safe_json_dump
from app.core.auth import get_current_user
from app.core.exceptions import (
    ERR_BAD_REQUEST,
    ERR_CHARACTER_NAME_REQUIRED,
    ERR_CHARACTER_BACKGROUND_REQUIRED,
    ERR_CHARACTER_PERSONALITY_REQUIRED,
    ERR_CHARACTER_NOT_FOUND,
    ERR_SYSTEM_CHARACTER_UNDELETABLE,
    ERR_SYSTEM_CHARACTER_IMMUTABLE,
    ERR_FORBIDDEN,
    ERR_AVATAR_TYPE_UNSUPPORTED,
    ERR_AVATAR_SIZE_EXCEEDED,
    ERR_AVATAR_INVALID_IMAGE,
    CharacterNotFound,
)
from app.core.logging import logger, LogCategory
from app.config import get_settings, AVATARS_DIR

router = APIRouter(prefix="/characters", tags=["Characters"])
settings = get_settings()


def validate_character_data(data: dict, is_create: bool = True):
    """Validate character data."""
    if is_create and not data.get("name"):
        raise HTTPException(status_code=400, detail={"code": ERR_CHARACTER_NAME_REQUIRED, "message": "角色名称不能为空", "data": None})
    if is_create and not data.get("background"):
        raise HTTPException(status_code=400, detail={"code": ERR_CHARACTER_BACKGROUND_REQUIRED, "message": "角色背景故事不能为空", "data": None})
    if is_create and not data.get("personality"):
        raise HTTPException(status_code=400, detail={"code": ERR_CHARACTER_PERSONALITY_REQUIRED, "message": "性格特征至少填写一项", "data": None})
    if data.get("personality") and not isinstance(data.get("personality"), list):
        raise HTTPException(status_code=400, detail={"code": ERR_BAD_REQUEST, "message": "personality 必须是数组", "data": None})


@router.get("")
async def list_characters(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    keyword: Optional[str] = Query(None),
    is_default: Optional[int] = Query(None),
    include_system: int = Query(1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
):
    """Get character list with pagination and search."""
    query = select(Character).where(Character.user_id == current_user.id)
    if not include_system:
        query = query.where(Character.is_system == 0)
    if keyword:
        query = query.where(
            (Character.name.ilike(f"%{keyword}%")) | (Character.nickname.ilike(f"%{keyword}%"))
        )
    if is_default is not None:
        query = query.where(Character.is_default == is_default)

    # Count
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    # Sort
    sort_col = getattr(Character, sort_by, Character.created_at)
    if sort_order == "desc":
        sort_col = desc(sort_col)
    query = query.order_by(sort_col).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    items = [row.to_dict(full=False) for row in result.scalars().all()]

    return {"code": 0, "message": "success", "data": {"items": items, "total": total, "page": page, "page_size": page_size}}


@router.get("/default")
async def get_default_character(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get default character, or the first one if none is set."""
    result = await db.execute(
        select(Character).where(
            Character.is_default == 1,
            Character.user_id == current_user.id,
        )
    )
    char = result.scalar_one_or_none()
    if not char:
        result = await db.execute(
            select(Character).where(
                Character.user_id == current_user.id
            ).order_by(Character.sort_order, Character.id).limit(1)
        )
        char = result.scalar_one_or_none()
    if not char:
        raise CharacterNotFound()
    return {"code": 0, "message": "success", "data": char.to_dict(full=True)}


@router.get("/{id}")
async def get_character(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get character detail."""
    result = await db.execute(select(Character).where(Character.id == id))
    char = result.scalar_one_or_none()
    if not char:
        raise CharacterNotFound()
    if char.user_id != current_user.id:
        raise HTTPException(status_code=403, detail={"code": ERR_FORBIDDEN, "message": "无权访问此角色", "data": None})
    return {"code": 0, "message": "success", "data": char.to_dict(full=True)}


@router.post("")
async def create_character(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new character."""
    validate_character_data(data, is_create=True)
    char = Character(
        name=data.get("name"),
        nickname=data.get("nickname"),
        age=data.get("age"),
        gender=data.get("gender"),
        appearance=data.get("appearance"),
        background=data.get("background"),
        personality=safe_json_dump(data.get("personality")),
        speaking_style=data.get("speaking_style"),
        emotional_triggers=safe_json_dump(data.get("emotional_triggers")),
        taboos=safe_json_dump(data.get("taboos")),
        examples=safe_json_dump(data.get("examples")),
        world_setting=data.get("world_setting"),
        search_enabled=data.get("search_enabled", 0),
        initial_mood=data.get("initial_mood", "平静"),
        initial_affection=data.get("initial_affection", 50),
        sort_order=data.get("sort_order", 0),
        user_id=current_user.id,
    )
    db.add(char)
    await db.commit()
    await db.refresh(char)
    logger.info(LogCategory.API, f"Created character {char.id}", {"name": char.name})
    return {"code": 0, "message": "success", "data": char.to_dict(full=False)}


@router.put("/{id}")
async def update_character(
    id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update character."""
    result = await db.execute(select(Character).where(Character.id == id))
    char = result.scalar_one_or_none()
    if not char:
        raise CharacterNotFound()
    # Permission: system character can be modified, only owner-protected
    if char.user_id != current_user.id:
        raise HTTPException(status_code=403, detail={
            "code": ERR_FORBIDDEN, "message": "无权修改此角色", "data": None
        })

    validate_character_data(data, is_create=False)
    update_fields = {
        "name": data.get("name"),
        "nickname": data.get("nickname"),
        "age": data.get("age"),
        "gender": data.get("gender"),
        "appearance": data.get("appearance"),
        "background": data.get("background"),
        "personality": safe_json_dump(data.get("personality")),
        "speaking_style": data.get("speaking_style"),
        "emotional_triggers": safe_json_dump(data.get("emotional_triggers")),
        "taboos": safe_json_dump(data.get("taboos")),
        "examples": safe_json_dump(data.get("examples")),
        "world_setting": data.get("world_setting"),
        "search_enabled": data.get("search_enabled"),
        "initial_mood": data.get("initial_mood"),
        "initial_affection": data.get("initial_affection"),
        "sort_order": data.get("sort_order"),
    }
    for key, value in update_fields.items():
        if value is not None or key in data:
            setattr(char, key, value)
    await db.commit()
    await db.refresh(char)
    logger.info(LogCategory.API, f"Updated character {id}", {"name": char.name})
    return {"code": 0, "message": "success", "data": char.to_dict(full=False)}


@router.delete("/{id}")
async def delete_character(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete character and cascade related data."""
    result = await db.execute(select(Character).where(Character.id == id))
    char = result.scalar_one_or_none()
    if not char:
        raise CharacterNotFound()
    if char.is_system:
        raise HTTPException(status_code=403, detail={"code": ERR_SYSTEM_CHARACTER_UNDELETABLE, "message": "系统角色不可删除", "data": None})
    if char.user_id != current_user.id:
        raise HTTPException(status_code=403, detail={
            "code": ERR_FORBIDDEN, "message": "无权删除此角色", "data": None
        })

    # Cascade delete
    sessions_result = await db.execute(select(ChatSession).where(ChatSession.character_id == id))
    sessions = sessions_result.scalars().all()
    cascade = {"sessions": 0, "messages": 0, "memories": 0}
    for session in sessions:
        # Count messages
        msg_result = await db.execute(select(func.count()).select_from(Message).where(Message.session_id == session.id))
        cascade["messages"] += msg_result.scalar() or 0
        # Delete messages
        await db.execute(Message.__table__.delete().where(Message.session_id == session.id))
        # Delete states
        await db.execute(CharacterState.__table__.delete().where(CharacterState.session_id == session.id))
        # Delete session
        await db.delete(session)
        cascade["sessions"] += 1

    await db.delete(char)
    await db.commit()

    # Cascade delete Qdrant memories (non-blocking on failure)
    try:
        from app.services.vector_store import QdrantStore
        store = QdrantStore()
        qdrant_count = await store.delete_by_character(id)
        cascade["qdrant_memories"] = qdrant_count
    except Exception:
        cascade["qdrant_memories"] = 0

    logger.info(LogCategory.API, f"Deleted character {id}", cascade)
    return {"code": 0, "message": "success", "data": {"deleted_id": id, "cascade_deleted": cascade}}


@router.put("/{id}/default")
async def set_default_character(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set character as default."""
    result = await db.execute(select(Character).where(Character.id == id))
    char = result.scalar_one_or_none()
    if not char:
        raise CharacterNotFound()
    # Permission check
    if char.user_id != current_user.id:
        raise HTTPException(status_code=403, detail={
            "code": ERR_FORBIDDEN, "message": "无权操作此角色", "data": None
        })
    # Clear other defaults only for this user's characters
    await db.execute(
        update(Character).values(is_default=0)
        .where(Character.user_id == current_user.id)
    )
    char.is_default = 1
    await db.commit()
    return {"code": 0, "message": "success", "data": {"id": id, "is_default": 1}}


@router.post("/{id}/avatar")
async def upload_avatar(
    id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload character avatar."""
    result = await db.execute(select(Character).where(Character.id == id))
    char = result.scalar_one_or_none()
    if not char:
        raise CharacterNotFound()
    if char.user_id != current_user.id:
        raise HTTPException(status_code=403, detail={
            "code": ERR_FORBIDDEN, "message": "无权操作此角色", "data": None
        })

    # Validate
    if file.content_type not in settings.AVATAR_ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail={"code": ERR_AVATAR_TYPE_UNSUPPORTED, "message": "头像文件类型不支持", "data": None})
    content = await file.read()
    if len(content) > settings.AVATAR_MAX_SIZE * 1024 * 1024:
        raise HTTPException(status_code=413, detail={"code": ERR_AVATAR_SIZE_EXCEEDED, "message": "头像文件超过 5MB", "data": None})

    # Save
    import os
    ext = os.path.splitext(file.filename or ".png")[1] or ".png"
    save_dir = AVATARS_DIR / "characters"
    save_dir.mkdir(parents=True, exist_ok=True)
    filepath = save_dir / f"{id}{ext}"
    with open(filepath, "wb") as f:
        f.write(content)
    # 加时间戳防浏览器缓存
    import time
    avatar_url = f"/avatars/characters/{id}{ext}?t={int(time.time())}"
    char.avatar = avatar_url
    await db.commit()

    # 安全守卫：确保角色头像不会意外出现在 persona 目录
    import shutil
    persona_file = AVATARS_DIR / "personas" / f"{id}{ext}"
    if persona_file.exists():
        persona_file.unlink()
        logger.warning(LogCategory.API, f"Cleaned stray persona avatar for character {id}")

    return {"code": 0, "message": "success", "data": {"avatar_url": avatar_url}}


@router.delete("/{id}/avatar")
async def delete_avatar(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete character avatar."""
    result = await db.execute(select(Character).where(Character.id == id))
    char = result.scalar_one_or_none()
    if not char:
        raise CharacterNotFound()
    if char.user_id != current_user.id:
        raise HTTPException(status_code=403, detail={
            "code": ERR_FORBIDDEN, "message": "无权操作此角色", "data": None
        })
    char.avatar = None
    await db.commit()
    return {"code": 0, "message": "success", "data": None}


@router.post("/{id}/clear-memories")
async def clear_character_memories(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Clear all long-term memories for a character (Qdrant vector store)."""
    result = await db.execute(select(Character).where(Character.id == id))
    char = result.scalar_one_or_none()
    if not char:
        raise CharacterNotFound()
    if char.user_id != current_user.id:
        raise HTTPException(status_code=403, detail={
            "code": ERR_FORBIDDEN, "message": "无权操作此角色", "data": None
        })

    try:
        from app.services.vector_store import QdrantStore
        store = QdrantStore()
        count = await store.delete_by_character(id)
        logger.info(
            LogCategory.API,
            f"Cleared {count} memories for character {id}",
            {"character_id": id, "name": char.name}
        )
        return {"code": 0, "message": "success", "data": {"deleted_count": count}}
    except Exception as e:
        logger.error(LogCategory.API, f"Failed to clear memories for character {id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={"code": "memory_clear_failed", "message": f"清除记忆失败: {str(e)}", "data": None}
        )
