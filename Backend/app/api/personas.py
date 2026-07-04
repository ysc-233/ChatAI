"""Personas API - CRUD + avatar for user roles."""
import os
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy import select, desc, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import UserPersona, ChatSession, User, safe_json_dump
from app.core.auth import get_current_user
from app.core.exceptions import (
    ERR_PERSONA_NOT_FOUND,
    ERR_DEFAULT_PERSONA_NAME_IMMUTABLE,
    ERR_DEFAULT_PERSONA_UNDELETABLE,
    PersonaNotFound,
)
from app.core.logging import logger, LogCategory
from app.config import get_settings, AVATARS_DIR

router = APIRouter(prefix="/personas", tags=["Personas"])
settings = get_settings()


@router.get("")
async def list_personas(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    keyword: Optional[str] = Query(None),
    is_default: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
):
    """Get user persona list."""
    query = select(UserPersona).where(UserPersona.user_id == current_user.id)
    if keyword:
        query = query.where(UserPersona.name.ilike(f"%{keyword}%"))
    if is_default is not None:
        query = query.where(UserPersona.is_default == is_default)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    sort_col = getattr(UserPersona, sort_by, UserPersona.created_at)
    if sort_order == "desc":
        sort_col = desc(sort_col)
    query = query.order_by(sort_col).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    items = [row.to_dict(full=False) for row in result.scalars().all()]
    return {"code": 0, "message": "success", "data": {"items": items, "total": total, "page": page, "page_size": page_size}}


