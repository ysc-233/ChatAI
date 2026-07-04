"""Qdrant Vector Store - collection management, upsert, search."""
import asyncio
import uuid
from typing import List, Dict, Optional

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter, FieldCondition,
    MatchValue,
)
from qdrant_client.http.exceptions import UnexpectedResponse

from app.config import get_settings
from app.core.logging import logger, LogCategory

settings = get_settings()


def _ensure_embedding_url(url: str) -> str:
    """Normalize embedding API URL to ensure it ends with /embeddings."""
    url = url.rstrip('/')
    if url.endswith('/v1'):
        return url + '/embeddings'
    if not url.endswith('/embeddings'):
        return url + '/v1/embeddings'
    return url


class QdrantStore:
    """Singleton wrapper for Qdrant vector database operations."""

    _instance: Optional["QdrantStore"] = None
    _client: Optional[AsyncQdrantClient] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _connect(self) -> Optional[AsyncQdrantClient]:
        """Lazy-init async Qdrant client connection."""
        if self._client is not None:
            return self._client
        try:
            self._client = AsyncQdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
                timeout=10,
            )
            # Will be verified on first actual operation
            logger.info(
                LogCategory.SYSTEM,
                f"AsyncQdrantClient created for {settings.QDRANT_HOST}:{settings.QDRANT_PORT}"
            )
            return self._client
        except Exception as e:
            logger.warning(LogCategory.SYSTEM, f"Qdrant connection failed: {e}")
            self._client = None
            return None

    async def init_collection(self) -> bool:
        """Create collection if not exists. Call once at startup."""
        if self._initialized:
            return True

        client = self._connect()
        if not client:
            return False

        collection_name = settings.QDRANT_COLLECTION_NAME
        try:
            collections = await client.get_collections()
            existing_names = [c.name for c in collections.collections]
            if collection_name in existing_names:
                logger.info(
                    LogCategory.SYSTEM,
                    f"Qdrant collection '{collection_name}' already exists"
                )
                self._initialized = True
                return True

            await client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=settings.EMBEDDING_DIMENSION,
                    distance=Distance.COSINE,
                ),
            )
            # Create payload indexes for filtering
            await client.create_payload_index(
                collection_name=collection_name,
                field_name="character_id",
                field_schema="integer",
            )
            await client.create_payload_index(
                collection_name=collection_name,
                field_name="user_persona_id",
                field_schema="integer",
            )
            await client.create_payload_index(
                collection_name=collection_name,
                field_name="session_id",
                field_schema="integer",
            )
            logger.info(
                LogCategory.SYSTEM,
                f"Created Qdrant collection '{collection_name}' (dim={settings.EMBEDDING_DIMENSION})"
            )
            self._initialized = True
            return True
        except Exception as e:
            logger.error(LogCategory.SYSTEM, f"Failed to init Qdrant collection: {e}")
            return False

    def _is_available(self) -> bool:
        """Check if Qdrant is connected."""
        return self._client is not None and self._initialized

    async def upsert(self, memories: List[Dict]) -> int:
        """Insert or update memory vectors into Qdrant.

        Each memory dict should have:
            vector (list): embedding vector
            content (str): memory text
            memory_type (str): fact/preference/event
            importance (int): 1-10
            character_id (int)
            user_persona_id (int, optional)
            session_id (int)
        Returns count of upserted points.
        """
        if not memories or not self._is_available():
            return 0

        points = []
        for m in memories:
            if not m.get("vector") or len(m["vector"]) != settings.EMBEDDING_DIMENSION:
                logger.warning(
                    LogCategory.MEMORY,
                    f"Skip memory: invalid vector dim (expected {settings.EMBEDDING_DIMENSION})"
                )
                continue
            point_id = m.get("id", str(uuid.uuid4()))
            points.append(PointStruct(
                id=point_id,
                vector=m["vector"],
                payload={
                    "content": m.get("content", ""),
                    "memory_type": m.get("memory_type", "fact"),
                    "importance": m.get("importance", 5),
                    "character_id": m.get("character_id", 0),
                    "user_persona_id": m.get("user_persona_id"),
                    "session_id": m.get("session_id"),
                },
            ))

        if not points:
            return 0

        try:
            await self._client.upsert(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                points=points,
                wait=False,
            )
            logger.memory_operation("upsert", 0, count=len(points))
            return len(points)
        except Exception as e:
            logger.error(LogCategory.MEMORY, f"Qdrant upsert failed: {e}")
            return 0

    async def search(
        self,
        query_vector: List[float],
        character_id: int,
        user_persona_id: Optional[int] = None,
        limit: int = None,
    ) -> List[Dict]:
        """Semantic search for relevant memories.

        Filters by character_id (required), optionally by user_persona_id.
        Returns list of {content, memory_type, importance, score}.
        """
        if not query_vector or not self._is_available():
            return []

        if limit is None:
            limit = settings.MEMORY_TOP_K

        # Build filter: must match character_id
        must_conditions = [
            FieldCondition(
                key="character_id",
                match=MatchValue(value=character_id),
            )
        ]
        # Optionally match user_persona_id
        if user_persona_id is not None:
            must_conditions.append(
                FieldCondition(
                    key="user_persona_id",
                    match=MatchValue(value=user_persona_id),
                )
            )

        try:
            results = await self._client.query_points(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                query=query_vector,
                query_filter=Filter(must=must_conditions),
                limit=limit * 2,  # Fetch extra for post-filtering
                with_payload=True,
            )

            memories = []
            for hit in results.points:
                payload = hit.payload or {}
                memories.append({
                    "content": payload.get("content", ""),
                    "memory_type": payload.get("memory_type", "fact"),
                    "importance": payload.get("importance", 5),
                    "score": hit.score,
                })
            logger.memory_operation("search", character_id, count=len(memories))
            return memories[:limit]

        except Exception as e:
            logger.warning(LogCategory.MEMORY, f"Qdrant search failed: {e}")
            return []

    async def delete_by_character(self, character_id: int) -> int:
        """Delete all memories for a character (cascade on character delete)."""
        if not self._is_available():
            return 0

        try:
            result = await self._client.delete(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="character_id",
                            match=MatchValue(value=character_id),
                        )
                    ]
                ),
            )
            count = result.status.get("deleted_count", 0) if hasattr(result, 'status') else 0
            logger.info(LogCategory.MEMORY, f"Deleted {count} memories for character {character_id}")
            return count
        except Exception as e:
            logger.warning(LogCategory.MEMORY, f"Qdrant delete_by_character failed: {e}")
            return 0

    async def delete_by_session(self, session_id: int) -> int:
        """Delete all memories for a session."""
        if not self._is_available():
            return 0

        try:
            result = await self._client.delete(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="session_id",
                            match=MatchValue(value=session_id),
                        )
                    ]
                ),
            )
            count = result.status.get("deleted_count", 0) if hasattr(result, 'status') else 0
            logger.info(LogCategory.MEMORY, f"Deleted {count} memories for session {session_id}")
            return count
        except Exception as e:
            logger.warning(LogCategory.MEMORY, f"Qdrant delete_by_session failed: {e}")
            return 0

    async def disconnect(self):
        """Close Qdrant connection."""
        if self._client:
            try:
                await self._client.close()
            except Exception:
                pass
            self._client = None
            self._initialized = False
