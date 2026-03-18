"""Unit tests for query rewriter."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.rag.query_rewriter import QueryRewriter


@pytest.mark.asyncio
async def test_query_rewriter_returns_original_when_disabled():
    rewriter = QueryRewriter(api_key=None)
    query = "ml retrieval"
    assert await rewriter.rewrite(query, mode="expand") == query


@pytest.mark.asyncio
async def test_query_rewriter_uses_cache():
    rewriter = QueryRewriter(api_key="dummy", ttl_seconds=60)

    create_mock = AsyncMock(
        return_value=SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="machine learning retrieval"))]
        )
    )
    rewriter._client = SimpleNamespace(  # type: ignore[assignment]
        chat=SimpleNamespace(completions=SimpleNamespace(create=create_mock))
    )

    q1 = await rewriter.rewrite("ml retrieval", mode="expand")
    q2 = await rewriter.rewrite("ml retrieval", mode="expand")

    assert q1 == q2
    assert create_mock.await_count == 1


@pytest.mark.asyncio
async def test_query_rewriter_fallback_on_llm_error():
    rewriter = QueryRewriter(api_key="dummy", ttl_seconds=60)
    rewriter._client = SimpleNamespace(  # type: ignore[assignment]
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=AsyncMock(side_effect=RuntimeError("boom")))
        )
    )
    query = "ambiguous query"
    assert await rewriter.rewrite(query, mode="clarify") == query
