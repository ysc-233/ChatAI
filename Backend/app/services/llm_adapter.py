"""LLM Adapter - stream chat completions."""
import json
import re
import asyncio
import time
from typing import AsyncIterator, List, Dict, Optional

import httpx

from app.config import get_settings
from app.core.logging import logger, LogCategory

settings = get_settings()

SEARCH_DECISION_PROMPT = """你是一个搜索意图判断器。判断用户消息是否需要联网搜索才能准确回答。

需要搜索的情况：
- 实时信息（新闻、天气、股价、赛事、最新动态）
- 事实查询（"XX是什么""XX的CEO是谁""XX什么时候成立的"）
- 最新数据（版本号、排行榜、统计数据）
- 用户明确要求搜索/查资料

不需要搜索的情况：
- 闲聊、情感交流、角色扮演
- 纯主观问题（"你觉得怎么样""你喜欢什么"）
- 已有知识可覆盖的一般常识
- 对角色设定/个人经历的询问

用户消息：{user_message}

角色设定（参考）：{character_brief}

请只回复一个词：SEARCH 或 NO_SEARCH。
如果是 SEARCH，后面跟一个冒号和优化后的搜索关键词。
示例：SEARCH: 2026年7月中国天气"""


class LLMAdapter:
    """Adapter for LLM API streaming."""

    def __init__(self):
        self.api_url = settings.LLM_API_URL
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL_NAME
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.temperature = settings.LLM_TEMPERATURE
        self.timeout = settings.LLM_TIMEOUT

    async def complete_chat(self, session, user_message: str, history: List[Dict],
                            search_results: Optional[str] = None,
                            client_time: Optional[str] = None) -> str:
        """Non-streaming LLM completion - wait for full response."""
        if not self.api_url or not self.api_key:
            return "（未配置 LLM API，请设置环境变量 LLM_API_URL 和 LLM_API_KEY）"

        messages = await self._build_messages(session, user_message, history,
                                              search_results=search_results,
                                              client_time=client_time)
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        start_time = time.time()
        try:
            api_url = self.api_url
            if not api_url.endswith('/chat/completions'):
                if api_url.endswith('/'):
                    api_url = api_url + 'v1/chat/completions'
                elif api_url.endswith('/v1'):
                    api_url = api_url + '/chat/completions'
                else:
                    api_url = api_url + '/v1/chat/completions'

            async with httpx.AsyncClient(timeout=self.timeout + 120) as client:
                resp = await client.post(api_url, json=payload, headers=headers)
                if resp.status_code != 200:
                    body = resp.text
                    raise Exception(f"LLM API error {resp.status_code}: {body}")

                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

            duration = (time.time() - start_time) * 1000
            logger.llm_call(
                model=self.model,
                prompt_tokens=len(user_message) // 2,
                completion_tokens=len(content) // 2,
                duration_ms=duration,
                success=True,
            )
            return content
        except Exception as e:
            logger.error(LogCategory.LLM, f"LLM completion failed: {e}", {"model": self.model})
            raise

    async def stream_chat(self, session, user_message: str, history: List[Dict],
                          search_results: Optional[str] = None) -> AsyncIterator[str]:
        """Stream LLM response (deprecated, kept for compatibility)."""
        if not self.api_url or not self.api_key:
            yield "（未配置 LLM API，请设置环境变量 LLM_API_URL 和 LLM_API_KEY）"
            return

        messages = await self._build_messages(session, user_message, history,
                                              search_results=search_results)
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": True,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        start_time = time.time()
        try:
            # Ensure full endpoint URL
            api_url = self.api_url
            if not api_url.endswith('/chat/completions'):
                if api_url.endswith('/'):
                    api_url = api_url + 'v1/chat/completions'
                elif api_url.endswith('/v1'):
                    api_url = api_url + '/chat/completions'
                else:
                    api_url = api_url + '/v1/chat/completions'

            async with httpx.AsyncClient(timeout=self.timeout + 10) as client:
                async with client.stream("POST", api_url, json=payload, headers=headers) as response:
                    if response.status_code != 200:
                        body = await response.aread()
                        raise Exception(f"LLM API error {response.status_code}: {body.decode()}")

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data.strip() == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if delta:
                                    yield delta
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            logger.error(LogCategory.LLM, f"LLM stream error: {e}", {"model": self.model})
            raise

    async def _build_messages(self, session, user_message: str, history: List[Dict],
                              search_results: Optional[str] = None,
                              client_time: Optional[str] = None) -> List[Dict]:
        """Build messages for LLM API."""
        from app.services.context_engine import ContextEngine
        engine = ContextEngine()
        return await engine.build_prompt(session, user_message, history,
                                         search_results=search_results,
                                         client_time=client_time)

    async def cheap_completion(self, prompt: str, max_tokens: int = 512) -> str:
        """Non-streaming cheap completion for internal tasks."""
        if not self.api_url or not self.api_key:
            return ""

        payload = {
            "model": settings.LLM_MODEL_NAME_CHEAP,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.5,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            # Ensure full endpoint URL
            api_url = self.api_url
            if not api_url.endswith('/chat/completions'):
                if api_url.endswith('/'):
                    api_url = api_url + 'v1/chat/completions'
                elif api_url.endswith('/v1'):
                    api_url = api_url + '/chat/completions'
                else:
                    api_url = api_url + '/v1/chat/completions'

            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(api_url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception as e:
            logger.error(LogCategory.LLM, f"Cheap completion failed: {e}")
            return ""

    async def judge_search_intent(
        self, user_message: str, character_brief: str
    ) -> tuple:
        """Judge whether user message needs web search.

        Uses cheap LLM for fast, low-cost intent classification.

        Args:
            user_message: the user's current message
            character_brief: brief character context (name + background, <200 chars)

        Returns:
            (need_search: bool, query: Optional[str])
            query is the optimized search keyword when need_search is True.
            Returns (False, None) on any exception.
        """
        prompt = SEARCH_DECISION_PROMPT.format(
            user_message=user_message[:500],
            character_brief=character_brief[:200],
        )
        try:
            raw = await self.cheap_completion(prompt, max_tokens=100)
            if not raw:
                return False, None

            raw = raw.strip()
            if raw.startswith("SEARCH:"):
                query = raw[7:].strip()
                # Sanitize: limit length, remove control chars
                query = re.sub(r'[\x00-\x1f\x7f]', '', query)[:200]
                if query:
                    return True, query
            return False, None
        except Exception as e:
            logger.debug(LogCategory.LLM, f"Search intent check failed: {e}")
            return False, None
