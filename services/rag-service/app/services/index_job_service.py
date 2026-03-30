"""Index job orchestration service for rag-service control-plane flows."""
from __future__ import annotations

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_index_job import DocumentIndexJob, DocumentIndexStatus
from app.models.project import ProjectNode
from app.services.queue_service import queue_service

logger = structlog.get_logger(__name__)


class IndexJobService:
    """Create and enqueue document indexing jobs."""

    async def schedule_indexing(
        self,
        *,
        storage_path: str,
        file_name: str,
        db: AsyncSession,
        project_id: uuid.UUID | None = None,
        project_node_id: uuid.UUID | None = None,
        rag_collection_id: uuid.UUID | None = None,
    ) -> DocumentIndexJob:
        """Create a new indexing job for a project node or a global RAG file."""
        if project_id is None and rag_collection_id is None:
            raise ValueError("Either project_id or rag_collection_id must be provided")

        job = DocumentIndexJob(
            project_id=project_id,
            project_node_id=project_node_id,
            rag_collection_id=rag_collection_id,
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
                project_id=str(project_id) if project_id else None,
                project_node_id=str(project_node_id) if project_node_id else None,
                rag_collection_id=str(rag_collection_id) if rag_collection_id else None,
                job_id=str(job.id),
                error=str(exc),
                exc_info=True,
            )
            job.status = DocumentIndexStatus.FAILED
            job.error_code = "queue_publish_failed"
            job.error_message = "queue_publish_failed"
            job.failed_step = "publish"
            await db.commit()
            await db.refresh(job)
            raise
        return job

    async def requeue_node(
        self,
        project_id: uuid.UUID,
        node_id: uuid.UUID,
        db: AsyncSession,
    ) -> DocumentIndexJob | None:
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
            rag_collection_id=None,
            storage_path=node.path,
            file_name=node.name,
            db=db,
        )


index_job_service = IndexJobService()
