"""Embedding Adapter - text to vector."""
from typing import List

import httpx

from app.config import get_settings
from app.core.logging import logger, LogCategory

settings = get_settings()

def _normalize_embedding_url(url: str) -> str:
    """Normalize embedding API URL to end with /embeddings."""
    url = url.rstrip('/')
    if url.endswith('/v1'):
        return url + '/embeddings'
    if url.endswith('/embeddings'):
        return url
    return url + '/v1/embeddings'

ZERO_VECTOR = None  # Lazy-computed when dimension is known


def _zero_vector() -> list:
    """Return a zero vector of configured dimension."""
    global ZERO_VECTOR
    if ZERO_VECTOR is None or len(ZERO_VECTOR) != settings.EMBEDDING_DIMENSION:
        ZERO_VECTOR = [0.0] * settings.EMBEDDING_DIMENSION
    return ZERO_VECTOR


class EmbeddingAdapter:
    """Adapter for embedding API (OpenAI-compatible)."""

    def _is_configured(self) -> bool:
        return bool(settings.EMBEDDING_API_URL and settings.EMBEDDING_API_KEY)

    async def encode(self, text: str) -> list:
        """Get embedding vector for a single text."""
        results = await self.encode_batch([text])
        return results[0] if results else _zero_vector()

    async def encode_batch(self, texts: List[str]) -> List[list]:
        """Get embedding vectors for multiple texts in one API call.

        Args:
            texts: list of text strings to embed

        Returns:
            List of embedding vectors, same order as input.
            Returns zero vectors if API is not configured or call fails.
        """
        if not texts:
            return []

        if not self._is_configured():
            logger.warning(LogCategory.LLM, "Embedding API not configured, returning zero vectors")
            return [_zero_vector() for _ in texts]

        payload = {
            "model": settings.EMBEDDING_MODEL,
            "input": texts,
        }
        headers = {
            "Authorization": f"Bearer {settings.EMBEDDING_API_KEY}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(_normalize_embedding_url(settings.EMBEDDING_API_URL), json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                # OpenAI returns data array sorted by index
                embeddings = sorted(data["data"], key=lambda d: d["index"])
                return [item["embedding"] for item in embeddings]
        except Exception as e:
            logger.error(LogCategory.LLM, f"Embedding failed: {e}")
            return [_zero_vector() for _ in texts]
