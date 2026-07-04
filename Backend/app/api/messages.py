"""Messages API - history query."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Message, ChatSession, User
from app.core.auth import get_current_user
from app.core.exceptions import SessionNotFound
from app.core.logging import logger, LogCategory

router = APIRouter(prefix="/messages", tags=["Messages"])


@router.get("")
async def get_messages(
    session_id: int = Query(..., description="Session ID"),
    limit: int = Query(50, ge=1, le=100),
    before_id: Optional[int] = Query(None),
    after_id: Optional[int] = Query(None),
    include_system: int = Query(0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get message history for a session."""
    # Verify session exists AND belongs to current user (no legacy null bypass)
    session_result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise SessionNotFound()

    query = select(Message).where(Message.session_id == session_id)
    if not include_system:
        query = query.where(Message.role != "system")
    if before_id:
        query = query.where(Message.id < before_id)
    if after_id:
        query = query.where(Message.id > after_id)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    query = query.order_by(desc(Message.created_at)).limit(limit)
    result = await db.execute(query)
    items = [row.to_dict() for row in result.scalars().all()]
    items.reverse()  # Oldest first

    has_more = len(items) < total if not after_id else (total > len(items))

    return {"code": 0, "message": "success", "data": {"items": items, "has_more": has_more, "total": total}}