@router.get("/default")
async def get_default_persona(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get default user persona."""
    result = await db.execute(
        select(UserPersona).where(
            UserPersona.is_default == 1,
            UserPersona.user_id == current_user.id,
        )
    )
    persona = result.scalar_one_or_none()
    if not persona:
        result = await db.execute(
            select(UserPersona).where(
                UserPersona.user_id == current_user.id
            ).order_by(UserPersona.id).limit(1)
        )
        persona = result.scalar_one_or_none()
    if not persona:
        raise PersonaNotFound()
    return {"code": 0, "message": "success", "data": persona.to_dict(full=True)}


@router.get("/{id}")
async def get_persona(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user persona detail."""
    result = await db.execute(select(UserPersona).where(UserPersona.id == id))
    persona = result.scalar_one_or_none()
    if not persona:
        raise PersonaNotFound()
    if persona.user_id != current_user.id:
        raise HTTPException(status_code=403, detail={
            "code": 40306, "message": "无权访问此身份", "data": None
        })
    return {"code": 0, "message": "success", "data": persona.to_dict(full=True)}


@router.post("")
async def create_persona(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create user persona."""
    if not data.get("name"):
        raise HTTPException(status_code=400, detail={"code": 40001, "message": "角色名称不能为空", "data": None})

    persona = UserPersona(
        name=data.get("name"),
        description=data.get("description"),
        background=data.get("background"),
        personality=safe_json_dump(data.get("personality")),
        speaking_style=data.get("speaking_style"),
        sort_order=data.get("sort_order", 0),
        user_id=current_user.id,
    )
    db.add(persona)
    await db.commit()
    await db.refresh(persona)
    logger.info(LogCategory.API, f"Created persona {persona.id}", {"name": persona.name})
    return {"code": 0, "message": "success", "data": persona.to_dict(full=False)}


@router.put("/{id}")
async def update_persona(
    id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update user persona."""
    result = await db.execute(select(UserPersona).where(UserPersona.id == id))
    persona = result.scalar_one_or_none()
    if not persona:
        raise PersonaNotFound()
    if persona.user_id != current_user.id:
        raise HTTPException(status_code=403, detail={
            "code": 40306, "message": "无权修改此身份", "data": None
        })

    fields = {
        "name": data.get("name"),
        "description": data.get("description"),
        "background": data.get("background"),
        "personality": safe_json_dump(data.get("personality")),
        "speaking_style": data.get("speaking_style"),
        "sort_order": data.get("sort_order"),
    }
    for key, value in fields.items():
        if value is not None or key in data:
            setattr(persona, key, value)
    await db.commit()
    await db.refresh(persona)
    return {"code": 0, "message": "success", "data": persona.to_dict(full=False)}


@router.delete("/{id}")
async def delete_persona(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete user persona. System personas cannot be deleted."""
    result = await db.execute(select(UserPersona).where(UserPersona.id == id))
    persona = result.scalar_one_or_none()
    if not persona:
        raise PersonaNotFound()
    if persona.user_id != current_user.id:
        raise HTTPException(status_code=403, detail={
            "code": 40306, "message": "无权删除此身份", "data": None
        })
    # Cascade: update sessions to use a user-owned persona or NULL
    fallback = (await db.execute(
        select(UserPersona).where(UserPersona.user_id == current_user.id).limit(1)
    )).scalar_one_or_none()
    fallback_id = fallback.id if fallback else None
    await db.execute(
        update(ChatSession).where(ChatSession.user_persona_id == id).values(user_persona_id=fallback_id)
    )
    await db.delete(persona)
    await db.commit()
    logger.info(LogCategory.API, f"Deleted persona {id}")
    return {"code": 0, "message": "success", "data": {"deleted_id": id}}


@router.put("/{id}/default")
async def set_default_persona(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set default user persona."""
    result = await db.execute(select(UserPersona).where(UserPersona.id == id))
    persona = result.scalar_one_or_none()
    if not persona:
        raise PersonaNotFound()
    if persona.user_id != current_user.id:
        raise HTTPException(status_code=403, detail={
            "code": 40306, "message": "无权操作此身份", "data": None
        })
    # Clear defaults only for this user
    await db.execute(
        update(UserPersona).values(is_default=0)
        .where(UserPersona.user_id == current_user.id)
    )
    persona.is_default = 1
    await db.commit()
    return {"code": 0, "message": "success", "data": {"id": id, "is_default": 1}}


@router.post("/{id}/avatar")
async def upload_persona_avatar(
    id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload persona avatar."""
    result = await db.execute(select(UserPersona).where(UserPersona.id == id))
    persona = result.scalar_one_or_none()
    if not persona:
        raise PersonaNotFound()
    if persona.user_id != current_user.id:
        raise HTTPException(status_code=403, detail={
            "code": 40306, "message": "无权操作此身份", "data": None
        })
    if file.content_type not in settings.AVATAR_ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail={"code": 40005, "message": "头像文件类型不支持", "data": None})
    content = await file.read()
    if len(content) > settings.AVATAR_MAX_SIZE * 1024 * 1024:
        raise HTTPException(status_code=413, detail={"code": 40006, "message": "头像文件超过 5MB", "data": None})

    ext = os.path.splitext(file.filename or ".png")[1] or ".png"
    save_dir = AVATARS_DIR / "personas"
    save_dir.mkdir(parents=True, exist_ok=True)
    filepath = save_dir / f"{id}{ext}"
    with open(filepath, "wb") as f:
        f.write(content)
    import time
    avatar_url = f"/avatars/personas/{id}{ext}?t={int(time.time())}"
    persona.avatar = avatar_url
    await db.commit()
    return {"code": 0, "message": "success", "data": {"avatar_url": avatar_url}}


@router.delete("/{id}/avatar")
async def delete_persona_avatar(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete persona avatar."""
    result = await db.execute(select(UserPersona).where(UserPersona.id == id))
    persona = result.scalar_one_or_none()
    if not persona:
        raise PersonaNotFound()
    if persona.user_id != current_user.id:
        raise HTTPException(status_code=403, detail={
            "code": 40306, "message": "无权操作此身份", "data": None
        })
    persona.avatar = None
    await db.commit()
    return {"code": 0, "message": "success", "data": None}
