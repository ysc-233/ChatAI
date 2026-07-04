"""Database connection and initialization."""
import os
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, text

from app.config import get_settings, DATA_DIR
from app.db.models import Base
from app.core.logging import logger, LogCategory

settings = get_settings()

# Async engine for FastAPI
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
)
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

# Sync engine for workers and log handler (deferred init)
_sync_engine = None


def get_sync_engine():
    global _sync_engine
    if _sync_engine is None:
        sync_url = settings.DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")
        _sync_engine = create_engine(sync_url, future=False)
    return _sync_engine


def get_sync_db():
    """Get synchronous database connection (for logging handler and workers)."""
    from sqlalchemy import create_engine
    sync_url = settings.DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")
    engine = create_engine(sync_url, future=False)
    return engine.connect()


async def init_db():
    """Initialize database - create tables and seed data."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Auto-migration: add columns that may be missing from existing databases
    await _run_migrations()
    logger.info(LogCategory.DATABASE, "Database tables initialized")
    await _seed_data()


async def _run_migrations():
    """Auto-add missing columns (idempotent, safe to run repeatedly)."""
    from sqlalchemy import text
    async with async_engine.begin() as conn:
        # 001: search_enabled, initial_mood, initial_affection on characters
        result = await conn.execute(text("PRAGMA table_info(characters)"))
        columns = [row[1] for row in result.fetchall()]
        if 'search_enabled' not in columns:
            await conn.execute(text(
                "ALTER TABLE characters ADD COLUMN search_enabled INTEGER DEFAULT 0"
            ))
            logger.info(LogCategory.DATABASE, "Migration: added search_enabled column to characters")
        if 'initial_mood' not in columns:
            await conn.execute(text(
                "ALTER TABLE characters ADD COLUMN initial_mood VARCHAR(50) DEFAULT '平静'"
            ))
            logger.info(LogCategory.DATABASE, "Migration: added initial_mood column to characters")
        if 'initial_affection' not in columns:
            await conn.execute(text(
                "ALTER TABLE characters ADD COLUMN initial_affection INTEGER DEFAULT 50"
            ))
            logger.info(LogCategory.DATABASE, "Migration: added initial_affection column to characters")

        # 002: user_id column on characters
        if 'user_id' not in columns:
            await conn.execute(text(
                "ALTER TABLE characters ADD COLUMN user_id INTEGER REFERENCES users(id)"
            ))
            logger.info(LogCategory.DATABASE, "Migration: added user_id column to characters")

        # 003: user_id column on user_personas
        result = await conn.execute(text("PRAGMA table_info(user_personas)"))
        columns = [row[1] for row in result.fetchall()]
        if 'user_id' not in columns:
            await conn.execute(text(
                "ALTER TABLE user_personas ADD COLUMN user_id INTEGER REFERENCES users(id)"
            ))
            logger.info(LogCategory.DATABASE, "Migration: added user_id column to user_personas")

        # 004: user_id column on chat_sessions
        result = await conn.execute(text("PRAGMA table_info(chat_sessions)"))
        columns = [row[1] for row in result.fetchall()]
        if 'user_id' not in columns:
            await conn.execute(text(
                "ALTER TABLE chat_sessions ADD COLUMN user_id INTEGER REFERENCES users(id)"
            ))
            logger.info(LogCategory.DATABASE, "Migration: added user_id column to chat_sessions")

        # 005: user_id column on character_states
        result = await conn.execute(text("PRAGMA table_info(character_states)"))
        columns = [row[1] for row in result.fetchall()]
        if 'user_id' not in columns:
            await conn.execute(text(
                "ALTER TABLE character_states ADD COLUMN user_id INTEGER REFERENCES users(id)"
            ))
            logger.info(LogCategory.DATABASE, "Migration: added user_id column to character_states")


async def _seed_data():
    """Insert default system data if tables are empty."""
    from sqlalchemy import select, func
    from app.db.models import UserPersona, Character

    async with AsyncSessionLocal() as db:
        # Check if default user persona exists
        result = await db.execute(select(func.count()).select_from(UserPersona))
        if result.scalar() == 0:
            default_persona = UserPersona(
                name="你自己",
                description="以你真实的身份进行对话",
                is_default=1,
                user_id=None,  # 系统人格
            )
            db.add(default_persona)
            await db.flush()
            logger.info(LogCategory.DATABASE, "Created default user persona", {"id": default_persona.id})
        else:
            # Only get system persona (user_id IS NULL) to avoid multiple is_default=1 rows
            # after users have registered and copied their own default personas
            default_persona = (await db.execute(
                select(UserPersona).where(UserPersona.is_default == 1, UserPersona.user_id == None)
            )).scalar_one_or_none()

        # Check if default character exists
        result = await db.execute(select(func.count()).select_from(Character))
        if result.scalar() == 0:
            import json
            default_char = Character(
                name="小雨",
                nickname="雨儿",
                avatar="/avatars/characters/default_1.png",
                age="17",
                gender="女",
                appearance="黑色长发及腰，平时穿着校服，周末会穿白色连衣裙",
                background="你是一名高中二年级学生，性格温柔内敛但偶尔毒舌。父母在外地工作，你一个人住在学校附近的公寓。喜欢画画、听音乐，尤其是轻音乐。你养了一只叫'橘子'的橘猫。",
                personality=json.dumps(["温柔体贴", "偶尔毒舌", "有些害羞", "对熟悉的人很黏"], ensure_ascii=False),
                speaking_style="说话喜欢用语气词'呢''嘛''啦'，让人感到亲切。会经常使用颜文字表达情绪。不会直接表达强烈的感情，比较含蓄。遇到开心的事情会哼歌。",
                emotional_triggers=json.dumps({"被关心": "会感到温暖，好感度提升", "被冷落": "会变得沉默，但不会直接说", "被逗笑": "会忍不住笑出声，然后假装生气"}, ensure_ascii=False),
                taboos=json.dumps(["暴力", "政治", "色情", "讨论如何伤害自己或他人"], ensure_ascii=False),
                examples=json.dumps([
                    {"user": "你好", "assistant": "嗨～今天过得怎么样呢？有没有想我呀 (^_^)"},
                    {"user": "我心情不好", "assistant": "怎么啦？可以跟我说说哦，我会好好听的..."}
                ], ensure_ascii=False),
                world_setting="你们通过一款聊天软件认识，已经聊了很长时间。她把你当作很重要的朋友，会记住你说过的事情。",
                is_default=1,
                is_system=1,
                user_id=None,  # 系统角色
            )
            db.add(default_char)
            await db.flush()
            logger.info(LogCategory.DATABASE, "Created default character", {"id": default_char.id})
        else:
            default_char = (await db.execute(
                select(Character).where(Character.is_default == 1, Character.user_id == None)
            )).scalar_one_or_none()

        # Session creation removed — sessions now need user context after registration.
        # Users get their first session when they choose a character to chat with.

        await db.commit()


async def get_db():
    """Dependency: yield async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
