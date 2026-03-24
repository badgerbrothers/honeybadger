"""Shared retrieval helpers for vector search and hybrid ranking."""

from __future__ import annotations

from typing import Any, Sequence


def resolve_scope(
    *,
    project_id: Any,
    rag_collection_id: Any,
) -> tuple[str, Any]:
    """Resolve retrieval scope preference."""
    if rag_collection_id is not None:
        return "rag_collection_id", rag_collection_id
    if project_id is not None:
        return "project_id", project_id
    raise ValueError("Either rag_collection_id or project_id must be provided")


def build_scope_filters(
    model: Any,
    *,
    project_id: Any,
    rag_collection_id: Any,
) -> list[Any]:
    """Build simple equality filters for project or collection scope."""
    scope_name, scope_value = resolve_scope(
        project_id=project_id,
        rag_collection_id=rag_collection_id,
    )
    return [getattr(model, scope_name) == scope_value]


class VectorRetrievalCore:
    """Shared vector retrieval behavior without DB-specific query construction."""

    def __init__(self, embedding_service: Any):
        self.embedding_service = embedding_service

    async def generate_query_embedding(self, query: str) -> list[float]:
        """Generate an embedding for a retrieval query."""
        return await self.embedding_service.generate_embedding(query)

    @staticmethod
    def format_scored_rows(rows: Sequence[tuple[Any, Any]]) -> list[dict[str, Any]]:
        """Convert `(chunk, score)` rows into standard retrieval payloads."""
        results: list[dict[str, Any]] = []
        for chunk, score in rows:
            numeric_score = float(score)
            results.append(
                {
                    "id": chunk.id,
                    "content": chunk.content,
                    "file_path": chunk.file_path,
                    "chunk_index": chunk.chunk_index,
                    "score": numeric_score,
                    "similarity": numeric_score,
                    "metadata": chunk.chunk_metadata,
                }
            )
        return results

    @staticmethod
    def filter_results(
        rows: Sequence[dict[str, Any]],
        *,
        threshold: float,
        score_key: str = "similarity",
    ) -> list[dict[str, Any]]:
        """Filter scored retrieval rows by a threshold."""
        return [row for row in rows if float(row.get(score_key, 0.0)) >= threshold]


def reciprocal_rank_fusion(
    vector_results: Sequence[dict[str, Any]],
    fulltext_results: Sequence[dict[str, Any]],
    *,
    k: int = 60,
) -> list[dict[str, Any]]:
    """Fuse ranked retrieval lists with Reciprocal Rank Fusion."""
    fused: dict[Any, dict[str, Any]] = {}

    for rank, item in enumerate(vector_results, start=1):
        chunk_id = item["id"]
        entry = fused.setdefault(
            chunk_id,
            {"chunk": item["chunk"], "score": 0.0, "sources": set()},
        )
        entry["score"] += 1.0 / (k + rank)
        entry["sources"].add(item["source"])

    for rank, item in enumerate(fulltext_results, start=1):
        chunk_id = item["id"]
        entry = fused.setdefault(
            chunk_id,
            {"chunk": item["chunk"], "score": 0.0, "sources": set()},
        )
        entry["score"] += 1.0 / (k + rank)
        entry["sources"].add(item["source"])

    sorted_rows = sorted(fused.values(), key=lambda row: row["score"], reverse=True)
    max_score = sorted_rows[0]["score"] if sorted_rows else 0.0

    results: list[dict[str, Any]] = []
    for row in sorted_rows:
        chunk = row["chunk"]
        normalized = (row["score"] / max_score) if max_score > 0 else 0.0
        results.append(
            {
                "id": chunk.id,
                "content": chunk.content,
                "file_path": chunk.file_path,
                "chunk_index": chunk.chunk_index,
                "score": float(normalized),
                "similarity": float(normalized),
                "raw_score": float(row["score"]),
                "metadata": chunk.chunk_metadata,
                "sources": sorted(row["sources"]),
            }
        )

    return results
