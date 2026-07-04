"""Log service - business logic for log module."""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy import select, desc, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SystemLog
from app.core.logging import logger, LogCategory


class LogService:
    """Service for querying and managing system logs."""

    VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    VALID_CATEGORIES = {"system", "api", "websocket", "llm", "memory", "database", "security"}

    @staticmethod
    async def get_logs(
        db: AsyncSession,
        level: Optional[str] = None,
        category: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """Query logs with filters and pagination."""
        query = select(SystemLog)

        if level and level.upper() in LogService.VALID_LEVELS:
            query = query.where(SystemLog.level == level.upper())
        if category and category.lower() in LogService.VALID_CATEGORIES:
            query = query.where(SystemLog.category == category.lower())
        if start_time:
            try:
                dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                query = query.where(SystemLog.created_at >= dt)
            except ValueError:
                pass
        if end_time:
            try:
                dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                query = query.where(SystemLog.created_at <= dt)
            except ValueError:
                pass
        if keyword:
            query = query.where(
                or_(
                    SystemLog.message.ilike(f"%{keyword}%"),
                    SystemLog.source.ilike(f"%{keyword}%"),
                )
            )

        # Total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Pagination
        offset = (page - 1) * page_size
        query = query.order_by(desc(SystemLog.created_at)).offset(offset).limit(page_size)
        result = await db.execute(query)
        items = [row.to_dict() for row in result.scalars().all()]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    @staticmethod
    async def create_log(
        db: AsyncSession,
        level: str,
        category: str,
        message: str,
        details: Optional[Dict] = None,
        source: Optional[str] = None,
    ) -> SystemLog:
        """Manually create a log entry."""
        log_entry = SystemLog(
            level=level.upper(),
            category=category.lower(),
            message=message,
            details=details,
            source=source or "api",
        )
        db.add(log_entry)
        await db.commit()
        await db.refresh(log_entry)
        return log_entry

    @staticmethod
    async def get_log_statistics(db: AsyncSession, days: int = 7) -> Dict[str, Any]:
        """Get log statistics for dashboard."""
        from sqlalchemy import select, func, and_, text
        from datetime import datetime, timedelta

        start = datetime.utcnow() - timedelta(days=days)

        # Count by level
        level_query = (
            select(SystemLog.level, func.count().label("count"))
            .where(SystemLog.created_at >= start)
            .group_by(SystemLog.level)
        )
        level_result = await db.execute(level_query)
        level_stats = {row[0]: row[1] for row in level_result.all()}

        # Count by category
        cat_query = (
            select(SystemLog.category, func.count().label("count"))
            .where(SystemLog.created_at >= start)
            .group_by(SystemLog.category)
        )
        cat_result = await db.execute(cat_query)
        category_stats = {row[0]: row[1] for row in cat_result.all()}

        # Daily trend
        daily_query = (
            select(
                func.strftime("%Y-%m-%d", SystemLog.created_at).label("date"),
                func.count().label("count"),
            )
            .where(SystemLog.created_at >= start)
            .group_by("date")
            .order_by("date")
        )
        daily_result = await db.execute(daily_query)
        daily_trend = [{"date": row[0], "count": row[1]} for row in daily_result.all()]

        # Total logs
        total_query = select(func.count()).select_from(SystemLog).where(SystemLog.created_at >= start)
        total_result = await db.execute(total_query)
        total = total_result.scalar() or 0

        # Error count
        error_query = select(func.count()).select_from(SystemLog).where(
            and_(SystemLog.created_at >= start, SystemLog.level.in_(["ERROR", "CRITICAL"]))
        )
        error_result = await db.execute(error_query)
        errors = error_result.scalar() or 0

        return {
            "period_days": days,
            "total": total,
            "errors": errors,
            "by_level": level_stats,
            "by_category": category_stats,
            "daily_trend": daily_trend,
        }

    @staticmethod
    async def cleanup_old_logs(db: AsyncSession, retention_days: int = 30) -> int:
        """Delete logs older than retention_days."""
        from sqlalchemy import delete
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        stmt = delete(SystemLog).where(SystemLog.created_at < cutoff)
        result = await db.execute(stmt)
        await db.commit()
        deleted = result.rowcount
        logger.info(LogCategory.SYSTEM, f"Cleaned up {deleted} old log entries", {"retention_days": retention_days, "deleted": deleted})
        return deleted
