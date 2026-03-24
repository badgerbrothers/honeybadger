"""Search orchestration service for rag-service retrieval APIs."""
from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.document_chunk import DocumentChunk
from app.rag.embeddings import EmbeddingService
from app.rag.hybrid_retriever import HybridRetriever
from app.rag.query_rewriter import QueryRewriter
from app.rag.reranker import RerankerService
from shared.rag.retrieval_core import VectorRetrievalCore, build_scope_filters


class SearchService:
    """Coordinate retrieval, query rewrite, reranking, and chunk management."""

    def __init__(self) -> None:
        self._embedding_service: EmbeddingService | None = None
        self._reranker: RerankerService | None = None
        self._rewriter: QueryRewriter | None = None

    @property
    def embedding_service(self) -> EmbeddingService:
        """Lazily create the embedding service used by search paths."""
        if self._embedding_service is None:
            self._embedding_service = EmbeddingService(
                api_key=settings.openai_api_key,
                model=settings.embedding_model,
                dimension=settings.embedding_dimension,
            )
        return self._embedding_service

    @property
    def reranker(self) -> RerankerService:
        """Lazily create the reranker service for search requests."""
        if self._reranker is None:
            self._reranker = RerankerService()
        return self._reranker

    @property
    def rewriter(self) -> QueryRewriter:
        """Lazily create the query rewriter for search requests."""
        if self._rewriter is None:
            self._rewriter = QueryRewriter(api_key=settings.openai_api_key)
        return self._rewriter

    async def search(
        self,
        project_id: uuid.UUID | None,
        query: str,
        top_k: int,
        threshold: float,
        db: AsyncSession,
        rag_collection_id: uuid.UUID | None = None,
        *,
        use_hybrid: bool = True,
        use_reranker: bool = True,
        use_query_rewrite: bool = False,
    ) -> list[dict]:
        """Search indexed chunks by rag_collection_id first, then project_id."""
        effective_query = query
        if use_query_rewrite:
            effective_query = await self.rewriter.rewrite(query, mode="expand")

        if use_hybrid:
            retriever = HybridRetriever(self.embedding_service, db)
            results = await retriever.retrieve(
                effective_query,
                project_id=project_id,
                rag_collection_id=rag_collection_id,
                top_k=max(top_k, 50),
                candidate_k=50,
            )
        else:
            results = await self._vector_search(
                project_id=project_id,
                rag_collection_id=rag_collection_id,
                query=effective_query,
                top_k=50,
                db=db,
            )

        if use_reranker and results:
            results = self.reranker.rerank(effective_query, results, top_k=top_k)
        else:
            results = results[:top_k]

        filtered = VectorRetrievalCore.filter_results(results, threshold=threshold, score_key="score")
        return filtered[:top_k]

    async def _vector_search(
        self,
        *,
        project_id: uuid.UUID | None,
        rag_collection_id: uuid.UUID | None,
        query: str,
        top_k: int,
        db: AsyncSession,
    ) -> list[dict]:
        query_embedding = await self.embedding_service.generate_embedding(query)
        filters = build_scope_filters(
            DocumentChunk,
            project_id=project_id,
            rag_collection_id=rag_collection_id,
        )

        stmt = (
            select(
                DocumentChunk,
                (1 - DocumentChunk.embedding.cosine_distance(query_embedding)).label("score"),
            )
            .where(*filters)
            .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        )
        result = await db.execute(stmt)

        return VectorRetrievalCore.format_scored_rows(result.all())

    async def list_chunks(self, project_id: uuid.UUID, db: AsyncSession) -> list[dict]:
        """List indexed chunks for a project."""
        result = await db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.project_id == project_id)
            .order_by(DocumentChunk.file_path, DocumentChunk.chunk_index)
        )
        chunks = result.scalars().all()
        return [
            {
                "id": chunk.id,
                "file_path": chunk.file_path,
                "chunk_index": chunk.chunk_index,
                "token_count": chunk.token_count,
            }
            for chunk in chunks
        ]

    async def delete_chunk(self, project_id: uuid.UUID, chunk_id: int, db: AsyncSession) -> bool:
        """Delete a single chunk for a project."""
        result = await db.execute(
            select(DocumentChunk).where(
                DocumentChunk.id == chunk_id,
                DocumentChunk.project_id == project_id,
            )
        )
        chunk = result.scalar_one_or_none()
        if not chunk:
            return False
        await db.delete(chunk)
        await db.commit()
        return True

    async def clear_project_chunks(self, project_id: uuid.UUID, db: AsyncSession) -> None:
        """Delete all chunks for a project."""
        await db.execute(delete(DocumentChunk).where(DocumentChunk.project_id == project_id))
        await db.commit()


search_service = SearchService()
