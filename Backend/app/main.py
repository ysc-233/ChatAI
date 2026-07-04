"""FastAPI main application entry."""
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from app.config import get_settings, DATA_DIR, AVATARS_DIR
from app.db.database import init_db
from app.core.exceptions import app_exception_handler, http_exception_handler, AppException
from app.core.logging import logger, LogCategory

from app.api import auth, characters, personas, sessions, messages, ws, health, logs

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info(LogCategory.SYSTEM, f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode")
    await init_db()

    # Initialize Qdrant collection (non-blocking on failure)
    try:
        from app.services.vector_store import QdrantStore
        store = QdrantStore()
        ok = await store.init_collection()
        if ok:
            logger.info(LogCategory.SYSTEM, "Qdrant collection initialized")
        else:
            logger.warning(LogCategory.SYSTEM, "Qdrant unavailable — memory features disabled")
    except Exception as e:
        logger.warning(LogCategory.SYSTEM, f"Qdrant init skipped: {e}")

    yield
    logger.info(LogCategory.SYSTEM, f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    description="AI Chat Companion Backend API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log all API requests and measure latency."""
    start = time.time()
    path = request.url.path
    method = request.method

    # Skip health check and static files logging
    if path.startswith("/avatars") or path == "/api/health":
        return await call_next(request)

    try:
        response = await call_next(request)
        duration = (time.time() - start) * 1000
        status_code = response.status_code
        client_ip = request.client.host if request.client else ""
        logger.api_request(method, path, status_code, duration, client_ip)
        return response
    except Exception as e:
        duration = (time.time() - start) * 1000
        client_ip = request.client.host if request.client else ""
        logger.api_request(method, path, 500, duration, client_ip, error=str(e))
        raise


# Exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, http_exception_handler)

# Static files (avatars)
app.mount("/avatars", StaticFiles(directory=str(AVATARS_DIR)), name="avatars")

# API routes
# Auth routes (public, uses JWT internally)
app.include_router(auth.router, prefix="/api")
app.include_router(health.router, prefix="/api")

# Resource routes (JWT auth per-endpoint via get_current_user)
app.include_router(characters.router, prefix="/api")
app.include_router(personas.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(messages.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(ws.router)
