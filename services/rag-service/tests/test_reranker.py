"""Unit tests for reranker service."""
from __future__ import annotations

from app.rag.reranker import RerankerService


class _FakeModel:
    def __init__(self, scores):
        self._scores = scores

    def predict(self, pairs):
        assert len(pairs) == len(self._scores)
        return self._scores


class _BrokenModel:
    def predict(self, pairs):
        raise RuntimeError("model failure")


def test_reranker_sorts_candidates_by_score():
    service = RerankerService(model=_FakeModel([0.2, 0.9, 0.5]))
    candidates = [
        {"id": 1, "content": "one", "score": 0.1},
        {"id": 2, "content": "two", "score": 0.1},
        {"id": 3, "content": "three", "score": 0.1},
    ]

    ranked = service.rerank("query", candidates, top_k=2)

    assert [item["id"] for item in ranked] == [2, 3]
    assert "rerank_score" in ranked[0]
    assert ranked[0]["similarity"] == ranked[0]["score"]


def test_reranker_fallback_on_failure_returns_original_slice():
    service = RerankerService(model=_BrokenModel())
    candidates = [
        {"id": 1, "content": "one", "score": 0.4},
        {"id": 2, "content": "two", "score": 0.3},
    ]

    ranked = service.rerank("query", candidates, top_k=1)
    assert ranked == [candidates[0]]
