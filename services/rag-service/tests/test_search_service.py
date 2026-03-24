"""Unit tests for search orchestration service."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.search_service import SearchService


@pytest.mark.asyncio
async def test_search_uses_hybrid_retriever_when_enabled(monkeypatch: pytest.MonkeyPatch):
    service = SearchService()
    fake_retriever = AsyncMock(return_value=[{"id": 1, "content": "alpha", "score": 0.92, "similarity": 0.92}])
    def fake_cls(embedding_service, db_session):
        return SimpleNamespace(retrieve=fake_retriever)

    monkeypatch.setattr("app.services.search_service.HybridRetriever", fake_cls)
    monkeypatch.setattr(type(service), "embedding_service", property(lambda self: object()))
    monkeypatch.setattr(type(service), "reranker", property(lambda self: SimpleNamespace(rerank=lambda query, rows, top_k: rows[:top_k])))

    result = await service.search(
        project_id=None,
        rag_collection_id="rag-1",
        query="test query",
        top_k=5,
        threshold=0.7,
        db=AsyncMock(),
    )

    assert result[0]["id"] == 1
    fake_retriever.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_uses_vector_fallback_when_hybrid_disabled():
    service = SearchService()
    service._vector_search = AsyncMock(  # type: ignore[method-assign]
        return_value=[
            {"id": 1, "content": "alpha", "score": 0.9, "similarity": 0.9},
            {"id": 2, "content": "beta", "score": 0.6, "similarity": 0.6},
        ]
    )

    result = await service.search(
        project_id=None,
        rag_collection_id="rag-1",
        query="test query",
        top_k=5,
        threshold=0.7,
        db=AsyncMock(),
        use_hybrid=False,
        use_reranker=False,
    )

    assert [row["id"] for row in result] == [1]
    service._vector_search.assert_awaited_once()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_search_uses_query_rewrite_when_enabled():
    service = SearchService()
    service._rewriter = SimpleNamespace(rewrite=AsyncMock(return_value="rewritten query"))  # type: ignore[assignment]
    service._vector_search = AsyncMock(  # type: ignore[method-assign]
        return_value=[{"id": 1, "content": "alpha", "score": 0.95, "similarity": 0.95}]
    )

    await service.search(
        project_id=SimpleNamespace(),
        query="original query",
        top_k=5,
        threshold=0.7,
        db=AsyncMock(),
        use_hybrid=False,
        use_reranker=False,
        use_query_rewrite=True,
    )

    service.rewriter.rewrite.assert_awaited_once_with("original query", mode="expand")
    service._vector_search.assert_awaited_once()  # type: ignore[attr-defined]
    _, kwargs = service._vector_search.await_args  # type: ignore[attr-defined]
    assert kwargs["query"] == "rewritten query"


@pytest.mark.asyncio
async def test_search_uses_reranker_when_enabled():
    service = SearchService()
    service._vector_search = AsyncMock(  # type: ignore[method-assign]
        return_value=[
            {"id": 1, "content": "alpha", "score": 0.8, "similarity": 0.8},
            {"id": 2, "content": "beta", "score": 0.7, "similarity": 0.7},
        ]
    )
    service._reranker = SimpleNamespace(  # type: ignore[assignment]
        rerank=lambda query, rows, top_k: [
            {**rows[1], "score": 0.99, "similarity": 0.99},
            {**rows[0], "score": 0.51, "similarity": 0.51},
        ][:top_k]
    )

    result = await service.search(
        project_id=SimpleNamespace(),
        query="query",
        top_k=1,
        threshold=0.7,
        db=AsyncMock(),
        use_hybrid=False,
        use_reranker=True,
    )

    assert result == [{"id": 2, "content": "beta", "score": 0.99, "similarity": 0.99}]


@pytest.mark.asyncio
async def test_search_filters_below_threshold_after_rerank():
    service = SearchService()
    service._vector_search = AsyncMock(  # type: ignore[method-assign]
        return_value=[{"id": 1, "content": "alpha", "score": 0.8, "similarity": 0.8}]
    )
    service._reranker = SimpleNamespace(  # type: ignore[assignment]
        rerank=lambda query, rows, top_k: [{**rows[0], "score": 0.3, "similarity": 0.3}]
    )

    result = await service.search(
        project_id=SimpleNamespace(),
        query="query",
        top_k=5,
        threshold=0.7,
        db=AsyncMock(),
        use_hybrid=False,
    )

    assert result == []


@pytest.mark.asyncio
async def test_list_chunks_returns_ordered_rows():
    service = SearchService()
    fake_chunks = [
        SimpleNamespace(id=1, file_path="a.md", chunk_index=0, token_count=10),
        SimpleNamespace(id=2, file_path="a.md", chunk_index=1, token_count=12),
    ]
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: fake_chunks))

    result = await service.list_chunks(SimpleNamespace(), db)

    assert result == [
        {"id": 1, "file_path": "a.md", "chunk_index": 0, "token_count": 10},
        {"id": 2, "file_path": "a.md", "chunk_index": 1, "token_count": 12},
    ]


@pytest.mark.asyncio
async def test_delete_chunk_returns_false_when_missing():
    service = SearchService()
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: None)

    deleted = await service.delete_chunk(SimpleNamespace(), 123, db)

    assert deleted is False
    db.delete.assert_not_called()


@pytest.mark.asyncio
async def test_delete_chunk_deletes_and_commits_when_found():
    service = SearchService()
    db = AsyncMock()
    chunk = SimpleNamespace(id=5)
    db.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: chunk)

    deleted = await service.delete_chunk(SimpleNamespace(), 5, db)

    assert deleted is True
    db.delete.assert_awaited_once_with(chunk)
    db.commit.assert_awaited_once()
