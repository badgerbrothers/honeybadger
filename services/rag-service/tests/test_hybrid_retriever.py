"""Unit tests for hybrid retrieval fusion."""
from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock

from app.rag.hybrid_retriever import HybridRetriever


@dataclass
class _Chunk:
    id: int
    content: str
    file_path: str
    chunk_index: int
    chunk_metadata: dict


def test_rrf_fusion_merges_and_normalizes_scores():
    retriever = HybridRetriever(embedding_service=AsyncMock(), db_session=AsyncMock())

    c1 = _Chunk(1, "alpha", "a.md", 0, {})
    c2 = _Chunk(2, "beta", "b.md", 0, {})
    c3 = _Chunk(3, "gamma", "c.md", 0, {})

    vector = [
        {"id": 1, "chunk": c1, "score": 0.9, "source": "vector"},
        {"id": 2, "chunk": c2, "score": 0.8, "source": "vector"},
    ]
    fulltext = [
        {"id": 2, "chunk": c2, "score": 0.9, "source": "fulltext"},
        {"id": 3, "chunk": c3, "score": 0.7, "source": "fulltext"},
    ]

    fused = retriever._rrf_fusion(vector, fulltext, k=60)

    assert len(fused) == 3
    assert fused[0]["id"] == 2
    assert fused[0]["sources"] == ["fulltext", "vector"]
    assert 0.0 <= fused[0]["score"] <= 1.0
    assert "raw_score" in fused[0]


def test_rrf_fusion_handles_empty_inputs():
    retriever = HybridRetriever(embedding_service=AsyncMock(), db_session=AsyncMock())
    assert retriever._rrf_fusion([], [], k=60) == []
