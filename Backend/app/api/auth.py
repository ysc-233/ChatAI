"""Auth API - register, login, refresh, profile."""
import time
import re
import bcrypt
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User, UserPersona
from app.core.auth import (
    create_access_token, create_refresh_token, decode_token, get_current_user
)
from app.core.logging import logger, LogCategory

router = APIRouter(prefix="/auth", tags=["Auth"])

# In-memory rate limiter (per IP)
_login_attempts: dict[str, list[float]] = defaultdict(list)
_register_attempts: dict[str, list[float]] = defaultdict(list)
MAX_LOGIN_PER_MIN = 10
MAX_REGISTER_PER_HOUR = 5


def _check_rate_limit(store: dict, key: str, max_attempts: int, window: int):
    """Check rate limit for key. Raises 429 if exceeded."""
    now = time.time()
    attempts = [t for t in store[key] if now - t < window]
    if len(attempts) >= max_attempts:
        raise HTTPException(status_code=429, detail={
            "code": 42900, "message": "请求过于频繁，请稍后再试", "data": None
        })
    attempts.append(now)
    store[key] = attempts


def _get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


async def _init_new_user_data(db: AsyncSession, user_id: int):
    """Create default persona and character for new user by copying system templates."""
    # Copy system personas
    system_personas = (await db.execute(
        select(UserPersona).where(UserPersona.user_id == None)
    )).scalars().all()

    for sp in system_personas:
        new_persona = UserPersona(
            name=sp.name,
            description=sp.description,
            background=sp.background,
            personality=sp.personality,
            speaking_style=sp.speaking_style,
            is_default=sp.is_default,
            sort_order=sp.sort_order,
            user_id=user_id,
        )
        db.add(new_persona)

    # Copy system characters (each user gets their own independent copy)
    from app.db.models import Character
    system_chars = (await db.execute(
        select(Character).where(Character.user_id == None)
    )).scalars().all()

    for sc in system_chars:
        new_char = Character(
            name=sc.name,
            nickname=sc.nickname,
            avatar=sc.avatar,
            age=sc.age,
            gender=sc.gender,
            appearance=sc.appearance,
            background=sc.background,
            personality=sc.personality,
            speaking_style=sc.speaking_style,
            emotional_triggers=sc.emotional_triggers,
            taboos=sc.taboos,
            examples=sc.examples,
            world_setting=sc.world_setting,
            is_default=sc.is_default,
            is_system=0,  # 用户副本不是系统角色，可删除
            sort_order=sc.sort_order,
            search_enabled=sc.search_enabled,
            initial_mood=sc.initial_mood,
            initial_affection=sc.initial_affection,
            user_id=user_id,
        )
        db.add(new_char)

    await db.flush()
    logger.info(LogCategory.DATABASE, f"Initialized user data for user {user_id}")


@router.post("/register")
async def register(data: dict, request: Request, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    nickname = (data.get("nickname") or "").strip() or None

    # Validate
    if not re.match(r'^[a-zA-Z0-9_]{3,50}$', username):
        raise HTTPException(status_code=400, detail={
            "code": 40001, "message": "用户名格式错误：3-50位字母、数字或下划线", "data": None
        })
    if len(password) < 8 or len(password) > 128:
        raise HTTPException(status_code=400, detail={
            "code": 40002, "message": "密码长度必须在 8-128 字符之间", "data": None
        })

    # Rate limit
    ip = _get_client_ip(request)
    _check_rate_limit(_register_attempts, ip, MAX_REGISTER_PER_HOUR, 3600)

    # Check uniqueness
    existing = (await db.execute(select(User).where(User.username == username))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail={
            "code": 40106, "message": "用户名已存在", "data": None
        })

    # Create user
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user = User(
        username=username,
        password_hash=password_hash,
        nickname=nickname or username,
    )
    db.add(user)
    await db.flush()

    # Initialize default data
    await _init_new_user_data(db, user.id)

    await db.commit()
    await db.refresh(user)

    # Generate tokens
    access_token = create_access_token(user.id, user.username, user.token_version)
    refresh_token = create_refresh_token(user.id, user.username, user.token_version)

    logger.security_event("register", username, {"user_id": user.id})

    return {
        "code": 0, "message": "success",
        "data": {
            "user": user.to_dict(),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
        }
    }


@router.post("/login")
async def login(data: dict, request: Request, db: AsyncSession = Depends(get_db)):
    """Login with username and password."""
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        raise HTTPException(status_code=400, detail={
            "code": 40000, "message": "用户名和密码不能为空", "data": None
        })

    # Rate limit
    ip = _get_client_ip(request)
    _check_rate_limit(_login_attempts, ip, MAX_LOGIN_PER_MIN, 60)

    # Find user
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail={
            "code": 40105, "message": "用户名或密码错误", "data": None
        })
    if not user.is_active:
        raise HTTPException(status_code=403, detail={
            "code": 40305, "message": "账号已被禁用", "data": None
        })

    # Verify password
    if not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        raise HTTPException(status_code=401, detail={
            "code": 40105, "message": "用户名或密码错误", "data": None
        })

    # Generate tokens
    access_token = create_access_token(user.id, user.username, user.token_version)
    refresh_token = create_refresh_token(user.id, user.username, user.token_version)

    logger.security_event("login", username, {"user_id": user.id})

    return {
        "code": 0, "message": "success",
        "data": {
            "user": user.to_dict(),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
        }
    }


