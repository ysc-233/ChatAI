"""Logs API - Query and manage system logs (新增 log 模块)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.logging import LogLevel, LogCategory, logger
from app.services.log_service import LogService

router = APIRouter(prefix="/logs", tags=["Logs"])


@router.get("")
async def get_logs(
    level: Optional[str] = Query(None, description="Filter by log level: DEBUG, INFO, WARNING, ERROR, CRITICAL"),
    category: Optional[str] = Query(None, description="Filter by category: system, api, websocket, llm, memory, database, security"),
    start_time: Optional[str] = Query(None, description="Start time (ISO 8601)"),
    end_time: Optional[str] = Query(None, description="End time (ISO 8601)"),
    keyword: Optional[str] = Query(None, description="Search keyword in message or source"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Query system logs with filters and pagination.

    **权限**: 需要 API Key 认证。

    **示例**:
    - `GET /api/logs?level=ERROR&page=1`
    - `GET /api/logs?category=api&start_time=2024-06-20T00:00:00Z`
    - `GET /api/logs?keyword=timeout`
    """
    data = await LogService.get_logs(
        db=db,
        level=level,
        category=category,
        start_time=start_time,
        end_time=end_time,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return {"code": 0, "message": "success", "data": data}


@router.get("/levels")
async def get_log_levels():
    """Get all supported log levels and categories.

    Returns available filtering options for the log query API.
    """
    return {
        "code": 0,
        "message": "success",
        "data": {
            "levels": [e.value for e in LogLevel],
            "categories": [e.value for e in LogCategory],
        }
    }


@router.get("/statistics")
async def get_log_statistics(
    days: int = Query(7, ge=1, le=90, description="Statistics period in days"),
    db: AsyncSession = Depends(get_db),
):
    """Get log statistics for dashboard.

    Returns aggregated statistics including:
    - Total log count in the period
    - Error count
    - Distribution by level and category
    - Daily trend
    """
    data = await LogService.get_log_statistics(db, days=days)
    return {"code": 0, "message": "success", "data": data}


@router.post("")
async def create_log(
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """Manually write a log entry (for frontend or external systems).

    **请求体**:
    ```json
    {
        "level": "INFO",
        "category": "system",
        "message": "User performed action",
        "details": {"action": "logout", "user_id": 1}
    }
    ```
    """
    level = data.get("level", "INFO").upper()
    category = data.get("category", "system").lower()
    message = data.get("message", "")
    details = data.get("details")
    source = data.get("source", "api.manual")

    if level not in LogService.VALID_LEVELS:
        raise HTTPException(status_code=400, detail={"code": 40000, "message": f"Invalid level: {level}", "data": None})
    if category not in LogService.VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail={"code": 40000, "message": f"Invalid category: {category}", "data": None})
    if not message:
        raise HTTPException(status_code=400, detail={"code": 40000, "message": "Message is required", "data": None})

    log_entry = await LogService.create_log(
        db=db,
        level=level,
        category=category,
        message=message,
        details=details,
        source=source,
    )
    logger.info(LogCategory.SYSTEM, f"Manual log entry created: {log_entry.id}", {"message": message})
    return {"code": 0, "message": "success", "data": log_entry.to_dict()}


@router.delete("/cleanup")
async def cleanup_logs(
    retention_days: int = Query(30, ge=1, le=365, description="Keep logs newer than this many days"),
    db: AsyncSession = Depends(get_db),
):
    """Clean up old log entries.

    **警告**: 此操作不可恢复。建议定期执行（如通过 cron 任务）。
    """
    from app.config import get_settings
    settings = get_settings()
    deleted = await LogService.cleanup_old_logs(db, retention_days=retention_days)
    return {
        "code": 0,
        "message": "success",
        "data": {"deleted": deleted, "retention_days": retention_days}
    }
