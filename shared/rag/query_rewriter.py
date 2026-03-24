"""Optional query rewriting with LLM + in-memory TTL cache."""
from __future__ import annotations

import time

import structlog
from openai import AsyncOpenAI

logger = structlog.get_logger(__name__)


class QueryRewriter:
    """LLM-based query optimization layer."""

    def __init__(
        self,
        *,
        api_key: str | None,
        model: str = "gpt-4o-mini",
        ttl_seconds: int = 300,
        max_cache_size: int = 500,
    ):
        self.model = model
        self.ttl_seconds = ttl_seconds
        self.max_cache_size = max_cache_size
        self._cache: dict[str, tuple[float, str]] = {}
        self._client = AsyncOpenAI(api_key=api_key) if api_key else None

    async def rewrite(self, query: str, mode: str = "expand") -> str:
        """Rewrite query and fall back to the original query on failure."""
        if self._client is None:
            return query

        key = f"{mode}:{query.strip().lower()}"
        cached = self._cache.get(key)
        now = time.time()
        if cached and cached[0] > now:
            return cached[1]

        prompt = self._build_prompt(query, mode)
        if prompt is None:
            return query

        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=96,
            )
            content = (response.choices[0].message.content or "").strip()
            rewritten = content if content else query
            self._cache[key] = (now + self.ttl_seconds, rewritten)
            self._evict_if_needed()
            logger.info("query_rewritten", mode=mode, original=query, rewritten=rewritten)
            return rewritten
        except Exception as exc:
            logger.warning("query_rewrite_failed_fallback", error=str(exc), mode=mode)
            return query

    def _build_prompt(self, query: str, mode: str) -> str | None:
        if mode == "expand":
            return (
                "Rewrite this search query for document retrieval. "
                "Add concise synonyms and related terms. "
                "Return only the rewritten query.\n\n"
                f"Query: {query}"
            )
        if mode == "clarify":
            return (
                "Clarify this ambiguous search query into a specific retrievable query. "
                "Return only one clarified query.\n\n"
                f"Query: {query}"
            )
        return None

    def _evict_if_needed(self) -> None:
        if len(self._cache) <= self.max_cache_size:
            return
        oldest_key = min(self._cache, key=lambda k: self._cache[k][0])
        self._cache.pop(oldest_key, None)
