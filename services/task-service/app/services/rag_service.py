"""RAG orchestration service for backend control-plane operations."""
from __future__ import annotations

import uuid

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_chunk import DocumentChunk
from app.models.document_index_job import DocumentIndexJob, DocumentIndexStatus
from app.models.project import ProjectNode
from app.services.memory_service import memory_service
from app.services.queue_service import queue_service

logger = structlog.get_logger(__name__)


class RagService:
    """Coordinates indexing jobs and chunk retrieval for project files."""

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
    ) -> list[dict]:
        """Search indexed chunks for a project."""
        query_embedding = await memory_service.generate_embedding(query)
        result = await db.execute(
            select(
                DocumentChunk,
                (1 - DocumentChunk.embedding.cosine_distance(query_embedding)).label("similarity"),
            )
            .where(DocumentChunk.project_id == project_id)
            .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        )

        chunks: list[dict] = []
        for chunk, similarity in result.all():
            if similarity >= threshold:
                chunks.append(
                    {
                        "id": chunk.id,
                        "content": chunk.content,
                        "file_path": chunk.file_path,
                        "chunk_index": chunk.chunk_index,
                        "similarity": float(similarity),
                        "metadata": chunk.chunk_metadata,
                    }
                )
        return chunks

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
