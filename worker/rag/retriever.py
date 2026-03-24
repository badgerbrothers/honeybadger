"""Similarity search and context retrieval."""
from typing import Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
try:
    from db_models import DocumentChunk
except ModuleNotFoundError:  # pragma: no cover - package-import fallback
    from worker.db_models import DocumentChunk
from .embeddings import EmbeddingService
from shared.rag.retrieval_core import VectorRetrievalCore, build_scope_filters


class DocumentRetriever(VectorRetrievalCore):
    """Service for retrieving similar document chunks."""

    def __init__(self, embedding_service: EmbeddingService, db_session: AsyncSession):
        super().__init__(embedding_service)
        self.db_session = db_session

    async def retrieve(
        self,
        query: str,
        project_id: str | None = None,
        *,
        rag_collection_id: str | None = None,
        top_k: int = 5,
        threshold: float = 0.7,
    ) -> List[Dict]:
        """Retrieve similar chunks for a query.

        Args:
            query: Search query
            project_id: Project ID scope (fallback when rag_collection_id is not set)
            rag_collection_id: Global RAG scope (priority over project_id)
            top_k: Number of results to return
            threshold: Minimum similarity score (0-1)

        Returns:
            List of chunks with similarity scores
        """
        query_embedding = await self._generate_query_embedding(query)

        results = await self._search_similar_chunks(
            query_embedding,
            project_id=project_id,
            rag_collection_id=rag_collection_id,
            top_k=top_k,
            threshold=threshold,
        )

        return results

    async def _generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for query."""
        return await self.generate_query_embedding(query)

    async def _search_similar_chunks(
        self,
        embedding: List[float],
        *,
        project_id: str | None,
        rag_collection_id: str | None,
        top_k: int,
        threshold: float,
    ) -> List[Dict]:
        """Search for similar chunks using cosine similarity."""
        scope_filters = build_scope_filters(
            DocumentChunk,
            project_id=project_id,
            rag_collection_id=rag_collection_id,
        )

        query = select(
            DocumentChunk,
            (1 - DocumentChunk.embedding.cosine_distance(embedding)).label("similarity")
        ).where(
            *scope_filters
        ).order_by(
            DocumentChunk.embedding.cosine_distance(embedding)
        ).limit(top_k)

        result = await self.db_session.execute(query)
        rows = self.format_scored_rows(result.all())
        return self.filter_results(rows, threshold=threshold)
