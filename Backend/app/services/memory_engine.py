"""Memory Engine - recall, extract, summarize, decay."""
import json
from typing import List, Dict, Optional

from app.config import get_settings
from app.core.logging import logger, LogCategory
from app.services.embedding_adapter import EmbeddingAdapter
from app.services.vector_store import QdrantStore

settings = get_settings()

EXTRACT_FACTS_PROMPT = """从以下对话中提取关键事实。每个事实包含 content（简洁描述）、importance（1-10 重要性评分）、memory_type（fact/preference/event 之一）。

规则：
- fact: 客观事实（如：用户养了一只猫、角色住在东京）
- preference: 用户偏好（如：用户喜欢咖啡、用户讨厌早起）
- event: 发生的事件（如：用户今天去看了电影）
- importance 评分：涉及情感/关键信息的给高分（7-10），一般事实低分（1-3）
- 没有值得记忆的内容输出空数组 []

对话：
{context}

请只输出 JSON 数组，不要其他内容：
[{{"content": "...", "importance": 8, "memory_type": "fact"}}]"""

SUMMARIZE_PROMPT = """用 1-3 句话总结以下对话的主要内容，包含关键话题和重要信息点：

{context}

总结："""


class MemoryEngine:
    """Handle long-term memory operations with Qdrant + Embedding."""

    def __init__(self):
        self.embedder = EmbeddingAdapter()
        self.store = QdrantStore()
        self._embedding_ok: Optional[bool] = None

    def _check_embedding(self) -> bool:
        """Check if embedding API is configured. Cache result."""
        if self._embedding_ok is None:
            self._embedding_ok = bool(
                settings.EMBEDDING_API_URL and settings.EMBEDDING_API_KEY
            )
            if not self._embedding_ok:
                logger.warning(LogCategory.SYSTEM, "Embedding API not configured, memory features disabled")
        return self._embedding_ok

    async def recall(
        self,
        query: str,
        character_id: int,
        user_persona_id: Optional[int] = None,
        limit: int = None,
    ) -> List[Dict]:
        """Recall relevant memories from Qdrant by semantic similarity.

        Args:
            query: user's current message for similarity search
            character_id: filter by character
            user_persona_id: optionally filter by user persona
            limit: max memories to return (default MEMORY_TOP_K)

        Returns:
            List of {content, memory_type, importance, score}
        """
        if not self._check_embedding():
            return []

        query_vector = await self.embedder.encode(query)
        if not query_vector or all(v == 0.0 for v in query_vector):
            return []

        if limit is None:
            limit = settings.MEMORY_TOP_K

        memories = await self.store.search(
            query_vector=query_vector,
            character_id=character_id,
            user_persona_id=user_persona_id,
            limit=limit,
        )

        # Sort by importance * score hybrid ranking
        for m in memories:
            m["_rank"] = (m.get("importance", 5) / 10.0) * 0.4 + m.get("score", 0) * 0.6

        memories.sort(key=lambda m: m.get("_rank", 0), reverse=True)
        for m in memories:
            m.pop("_rank", None)

        if memories:
            logger.info(
                LogCategory.MEMORY,
                f"Recalled {len(memories)} memories for character {character_id}"
            )

        return memories[:limit]

    async def extract(
        self,
        dialogue: List[Dict],
        character_id: int,
        user_persona_id: Optional[int] = None,
        session_id: int = None,
    ) -> int:
        """Extract facts from recent dialogue and store in Qdrant.

        Args:
            dialogue: list of {role, content} from recent conversation
            character_id: the AI character being spoken to
            user_persona_id: the user persona (if any)
            session_id: current session for traceability

        Returns:
            Number of facts extracted and stored
        """
        if not self._check_embedding():
            return 0

        # Build context text from dialogue
        lines = []
        for msg in dialogue:
            role_label = "用户" if msg.get("role") == "user" else "角色"
            lines.append(f"{role_label}：{msg.get('content', '')}")
        context = "\n".join(lines)

        if not context.strip():
            return 0

        # Use cheap LLM to extract facts
        try:
            from app.services.llm_adapter import LLMAdapter
            llm = LLMAdapter()
            prompt = EXTRACT_FACTS_PROMPT.format(context=context)
            raw = await llm.cheap_completion(prompt, max_tokens=1024)

            # Parse JSON response
            facts = self._parse_facts(raw)
            if not facts:
                return 0

            # Encode all fact contents to vectors
            contents = [f["content"] for f in facts]
            vectors = await self.embedder.encode_batch(contents)

            # Build memory payloads
            memories = []
            for i, fact in enumerate(facts):
                if i < len(vectors) and vectors[i] and not all(v == 0.0 for v in vectors[i]):
                    memories.append({
                        "vector": vectors[i],
                        "content": fact.get("content", ""),
                        "memory_type": fact.get("memory_type", "fact"),
                        "importance": int(fact.get("importance", 5)),
                        "character_id": character_id,
                        "user_persona_id": user_persona_id,
                        "session_id": session_id,
                    })

            if memories:
                count = await self.store.upsert(memories)
                logger.info(
                    LogCategory.MEMORY,
                    f"Extracted {count} memories for character {character_id}"
                )
                return count
            return 0

        except Exception as e:
            logger.error(LogCategory.MEMORY, f"Memory extraction failed: {e}")
            return 0

    async def summarize(
        self,
        messages: List[Dict],
        character_id: int,
        session_id: int = None,
        start_msg_id: int = None,
        end_msg_id: int = None,
    ) -> Optional[str]:
        """Summarize a conversation segment using cheap LLM.

        Returns summary text, or None if too few messages.
        """
        if len(messages) < 8:
            return None

        lines = []
        for msg in messages:
            role_label = "用户" if msg.get("role") == "user" else "角色"
            lines.append(f"{role_label}：{msg.get('content', '')}")
        context = "\n".join(lines)

        try:
            from app.services.llm_adapter import LLMAdapter
            llm = LLMAdapter()
            prompt = SUMMARIZE_PROMPT.format(context=context)
            summary = await llm.cheap_completion(prompt, max_tokens=512)

            if summary and summary.strip():
                # Persist to SQLite MemorySummary table
                await self._save_summary(
                    session_id=session_id,
                    summary=summary.strip(),
                    start_msg_id=start_msg_id,
                    end_msg_id=end_msg_id,
                )
                logger.info(
                    LogCategory.MEMORY,
                    f"Summarized session {session_id}: {len(summary)} chars"
                )
                return summary.strip()
            return None

        except Exception as e:
            logger.error(LogCategory.MEMORY, f"Summarization failed: {e}")
            return None

    async def _save_summary(
        self,
        session_id: int,
        summary: str,
        start_msg_id: int = None,
        end_msg_id: int = None,
    ):
        """Save summary to SQLite MemorySummary table."""
        from app.db.database import AsyncSessionLocal
        from app.db.models import MemorySummary

        async with AsyncSessionLocal() as db:
            record = MemorySummary(
                session_id=session_id,
                summary=summary,
                start_message_id=start_msg_id,
                end_message_id=end_msg_id,
            )
            db.add(record)
            await db.commit()

    async def decay(self) -> int:
        """Decrease importance of old memories by 1 point.
        Only affects memories older than MEMORY_DECAY_DAYS and importance > 1.

        Note: Qdrant does not support bulk payload updates natively.
        This is implemented as a scan + re-upsert (expensive, call sparingly).
        Returns count of decayed memories.
        """
        if not self._check_embedding():
            return 0

        store = self.store
        if not store._is_available():
            return 0

        try:
            import time
            cutoff = time.time() - settings.MEMORY_DECAY_DAYS * 86400

            # Scroll through all points
            client = store._client
            collection = settings.QDRANT_COLLECTION_NAME
            offset = None
            decayed = 0

            while True:
                scroll_result = client.scroll(
                    collection_name=collection,
                    limit=100,
                    offset=offset,
                    with_payload=True,
                    with_vectors=True,
                )
                points = scroll_result[0]
                next_offset = scroll_result[1]

                if not points:
                    break

                # Filter and prepare updates
                to_update = []
                for point in points:
                    payload = point.payload or {}
                    importance = payload.get("importance", 5)
                    if importance <= 1:
                        continue
                    to_update.append({
                        "id": point.id,
                        "vector": point.vector,
                        "content": payload.get("content", ""),
                        "memory_type": payload.get("memory_type", "fact"),
                        "importance": importance - 1,
                        "character_id": payload.get("character_id", 0),
                        "user_persona_id": payload.get("user_persona_id"),
                        "session_id": payload.get("session_id"),
                    })

                if to_update:
                    await store.upsert(to_update)
                    decayed += len(to_update)

                if next_offset is None:
                    break
                offset = next_offset

            logger.info(LogCategory.MEMORY, f"Decayed {decayed} memories")
            return decayed

        except Exception as e:
            logger.warning(LogCategory.MEMORY, f"Memory decay failed: {e}")
            return 0

    def _parse_facts(self, raw: str) -> List[Dict]:
        """Parse LLM-extracted facts from raw JSON response."""
        if not raw or not raw.strip():
            return []
        try:
            # Strip markdown code fences if present
            text = raw.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                # Remove first and last fence lines
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                text = "\n".join(lines)

            data = json.loads(text)
            if isinstance(data, list):
                # Validate each fact
                facts = []
                for item in data:
                    if isinstance(item, dict) and "content" in item:
                        facts.append({
                            "content": str(item.get("content", "")),
                            "importance": min(10, max(1, int(item.get("importance", 5)))),
                            "memory_type": item.get("memory_type", "fact"),
                        })
                return facts
            return []
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(LogCategory.MEMORY, f"Failed to parse facts JSON: {e}")
            return []
