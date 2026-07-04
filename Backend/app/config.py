"""Global configuration loaded from environment variables and .env file."""
import os
from pathlib import Path
from functools import lru_cache

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
AVATARS_DIR = DATA_DIR / "avatars"

class Settings:
    """Application settings."""

    # === Basic ===
    APP_NAME: str = os.getenv("APP_NAME", "AI-Chat-Companion")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DEBUG: bool = APP_ENV == "development"

    # === Security ===
    # (JWT-based auth replaces the legacy API Key)

    # === JWT ===
    JWT_SECRET: str = os.getenv(
        "JWT_SECRET",
        __import__("secrets").token_hex(32),
    )

    # === Server ===
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))

    # === Database ===
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        f"sqlite+aiosqlite:///{DATA_DIR / 'chat.db'}"
    )

    # === File Storage ===
    AVATAR_MAX_SIZE: int = int(os.getenv("AVATAR_MAX_SIZE", "5"))  # MB
    AVATAR_ALLOWED_TYPES: set = set(
        os.getenv("AVATAR_ALLOWED_TYPES", "image/jpeg,image/png,image/webp").split(",")
    )

    # === LLM API ===
    LLM_API_URL: str = os.getenv("LLM_API_URL", "")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gpt-4o-mini")
    LLM_MODEL_NAME_CHEAP: str = os.getenv("LLM_MODEL_NAME_CHEAP", "gpt-4o-mini")
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2048"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "60"))

    # === Embedding API ===
    EMBEDDING_API_URL: str = os.getenv("EMBEDDING_API_URL", "")
    EMBEDDING_API_KEY: str = os.getenv("EMBEDDING_API_KEY", "")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "1536"))

    # === Qdrant ===
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
    QDRANT_COLLECTION_NAME: str = os.getenv("QDRANT_COLLECTION_NAME", "memories")

    # === Redis (arq) ===
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    USE_WORKERS: bool = os.getenv("USE_WORKERS", "true").lower() == "true"

    # === Memory ===
    MEMORY_TOP_K: int = int(os.getenv("MEMORY_TOP_K", "5"))
    MEMORY_DECAY_DAYS: int = int(os.getenv("MEMORY_DECAY_DAYS", "30"))
    RECENT_HISTORY_ROUNDS: int = int(os.getenv("RECENT_HISTORY_ROUNDS", "10"))
    MAX_PROMPT_TOKENS: int = int(os.getenv("MAX_PROMPT_TOKENS", "6000"))

    # === Logging ===
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_RETENTION_DAYS: int = int(os.getenv("LOG_RETENTION_DAYS", "30"))
    LOG_TO_DB: bool = os.getenv("LOG_TO_DB", "true").lower() == "true"
    LOG_TO_FILE: bool = os.getenv("LOG_TO_FILE", "true").lower() == "true"
    LOG_FILE_PATH: str = os.getenv("LOG_FILE_PATH", str(DATA_DIR / "logs" / "app.log"))

    # === Search API (博查 Bocha) ===
    # 注册获取免费 API Key: https://open.bochaai.com
    SEARCH_API_URL: str = os.getenv("SEARCH_API_URL", "https://api.bochaai.com/v1/web-search")
    SEARCH_API_KEY: str = os.getenv("SEARCH_API_KEY", "")
    SEARCH_RESULT_COUNT: int = int(os.getenv("SEARCH_RESULT_COUNT", "5"))
    SEARCH_TIMEOUT: int = int(os.getenv("SEARCH_TIMEOUT", "10"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
