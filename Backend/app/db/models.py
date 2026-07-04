"""Database models using SQLAlchemy ORM."""
import json
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import (
    Column, Integer, String, Text, Float, ForeignKey, DateTime, UniqueConstraint, CheckConstraint, JSON, select, func
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    password_hash = Column(String(128), nullable=False)
    nickname = Column(String(50), nullable=True)  # 显示昵称
    token_version = Column(Integer, default=1)     # Token 版本号，修改密码时+1，旧 token 自动失效
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    characters = relationship("Character", back_populates="user", lazy="selectin")
    personas = relationship("UserPersona", back_populates="user", lazy="selectin")
    sessions = relationship("ChatSession", back_populates="user", lazy="selectin")
    states = relationship("CharacterState", back_populates="user", lazy="selectin")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "nickname": self.nickname,
            "is_active": self.is_active,
            "token_version": self.token_version,
            "created_at": _to_iso(self.created_at),
        }


class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    nickname = Column(String(50), nullable=True)
    avatar = Column(Text, nullable=True)
    age = Column(String(20), nullable=True)
    gender = Column(String(10), nullable=True)
    appearance = Column(Text, nullable=True)
    background = Column(Text, nullable=True)
    personality = Column(Text, nullable=True)  # JSON array
    speaking_style = Column(Text, nullable=True)
    emotional_triggers = Column(Text, nullable=True)  # JSON object
    taboos = Column(Text, nullable=True)  # JSON array
    examples = Column(Text, nullable=True)  # JSON array
    world_setting = Column(Text, nullable=True)
    is_default = Column(Integer, default=0)
    is_system = Column(Integer, default=0)
    sort_order = Column(Integer, default=0)
    search_enabled = Column(Integer, default=0)  # 0=关闭, 1=开启
    initial_mood = Column(String(50), default="平静")
    initial_affection = Column(Integer, default=50)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # NULL=系统角色
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="characters", lazy="selectin")
    sessions = relationship("ChatSession", back_populates="character", lazy="selectin")
    states = relationship("CharacterState", back_populates="character", lazy="selectin")

    def to_dict(self, full: bool = False) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "nickname": self.nickname,
            "avatar": self.avatar,
            "is_default": self.is_default,
            "is_system": self.is_system,
            "sort_order": self.sort_order,
            "search_enabled": self.search_enabled,
            "initial_mood": self.initial_mood,
            "initial_affection": self.initial_affection,
            "created_at": _to_iso(self.created_at),
            "updated_at": _to_iso(self.updated_at),
        }
        if full:
            data.update({
                "age": self.age,
                "gender": self.gender,
                "appearance": self.appearance,
                "background": self.background,
                "personality": safe_json_load(self.personality, []),
                "speaking_style": self.speaking_style,
                "emotional_triggers": safe_json_load(self.emotional_triggers, {}),
                "taboos": safe_json_load(self.taboos, []),
                "examples": safe_json_load(self.examples, []),
                "world_setting": self.world_setting,
            })
        return data


class UserPersona(Base):
    __tablename__ = "user_personas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    avatar = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    background = Column(Text, nullable=True)
    personality = Column(Text, nullable=True)  # JSON array
    speaking_style = Column(Text, nullable=True)
    is_default = Column(Integer, default=0)
    sort_order = Column(Integer, default=0)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # NULL=系统人格
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="personas", lazy="selectin")
    sessions = relationship("ChatSession", back_populates="user_persona", lazy="selectin")
    states = relationship("CharacterState", back_populates="user_persona", lazy="selectin")

    def to_dict(self, full: bool = False) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "avatar": self.avatar,
            "description": self.description,
            "is_default": self.is_default,
            "sort_order": self.sort_order,
            "created_at": _to_iso(self.created_at),
            "updated_at": _to_iso(self.updated_at),
        }
        if full:
            data.update({
                "background": self.background,
                "personality": safe_json_load(self.personality, []),
                "speaking_style": self.speaking_style,
            })
        return data


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    user_persona_id = Column(Integer, ForeignKey("user_personas.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # nullable 兼容存量；业务强制赋值
    is_active = Column(Integer, default=1)
    message_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="sessions", lazy="selectin")
    character = relationship("Character", back_populates="sessions", lazy="selectin")
    user_persona = relationship("UserPersona", back_populates="sessions", lazy="selectin")
    messages = relationship("Message", back_populates="session", lazy="selectin", order_by="Message.created_at")
    states = relationship("CharacterState", back_populates="session", lazy="selectin")
    summaries = relationship("MemorySummary", back_populates="session", lazy="selectin")

    def to_dict(self, include_character: bool = True, include_persona: bool = True) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "character_id": self.character_id,
            "user_persona_id": self.user_persona_id,
            "is_active": self.is_active,
            "message_count": self.message_count,
            "created_at": _to_iso(self.created_at),
            "updated_at": _to_iso(self.updated_at),
        }
        if include_character and self.character:
            data["character"] = {
                "id": self.character.id,
                "name": self.character.name,
                "avatar": self.character.avatar,
            }
        if include_persona and self.user_persona:
            data["user_persona"] = {
                "id": self.user_persona.id,
                "name": self.user_persona.name,
                "avatar": self.user_persona.avatar,
            }
        return data


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    parent_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    token_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages", lazy="selectin")

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system')", name="check_message_role"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "parent_message_id": self.parent_message_id,
            "token_count": self.token_count,
            "created_at": _to_iso(self.created_at),
        }


