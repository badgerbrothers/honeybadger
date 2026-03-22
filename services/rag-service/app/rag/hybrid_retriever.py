"""Hybrid retrieval combining vector and full-text search."""
from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_chunk import DocumentChunk
from app.rag.embeddings import EmbeddingService

logger = structlog.get_logger(__name__)


class HybridRetriever:
    """Hybrid search using vector similarity + PostgreSQL full-text search."""

    def __init__(self, embedding_service: EmbeddingService, db_session: AsyncSession):
        self.embedding_service = embedding_service
        self.db_session = db_session

    async def retrieve(
        self,
        query: str,
        project_id: uuid.UUID | str | None = None,
        rag_collection_id: uuid.UUID | str | None = None,
        *,
        top_k: int = 5,
        candidate_k: int = 50,
    ) -> list[dict[str, Any]]:
        """Retrieve and fuse candidates via Reciprocal Rank Fusion (RRF)."""
        vector_results = await self._vector_search(
            query,
            project_id=project_id,
            rag_collection_id=rag_collection_id,
            top_k=candidate_k,
        )
        fulltext_results = await self._fulltext_search(
            query,
            project_id=project_id,
            rag_collection_id=rag_collection_id,
            top_k=candidate_k,
        )
        fused = self._rrf_fusion(vector_results, fulltext_results, k=60)
        return fused[:top_k]

    async def _vector_search(
        self,
        query: str,
        *,
        project_id: uuid.UUID | str | None,
        rag_collection_id: uuid.UUID | str | None,
        top_k: int,
    ) -> list[dict[str, Any]]:
        embedding = await self.embedding_service.generate_embedding(query)
        scope_filters = self._scope_filters(
            project_id=project_id,
            rag_collection_id=rag_collection_id,
        )
        stmt = (
            select(
                DocumentChunk,
                (1 - DocumentChunk.embedding.cosine_distance(embedding)).label("score"),
            )
            .where(*scope_filters)
            .order_by(DocumentChunk.embedding.cosine_distance(embedding))
            .limit(top_k)
        )
        result = await self.db_session.execute(stmt)
        return [
            {"id": chunk.id, "chunk": chunk, "score": float(score), "source": "vector"}
            for chunk, score in result.all()
        ]

    async def _fulltext_search(
        self,
        query: str,
        *,
        project_id: uuid.UUID | str | None,
        rag_collection_id: uuid.UUID | str | None,
        top_k: int,
    ) -> list[dict[str, Any]]:
        ts_query = func.websearch_to_tsquery("english", query)
        rank_expr = func.ts_rank_cd(DocumentChunk.text_search_vector, ts_query)
        scope_filters = self._scope_filters(
            project_id=project_id,
            rag_collection_id=rag_collection_id,
        )
        stmt = (
            select(DocumentChunk, rank_expr.label("score"))
            .where(
                *scope_filters,
                DocumentChunk.text_search_vector.is_not(None),
                DocumentChunk.text_search_vector.op("@@")(ts_query),
            )
            .order_by(rank_expr.desc())
            .limit(top_k)
        )
        result = await self.db_session.execute(stmt)
        return [
            {"id": chunk.id, "chunk": chunk, "score": float(score), "source": "fulltext"}
            for chunk, score in result.all()
        ]

    def _rrf_fusion(
        self,
        vector_results: list[dict[str, Any]],
        fulltext_results: list[dict[str, Any]],
        *,
        k: int = 60,
    ) -> list[dict[str, Any]]:
        """Fuse two ranked lists with Reciprocal Rank Fusion."""
        fused: dict[int, dict[str, Any]] = {}

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

        sorted_rows = sorted(fused.values(), key=lambda x: x["score"], reverse=True)
        max_score = sorted_rows[0]["score"] if sorted_rows else 0.0
        rows = []
        for row in sorted_rows:
            chunk = row["chunk"]
            normalized = (row["score"] / max_score) if max_score > 0 else 0.0
            rows.append(
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
        logger.info(
            "hybrid_retrieval_fused",
            vector_candidates=len(vector_results),
            fulltext_candidates=len(fulltext_results),
            fused_candidates=len(rows),
        )
        return rows

    @staticmethod
    def _scope_filters(
        *,
        project_id: uuid.UUID | str | None,
        rag_collection_id: uuid.UUID | str | None,
    ) -> list[Any]:
        if rag_collection_id is not None:
            return [DocumentChunk.rag_collection_id == rag_collection_id]
        if project_id is not None:
            return [DocumentChunk.project_id == project_id]
        raise ValueError("Either rag_collection_id or project_id must be provided")
