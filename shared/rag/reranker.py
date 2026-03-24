"""Reranking service based on Cross-Encoder models."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class RerankerService:
    """Cross-encoder reranker with graceful degradation."""

    def __init__(self, model_name: str = "BAAI/bge-reranker-base", model: Any | None = None):
        self.model_name = model_name
        self._model = model

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name)
            logger.info("reranker_model_loaded", model_name=self.model_name)
        return self._model

    def rerank(
        self,
        query: str,
        candidates: Sequence[dict[str, Any]],
        *,
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Rerank candidate chunks and return top_k results."""
        if not candidates:
            return []

        try:
            model = self._get_model()
            pairs = [(query, item["content"]) for item in candidates]
            scores = model.predict(pairs)
        except Exception as exc:
            logger.warning("reranker_unavailable_fallback", error=str(exc))
            return list(candidates[:top_k])

        ranked: list[dict[str, Any]] = []
        for item, score in zip(candidates, scores):
            copy_item = dict(item)
            copy_item["rerank_score"] = float(score)
            copy_item["score"] = float(score)
            copy_item["similarity"] = float(score)
            ranked.append(copy_item)

        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked[:top_k]
