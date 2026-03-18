"""RAG orchestration service for backend control-plane operations."""
from __future__ import annotations

import uuid

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.document_chunk import DocumentChunk
from app.models.document_index_job import DocumentIndexJob, DocumentIndexStatus
from app.models.project import ProjectNode
from app.services.queue_service import queue_service
from app.rag.embeddings import EmbeddingService
from app.rag.hybrid_retriever import HybridRetriever
from app.rag.query_rewriter import QueryRewriter
from app.rag.reranker import RerankerService

logger = structlog.get_logger(__name__)


class RagService:
    """Coordinates indexing jobs and chunk retrieval for project files."""

    def __init__(self) -> None:
        self.embedding_service = EmbeddingService(
            api_key=settings.openai_api_key,
            model=settings.embedding_model,
            dimension=settings.embedding_dimension,
        )
        self.reranker = RerankerService()
        self.rewriter = QueryRewriter(api_key=settings.openai_api_key)

    async def schedule_indexing(
        self,
        project_id: uuid.UUID,
        project_node_id: uuid.UUID,
        storage_path: str,
        file_name: str,
        db: AsyncSession,
    ) -> DocumentIndexJob:
        """Create a new indexing job for a project file."""
        job = DocumentIndexJob(
            project_id=project_id,
            project_node_id=project_node_id,
            storage_path=storage_path,
            file_name=file_name,
            status=DocumentIndexStatus.PENDING,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        try:
            await queue_service.publish_index_job(job.id)
        except Exception as exc:
            logger.error(
                "index_job_publish_failed",
                project_id=str(project_id),
                project_node_id=str(project_node_id),
                job_id=str(job.id),
                error=str(exc),
                exc_info=True,
            )
            job.status = DocumentIndexStatus.FAILED
            job.error_message = "queue_publish_failed"
            await db.commit()
            await db.refresh(job)
            raise
        return job

    async def search(
        self,
        project_id: uuid.UUID,
        query: str,
        top_k: int,
        threshold: float,
        db: AsyncSession,
        *,
        use_hybrid: bool = True,
        use_reranker: bool = True,
        use_query_rewrite: bool = False,
    ) -> list[dict]:
        """Search indexed chunks for a project with optional RAG optimizations."""
        effective_query = query
        if use_query_rewrite:
            effective_query = await self.rewriter.rewrite(query, mode="expand")

        if use_hybrid:
            retriever = HybridRetriever(self.embedding_service, db)
            results = await retriever.retrieve(
                effective_query,
                project_id=project_id,
                top_k=max(top_k, 50),
                candidate_k=50,
            )
        else:
            results = await self._vector_search(
                project_id=project_id,
                query=effective_query,
                top_k=50,
                db=db,
            )

        if use_reranker and results:
            results = self.reranker.rerank(effective_query, results, top_k=top_k)
        else:
            results = results[:top_k]

        filtered = [row for row in results if float(row.get("score", 0.0)) >= threshold]
        return filtered[:top_k]

    async def _vector_search(
        self,
        *,
        project_id: uuid.UUID,
        query: str,
        top_k: int,
        db: AsyncSession,
    ) -> list[dict]:
        query_embedding = await self.embedding_service.generate_embedding(query)
        stmt = (
            select(
                DocumentChunk,
                (1 - DocumentChunk.embedding.cosine_distance(query_embedding)).label("score"),
            )
            .where(DocumentChunk.project_id == project_id)
            .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        )
        result = await db.execute(stmt)

        return [
            {
                "id": chunk.id,
                "content": chunk.content,
                "file_path": chunk.file_path,
                "chunk_index": chunk.chunk_index,
                "score": float(score),
                "similarity": float(score),
                "metadata": chunk.chunk_metadata,
            }
            for chunk, score in result.all()
        ]

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

    async def requeue_node(self, project_id: uuid.UUID, node_id: uuid.UUID, db: AsyncSession) -> DocumentIndexJob | None:
        """Schedule indexing for an existing project file node."""
        result = await db.execute(
            select(ProjectNode).where(
                ProjectNode.id == node_id,
                ProjectNode.project_id == project_id,
            )
        )
        node = result.scalar_one_or_none()
        if node is None:
            return None
        return await self.schedule_indexing(
            project_id=project_id,
            project_node_id=node.id,
            storage_path=node.path,
            file_name=node.name,
            db=db,
        )

    async def clear_project_chunks(self, project_id: uuid.UUID, db: AsyncSession) -> None:
        """Delete all chunks for a project."""
        await db.execute(delete(DocumentChunk).where(DocumentChunk.project_id == project_id))
        await db.commit()


rag_service = RagService()
