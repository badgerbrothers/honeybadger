"""Unit tests for index job orchestration service."""
from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.document_index_job import DocumentIndexJob, DocumentIndexStatus
from app.models.project import NodeType, Project, ProjectNode
from app.models.rag_collection import RagCollection
from app.services import index_job_service as index_job_service_module
from app.services.index_job_service import IndexJobService


@pytest_asyncio.fixture
async def db_session(tmp_path: Path):
    db_file = tmp_path / "index_job_service.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(
            DocumentIndexJob.metadata.create_all,
            tables=[
                Project.__table__,
                ProjectNode.__table__,
                RagCollection.__table__,
                DocumentIndexJob.__table__,
            ],
        )

    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_schedule_indexing_creates_pending_job_and_publishes(db_session: AsyncSession):
    service = IndexJobService()
    publish_mock = AsyncMock()
    original_publish = index_job_service_module.queue_service.publish_index_job
    index_job_service_module.queue_service.publish_index_job = publish_mock
    try:
        rag_id = uuid.uuid4()
        db_session.add(RagCollection(id=rag_id, owner_user_id=uuid.uuid4(), name="shared"))
        await db_session.commit()

        job = await service.schedule_indexing(
            db=db_session,
            rag_collection_id=rag_id,
            storage_path="rags/test/doc.md",
            file_name="doc.md",
        )

        assert job.status == DocumentIndexStatus.PENDING
        publish_mock.assert_awaited_once_with(job.id)

        persisted = await db_session.get(DocumentIndexJob, job.id)
        assert persisted is not None
        assert persisted.storage_path == "rags/test/doc.md"
    finally:
        index_job_service_module.queue_service.publish_index_job = original_publish


@pytest.mark.asyncio
async def test_schedule_indexing_marks_job_failed_when_publish_fails(db_session: AsyncSession):
    service = IndexJobService()
    original_publish = index_job_service_module.queue_service.publish_index_job
    index_job_service_module.queue_service.publish_index_job = AsyncMock(side_effect=RuntimeError("rabbit down"))
    try:
        rag_id = uuid.uuid4()
        db_session.add(RagCollection(id=rag_id, owner_user_id=uuid.uuid4(), name="shared"))
        await db_session.commit()

        with pytest.raises(RuntimeError, match="rabbit down"):
            await service.schedule_indexing(
                db=db_session,
                rag_collection_id=rag_id,
                storage_path="rags/test/doc.md",
                file_name="doc.md",
            )

        result = await db_session.execute(select(DocumentIndexJob))
        jobs = result.scalars().all()
        assert len(jobs) == 1
        assert jobs[0].status == DocumentIndexStatus.FAILED
        assert jobs[0].error_message == "queue_publish_failed"
    finally:
        index_job_service_module.queue_service.publish_index_job = original_publish


@pytest.mark.asyncio
async def test_requeue_node_returns_none_when_node_missing(db_session: AsyncSession):
    service = IndexJobService()
    project = Project(id=uuid.uuid4(), name="proj", owner_user_id=uuid.uuid4())
    db_session.add(project)
    await db_session.commit()

    result = await service.requeue_node(project.id, uuid.uuid4(), db_session)

    assert result is None


@pytest.mark.asyncio
async def test_requeue_node_copies_node_fields_into_job(db_session: AsyncSession):
    service = IndexJobService()
    original_publish = index_job_service_module.queue_service.publish_index_job
    index_job_service_module.queue_service.publish_index_job = AsyncMock()
    try:
        project = Project(id=uuid.uuid4(), name="proj", owner_user_id=uuid.uuid4())
        node = ProjectNode(
            id=uuid.uuid4(),
            project_id=project.id,
            name="guide.md",
            path="projects/proj/files/node/guide.md",
            node_type=NodeType.FILE,
            size=128,
        )
        db_session.add(project)
        db_session.add(node)
        await db_session.commit()

        job = await service.requeue_node(project.id, node.id, db_session)

        assert job is not None
        assert job.project_id == project.id
        assert job.project_node_id == node.id
        assert job.storage_path == node.path
        assert job.file_name == node.name
    finally:
        index_job_service_module.queue_service.publish_index_job = original_publish


def test_index_job_service_does_not_expose_search_helpers():
    service = IndexJobService()
    assert not hasattr(service, "embedding_service")
    assert not hasattr(service, "reranker")
    assert not hasattr(service, "rewriter")
