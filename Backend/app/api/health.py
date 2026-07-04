"""Health check API."""
from datetime import datetime

from fastapi import APIRouter

from app.core.logging import logger, LogCategory

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health_check():
    """Check backend and dependencies health."""
    from app.config import get_settings
    from app.db.database import async_engine
    from sqlalchemy import text

    settings = get_settings()
    services = {
        "database": "unknown",
        "qdrant": "unknown",
        "redis": "unknown",
    }

    # Check database
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        services["database"] = "connected"
    except Exception as e:
        services["database"] = f"error: {str(e)}"
        logger.error(LogCategory.SYSTEM, "Database health check failed", {"error": str(e)})

    # Check Qdrant (optional)
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
            if resp.status_code < 500:
                services["qdrant"] = "connected"
    except Exception:
        services["qdrant"] = "disconnected (optional)"

    # Check Redis (optional)
    try:
        import redis.asyncio as redis
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.ping()
        services["redis"] = "connected"
        await r.close()
    except Exception:
        services["redis"] = "disconnected (optional)"

    return {
        "code": 0,
        "message": "success",
        "data": {
            "status": "healthy" if services["database"] == "connected" else "degraded",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "services": services,
        }
    }
