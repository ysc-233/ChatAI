"""Search Service - 博查 Bocha Web Search API adapter."""
import json
import re
import time
import asyncio
from typing import List, Dict, Optional

import httpx

from app.config import get_settings
from app.core.logging import logger, LogCategory

settings = get_settings()

# Limit concurrent search requests to avoid hitting Bocha QPS limits
_search_semaphore = asyncio.Semaphore(3)


class SearchResult:
    """Structured search result."""

    def __init__(self, title: str, url: str, snippet: str, summary: str = "",
                 site_name: str = "", date: str = ""):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.summary = summary
        self.site_name = site_name
        self.date = date


class SearchService:
    """博查 Web Search API adapter for AI Agent search."""

    def __init__(self):
        self.api_url = settings.SEARCH_API_URL
        self.api_key = settings.SEARCH_API_KEY
        self.timeout = settings.SEARCH_TIMEOUT
        self.result_count = settings.SEARCH_RESULT_COUNT

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    @staticmethod
    def _sanitize_query(query: str) -> str:
        """Sanitize search query: limit length, remove control characters."""
        # Limit to 200 chars
        query = query[:200].strip()
        # Remove control characters
        query = re.sub(r'[\x00-\x1f\x7f]', '', query)
        return query

    async def search(self, query: str, count: int = None) -> List[SearchResult]:
        """Execute search with QPS control and retry.

        Args:
            query: search query string
            count: max results (default: SEARCH_RESULT_COUNT)

        Returns:
            List of SearchResult, empty on failure
        """
        if not self.is_configured:
            logger.debug(LogCategory.LLM, "Search API not configured, skipping")
            return []

        query = self._sanitize_query(query)
        if not query:
            return []

        if count is None:
            count = self.result_count

        # QPS control: semaphore with 5s timeout
        try:
            acquired = await asyncio.wait_for(
                _search_semaphore.acquire(), timeout=5.0
            )
        except asyncio.TimeoutError:
            logger.warning(
                LogCategory.LLM,
                "Search concurrency limit reached, skipping search"
            )
            return []

        try:
            # Retry with exponential backoff, max 2 retries
            for attempt in range(3):
                try:
                    return await self._do_search(query, count)
                except Exception as e:
                    if attempt < 2:
                        wait = 2 ** attempt  # 1s, 2s
                        logger.warning(
                            LogCategory.LLM,
                            f"Search attempt {attempt + 1} failed: {e}, "
                            f"retrying in {wait}s"
                        )
                        await asyncio.sleep(wait)
                    else:
                        logger.error(
                            LogCategory.LLM,
                            f"Search failed after 3 attempts: {e}"
                        )
                        return []
            return []
        finally:
            _search_semaphore.release()

    async def _do_search(self, query: str, count: int) -> List[SearchResult]:
        """Execute a single search request."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "query": query,
            "count": count,
            "freshness": "noLimit",
            "summary": True,  # 请求长文本摘要，提供更丰富的上下文
        }

        start_time = time.time()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(self.api_url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        duration = (time.time() - start_time) * 1000
        results = self._parse_response(data)
        logger.info(
            LogCategory.LLM,
            f"Search: \"{query[:50]}\" returned {len(results)} results "
            f"({duration:.0f}ms)"
        )
        # 如果结果为 0，记录原始响应用于排查
        if not results:
            logger.debug(
                LogCategory.LLM,
                f"Search empty response: {json.dumps(data, ensure_ascii=False)[:500]}"
            )
        return results

    def _parse_response(self, data: dict) -> List[SearchResult]:
        """Parse Bocha API response into SearchResult list.

        Supports both response formats:
        - Bocha native: {"code": 200, "data": {"webPages": {"value": [...]}}}
        - Bing-compatible: {"webPages": {"value": [...]}}
        """
        results = []

        # 先尝试顶层 Bing-compatible 格式，再尝试 Bocha native data 包裹格式
        web_pages = data.get("webPages")
        if web_pages is None:
            web_pages = data.get("data", {}).get("webPages", {})

        values = web_pages.get("value", [])
        if not isinstance(values, list):
            return results

        for item in values[:self.result_count]:
            results.append(SearchResult(
                title=item.get("name", ""),
                url=item.get("url", ""),
                snippet=item.get("snippet", ""),
                summary=item.get("summary", ""),
                site_name=item.get("siteName", ""),
                date=item.get("dateLastCrawled", ""),
            ))
        return results

    def format_for_llm(self, results: List[SearchResult], max_chars: int = 2000) -> str:
        """Format search results as LLM-readable prompt text.

        Hard-limited to max_chars to avoid blowing up the prompt.
        """
        if not results:
            return ""

        lines = ["【联网搜索结果】以下是与用户问题相关的实时信息，请参考这些信息进行回答："]
        total = 0

        for i, r in enumerate(results, 1):
            # Use AI summary if available, otherwise snippet
            info = r.summary or r.snippet or ""
            line = f"\n{i}. **{r.title}**"
            if info:
                line += f"\n   {info}"
            if r.url:
                line += f"\n   来源: {r.site_name or r.url}"
            if r.date:
                line += f" | {r.date}"

            # Check if adding this entry exceeds limit
            if total + len(line) > max_chars:
                break
            lines.append(line)
            total += len(line)

        return "\n".join(lines)