@router.post("/refresh")
async def refresh_token(
    request: Request,
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token using refresh token."""
    token = authorization or ""
    if not token:
        # Fallback: try to get from request headers directly
        token = request.headers.get("Authorization", "")
    if not token:
        raise HTTPException(status_code=401, detail={
            "code": 40100, "message": "未认证：缺少 Authorization header", "data": None
        })
    if token.startswith("Bearer "):
        token = token[7:]

    payload = decode_token(token)

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail={
            "code": 40103, "message": "Token 类型错误，请使用 refresh token", "data": None
        })

    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail={
            "code": 40104, "message": "用户不存在或已被禁用", "data": None
        })

    # Verify token version
    token_ver = payload.get("ver", 0)
    if token_ver != user.token_version:
        raise HTTPException(status_code=401, detail={
            "code": 40107, "message": "Token 已失效（密码已修改），请重新登录", "data": None
        })

    # Issue new tokens
    access_token = create_access_token(user.id, user.username, user.token_version)
    refresh_token = create_refresh_token(user.id, user.username, user.token_version)

    return {
        "code": 0, "message": "success",
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
        }
    }


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user profile."""
    return {"code": 0, "message": "success", "data": current_user.to_dict()}


@router.put("/me")
async def update_me(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user profile (nickname only)."""
    if "nickname" in data:
        nickname = (data["nickname"] or "").strip()
        if nickname and len(nickname) > 50:
            raise HTTPException(status_code=400, detail={
                "code": 40000, "message": "昵称不能超过50个字符", "data": None
            })
        current_user.nickname = nickname

    await db.commit()
    await db.refresh(current_user)
    return {"code": 0, "message": "success", "data": current_user.to_dict()}


@router.put("/password")
async def change_password(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change password. Invalidates all existing tokens."""
    old_password = data.get("old_password") or ""
    new_password = data.get("new_password") or ""

    if not old_password or not new_password:
        raise HTTPException(status_code=400, detail={
            "code": 40000, "message": "旧密码和新密码不能为空", "data": None
        })
    if len(new_password) < 8 or len(new_password) > 128:
        raise HTTPException(status_code=400, detail={
            "code": 40002, "message": "新密码长度必须在 8-128 字符之间", "data": None
        })

    # Verify old password
    if not bcrypt.checkpw(old_password.encode(), current_user.password_hash.encode()):
        raise HTTPException(status_code=400, detail={
            "code": 40003, "message": "旧密码错误", "data": None
        })

    # Update password and increment token version
    current_user.password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    current_user.token_version += 1
    await db.commit()

    # Issue new tokens (old ones now invalid)
    access_token = create_access_token(current_user.id, current_user.username, current_user.token_version)
    refresh_token = create_refresh_token(current_user.id, current_user.username, current_user.token_version)

    logger.security_event("password_changed", current_user.username, {"user_id": current_user.id})

    return {
        "code": 0, "message": "success",
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
        }
    }