class CharacterState(Base):
    __tablename__ = "character_states"

    id = Column(Integer, primary_key=True, autoincrement=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    user_persona_id = Column(Integer, ForeignKey("user_personas.id"), nullable=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # 多用户状态隔离
    mood = Column(String(50), default="平静")
    affection = Column(Integer, default=50)
    state_json = Column(Text, nullable=True)  # JSON
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="states", lazy="selectin")
    character = relationship("Character", back_populates="states", lazy="selectin")
    user_persona = relationship("UserPersona", back_populates="states", lazy="selectin")
    session = relationship("ChatSession", back_populates="states", lazy="selectin")

    # Note: Unique constraint migrated from (character_id, user_persona_id)
    # to (character_id, user_persona_id, user_id). Since SQLite cannot ALTER
    # constraints, uniqueness is now enforced at the application level
    # (see character_service.py). The old constraint remains in the DB but
    # is excluded from the ORM model so new tables won't have it.

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "character_id": self.character_id,
            "user_persona_id": self.user_persona_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "mood": self.mood,
            "affection": self.affection,
            "state_json": safe_json_load(self.state_json, {}),
            "last_updated": _to_iso(self.last_updated),
        }


class MemorySummary(Base):
    __tablename__ = "memory_summaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    summary = Column(Text, nullable=False)
    start_message_id = Column(Integer, nullable=True)
    end_message_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="summaries", lazy="selectin")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "summary": self.summary,
            "start_message_id": self.start_message_id,
            "end_message_id": self.end_message_id,
            "created_at": _to_iso(self.created_at),
        }


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String(20), nullable=False)
    category = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    details = Column(Text, nullable=True)  # JSON
    source = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')", name="check_log_level"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "level": self.level,
            "category": self.category,
            "message": self.message,
            "details": safe_json_load(self.details, None),
            "source": self.source,
            "created_at": _to_iso(self.created_at),
        }


def _to_iso(dt: Optional[datetime]) -> Optional[str]:
    """Convert datetime to ISO 8601 string with timezone.

    SQLite stores naive UTC datetimes. Without timezone info, JavaScript
    engines may parse them as local time, causing off-by-hours display.
    Always append 'Z' (or timezone offset) to make UTC explicit.
    """
    if dt is None:
        return None
    # SQLite may return datetimes as strings; handle both cases
    if isinstance(dt, str):
        # Already has timezone marker? Return as-is
        if dt.endswith('Z') or (len(dt) >= 6 and (dt[-6] == '+' or dt[-6] == '-')):
            return dt
        # SQLite stores as "YYYY-MM-DD HH:MM:SS.mmmmmm" — replace space with T
        s = dt.replace(' ', 'T')
        return s + 'Z'
    if dt.tzinfo is None:
        return dt.isoformat() + 'Z'
    return dt.isoformat()


def safe_json_load(value: Optional[str], default):
    """Safely load JSON string, return default on failure."""
    if not value:
        return default
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dump(value) -> Optional[str]:
    """Safely dump value to JSON string."""
    if value is None:
        return None
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return None
