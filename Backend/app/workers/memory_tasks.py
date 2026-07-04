"""arq worker tasks - background processing for memory extraction and summarization."""
from datetime import datetime
from typing import List, Dict

from arq import create_pool
from arq.connections import RedisSettings

from app.config import get_settings
from app.core.logging import logger, LogCategory

settings = get_settings()


async def extract_memories(ctx, session_id: int, dialogue: List[Dict]):
    """Background task: extract memories from dialogue."""
    logger.info(LogCategory.MEMORY, f"Extracting memories for session {session_id}")
    # Placeholder: real implementation would call LLM to extract facts
    return {"session_id": session_id, "extracted": 0}


async def summarize_session(ctx, session_id: int, start_msg_id: int, end_msg_id: int):
    """Background task: summarize conversation segment."""
    logger.info(LogCategory.MEMORY, f"Summarizing session {session_id} messages {start_msg_id}-{end_msg_id}")
    return {"session_id": session_id, "summarized": True}


async def update_character_state_task(ctx, session_id: int, character_id: int, user_persona_id: int):
    """Background task: update character state after conversation."""
    logger.info(LogCategory.MEMORY, f"Updating state for character {character_id} / persona {user_persona_id}")
    return {"character_id": character_id, "updated": True}


class WorkerSettings:
    """arq worker configuration."""
    functions = [extract_memories, summarize_session, update_character_state_task]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    job_timeout = 300
    max_jobs = 10


async def get_redis_pool():
    """Get Redis connection pool for enqueueing tasks."""
    return await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
