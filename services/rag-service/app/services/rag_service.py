"""Compatibility facade for legacy rag-service imports."""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.index_job_service import index_job_service
from app.services.search_service import search_service


class RagService:
    """Delegate legacy mixed responsibilities to the split service modules."""

    async def schedule_indexing(
        self,
        *,
        storage_path: str,
        file_name: str,
        db: AsyncSession,
        project_id: uuid.UUID | None = None,
        project_node_id: uuid.UUID | None = None,
        rag_collection_id: uuid.UUID | None = None,
    ):
        """Compatibility proxy for index scheduling."""
        return await index_job_service.schedule_indexing(
            storage_path=storage_path,
            file_name=file_name,
            db=db,
            project_id=project_id,
            project_node_id=project_node_id,
            rag_collection_id=rag_collection_id,
        )

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
        """Compatibility proxy for search paths."""
        return await search_service.search(
            project_id=project_id,
            query=query,
            top_k=top_k,
            threshold=threshold,
            db=db,
            rag_collection_id=rag_collection_id,
            use_hybrid=use_hybrid,
            use_reranker=use_reranker,
            use_query_rewrite=use_query_rewrite,
        )

    async def list_chunks(self, project_id: uuid.UUID, db: AsyncSession) -> list[dict]:
        """Compatibility proxy for chunk listing."""
        return await search_service.list_chunks(project_id, db)

    async def delete_chunk(self, project_id: uuid.UUID, chunk_id: int, db: AsyncSession) -> bool:
        """Compatibility proxy for chunk deletion."""
        return await search_service.delete_chunk(project_id, chunk_id, db)

    async def requeue_node(self, project_id: uuid.UUID, node_id: uuid.UUID, db: AsyncSession):
        """Compatibility proxy for node requeue."""
        return await index_job_service.requeue_node(project_id, node_id, db)

    async def clear_project_chunks(self, project_id: uuid.UUID, db: AsyncSession) -> None:
        """Compatibility proxy for chunk clearing."""
        await search_service.clear_project_chunks(project_id, db)


rag_service = RagService()
