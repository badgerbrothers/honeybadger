"""Tests for project multipart upload APIs."""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import get_db
from app.config import settings
from app.models.project import Project, ProjectNode
from app.models.project_upload_session import ProjectUploadSession, ProjectUploadSessionStatus
from app.routers import projects as projects_router
from app.security.auth import CurrentUser, get_current_user


@pytest.mark.asyncio
async def test_create_project_multipart_upload_session(tmp_path: Path):
    db_file = tmp_path / "projects_multipart_init.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    owner_user_id = uuid.uuid4()

    async with engine.begin() as conn:
        await conn.run_sync(
            Project.metadata.create_all,
            tables=[Project.__table__, ProjectNode.__table__, ProjectUploadSession.__table__],
        )

    app = FastAPI()
    app.include_router(projects_router.router)

    async def _override_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(id=owner_user_id)

    project_id = uuid.uuid4()
    async with session_maker() as session:
        session.add(Project(id=project_id, owner_user_id=owner_user_id, name="proj"))
        await session.commit()

    projects_router.storage_service.create_multipart_upload = AsyncMock(return_value="upload-123")
    projects_router.storage_service.get_presigned_multipart_part_url = AsyncMock(
        side_effect=["http://upload/part-1", "http://upload/part-2"]
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/projects/{project_id}/files/multipart",
            json={
                "file_name": "doc.md",
                "file_size": settings.s3_multipart_part_size + 5,
                "mime_type": "text/markdown",
            },
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["upload_id"] == "upload-123"
    assert payload["part_count"] == 2

    async with session_maker() as session:
        stored = (await session.execute(select(ProjectUploadSession))).scalar_one()
        assert stored.upload_id == "upload-123"
        assert stored.status == ProjectUploadSessionStatus.INITIATED

    await engine.dispose()


@pytest.mark.asyncio
async def test_complete_project_multipart_upload_creates_node(tmp_path: Path):
    db_file = tmp_path / "projects_multipart_complete.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    owner_user_id = uuid.uuid4()

    async with engine.begin() as conn:
        await conn.run_sync(
            Project.metadata.create_all,
            tables=[Project.__table__, ProjectNode.__table__, ProjectUploadSession.__table__],
        )

    app = FastAPI()
    app.include_router(projects_router.router)

    async def _override_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(id=owner_user_id)

    project_id = uuid.uuid4()
    upload_session_id = uuid.uuid4()
    file_id = uuid.uuid4()
    storage_path = f"projects/{project_id}/files/{file_id}/doc.md"

    async with session_maker() as session:
        session.add(Project(id=project_id, owner_user_id=owner_user_id, name="proj"))
        session.add(
            ProjectUploadSession(
                id=upload_session_id,
                file_id=file_id,
                project_id=project_id,
                owner_user_id=owner_user_id,
                storage_path=storage_path,
                file_name="doc.md",
                file_size=42,
                mime_type="text/markdown",
                upload_id="upload-123",
                part_size=settings.s3_multipart_part_size,
                part_count=1,
                status=ProjectUploadSessionStatus.INITIATED,
            )
        )
        await session.commit()

    projects_router.storage_service.complete_multipart_upload = AsyncMock()
    projects_router.storage_service.stat_file = AsyncMock(return_value=SimpleNamespace(size=42))
    projects_router.rag_client.schedule_indexing = AsyncMock()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/projects/{project_id}/files/multipart/complete",
            headers={"Authorization": "Bearer test-token"},
            json={
                "upload_session_id": str(upload_session_id),
                "parts": [{"part_number": 1, "etag": '"etag-1"'}],
            },
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["id"] == str(file_id)
    assert payload["path"] == storage_path

    async with session_maker() as session:
        stored_node = (await session.execute(select(ProjectNode))).scalar_one()
        stored_session = (await session.execute(select(ProjectUploadSession))).scalar_one()
        assert stored_node.id == file_id
        assert stored_session.status == ProjectUploadSessionStatus.COMPLETED

    projects_router.rag_client.schedule_indexing.assert_not_awaited()
    await engine.dispose()
