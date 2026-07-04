"""JWT authentication module."""
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.database import get_db
from app.db.models import User

settings = get_settings()

# JWT Configuration
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24
REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_access_token(user_id: int, username: str, token_version: int = 1) -> str:
    """Create access token."""
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": str(user_id),
        "username": username,
        "ver": token_version,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: int, username: str, token_version: int = 1) -> str:
    """Create refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "username": username,
        "ver": token_version,
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode JWT token, return payload."""
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail={
            "code": 40102, "message": "Token 已过期", "data": None
        })
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail={
            "code": 40103, "message": "Token 无效", "data": None
        })


async def get_current_user(
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and verify JWT from Authorization header, return current user."""
    if not authorization:
        raise HTTPException(status_code=401, detail={
            "code": 40100, "message": "未认证：缺少 Authorization header", "data": None
        })

    token = authorization
    if authorization.startswith("Bearer "):
        token = authorization[7:]

    payload = decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail={
            "code": 40103, "message": "Token 类型错误，请使用 access token", "data": None
        })

    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail={
            "code": 40104, "message": "用户不存在或已被删除", "data": None
        })
    if not user.is_active:
        raise HTTPException(status_code=403, detail={
            "code": 40305, "message": "账号已被禁用", "data": None
        })

    # Verify token version (modified password -> old tokens invalid)
    token_ver = payload.get("ver", 0)
    if token_ver != user.token_version:
        raise HTTPException(status_code=401, detail={
            "code": 40107, "message": "Token 已失效（密码已修改），请重新登录", "data": None
        })

    return user


async def verify_ws_token(token: str, db: AsyncSession) -> User | None:
    """WebSocket authentication: verify user from JWT token string."""
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        user_id = int(payload["sub"])
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user and user.is_active:
            token_ver = payload.get("ver", 0)
            if token_ver == user.token_version:
                return user
    except Exception:
        pass
    return None
