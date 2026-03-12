"""Similarity search and context retrieval."""
from typing import List, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .embeddings import EmbeddingService


class DocumentRetriever:
    """Service for retrieving similar document chunks."""

    def __init__(self, embedding_service: EmbeddingService, db_session: AsyncSession):
        self.embedding_service = embedding_service
        self.db_session = db_session

    async def retrieve(
        self,
        query: str,
        project_id: str,
        top_k: int = 5,
        threshold: float = 0.7
    ) -> List[Dict]:
        """Retrieve similar chunks for a query.

        Args:
            query: Search query
            project_id: Project ID to filter by
            top_k: Number of results to return
            threshold: Minimum similarity score (0-1)

        Returns:
            List of chunks with similarity scores
        """
        # Generate query embedding
        query_embedding = await self._generate_query_embedding(query)

        # Search similar chunks
        results = await self._search_similar_chunks(
            query_embedding, project_id, top_k, threshold
        )

        return results

    async def _generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for query."""
        return await self.embedding_service.generate_embedding(query)

    async def _search_similar_chunks(
        self,
        embedding: List[float],
        project_id: str,
        top_k: int,
        threshold: float
    ) -> List[Dict]:
        """Search for similar chunks using cosine similarity."""
        from app.models.document_chunk import DocumentChunk

        # pgvector cosine distance: 1 - cosine_similarity
        # So similarity = 1 - distance
        query = select(
            DocumentChunk,
            (1 - DocumentChunk.embedding.cosine_distance(embedding)).label("similarity")
        ).where(
            DocumentChunk.project_id == project_id
        ).order_by(
            DocumentChunk.embedding.cosine_distance(embedding)
        ).limit(top_k)

        result = await self.db_session.execute(query)
        rows = result.all()

        # Filter by threshold and format results
        chunks = []
        for chunk, similarity in rows:
            if similarity >= threshold:
                chunks.append({
                    "id": chunk.id,
                    "content": chunk.content,
                    "file_path": chunk.file_path,
                    "chunk_index": chunk.chunk_index,
                    "similarity": float(similarity),
                    "metadata": chunk.chunk_metadata
                })

        return chunks
