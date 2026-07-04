"""Character Service - state management per character-persona pair."""
import asyncio
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CharacterState, Character
from app.core.logging import logger, LogCategory

# Per-key locks to prevent duplicate CharacterState creation.
# Since SQLite cannot ALTER unique constraints, uniqueness is
# enforced at the application level with asyncio.Lock per key.
_state_locks: dict[tuple, asyncio.Lock] = {}
_locks_lock = asyncio.Lock()


async def _acquire_state_lock(character_id: int, user_persona_id, user_id) -> asyncio.Lock:
    """Get or create a per-key lock to serialize get_or_create_state calls."""
    key = (character_id, user_persona_id, user_id)
    async with _locks_lock:
        if key not in _state_locks:
            _state_locks[key] = asyncio.Lock()
        return _state_locks[key]


class CharacterService:
    """Manage character states and relationships."""

    @staticmethod
    async def get_or_create_state(
        db: AsyncSession,
        character_id: int,
        user_persona_id: Optional[int] = None,
        user_id: Optional[int] = None,
        session_id: Optional[int] = None,
    ):
        """Get or create character state for a pair (scoped to user)."""
        lock = await _acquire_state_lock(character_id, user_persona_id, user_id)
        async with lock:
            query = select(CharacterState).where(
                CharacterState.character_id == character_id,
                CharacterState.user_persona_id == user_persona_id,
                CharacterState.user_id == user_id,  # User-scoped
            )
            result = await db.execute(query)
            state = result.scalar_one_or_none()
            if not state:
                # Get character's initial mood/affection defaults
                char_result = await db.execute(select(Character).where(Character.id == character_id))
                char = char_result.scalar_one_or_none()
                initial_mood = (char.initial_mood if char and char.initial_mood else None) or "平静"
                initial_affection = char.initial_affection if char else 50

                state = CharacterState(
                    character_id=character_id,
                    user_persona_id=user_persona_id,
                    user_id=user_id,
                    session_id=session_id,
                    mood=initial_mood,
                    affection=initial_affection,
                )
                db.add(state)
                await db.commit()
                await db.refresh(state)
                logger.info(LogCategory.SYSTEM, f"Created character state for pair ({character_id}, {user_persona_id}, user={user_id})")
            return state

    @staticmethod
    async def update_state(
        db: AsyncSession,
        character_id: int,
        user_persona_id: Optional[int],
        user_id: Optional[int] = None,
        mood: Optional[str] = None,
        affection_delta: int = 0,
    ):
        """Update character state."""
        state = await CharacterService.get_or_create_state(
            db, character_id, user_persona_id, user_id=user_id
        )
        if mood:
            state.mood = mood
        if affection_delta:
            state.affection = max(0, min(100, (state.affection or 50) + affection_delta))
        await db.commit()
        return state
