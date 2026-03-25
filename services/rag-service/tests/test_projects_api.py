from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import get_db
from app.models.project import Project, ProjectNode
from app.routers import projects as projects_router


@pytest.mark.asyncio
async def test_upload_project_file_success(tmp_path):
    db_file = tmp_path / "projects_api.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(
            Project.metadata.create_all,
            tables=[Project.__table__, ProjectNode.__table__],
        )

    app = FastAPI()
    app.include_router(projects_router.router)

    async def _override_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _override_db

    project_id = uuid.uuid4()
    async with session_maker() as session:
        session.add(Project(id=project_id, name="proj", owner_user_id=uuid.uuid4()))
        await session.commit()

    projects_router.storage_service.upload_stream = AsyncMock(return_value="ok")
    projects_router.index_job_service.schedule_indexing = AsyncMock(
        return_value=SimpleNamespace(id=uuid.uuid4())
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/projects/{project_id}/files/upload",
            files={"file": ("guide.md", b"# guide", "text/markdown")},
        )

    assert response.status_code == 201
    payload = response.json()
    assert payload["project_id"] == str(project_id)
    assert payload["name"] == "guide.md"
    assert payload["size"] == len(b"# guide")
    projects_router.storage_service.upload_stream.assert_awaited_once()
    projects_router.index_job_service.schedule_indexing.assert_awaited_once()

    async with session_maker() as session:
        rows = (await session.execute(select(ProjectNode))).scalars().all()
        assert len(rows) == 1
        assert rows[0].name == "guide.md"

    await engine.dispose()


@pytest.mark.asyncio
async def test_upload_project_file_rejects_invalid_extension(tmp_path):
    db_file = tmp_path / "projects_api_invalid.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(
            Project.metadata.create_all,
            tables=[Project.__table__, ProjectNode.__table__],
        )

    app = FastAPI()
    app.include_router(projects_router.router)

    async def _override_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _override_db

    project_id = uuid.uuid4()
    async with session_maker() as session:
        session.add(Project(id=project_id, name="proj", owner_user_id=uuid.uuid4()))
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/projects/{project_id}/files/upload",
            files={"file": ("bad.exe", b"boom", "application/octet-stream")},
        )

    assert response.status_code == 400
    assert "File type not allowed" in response.json()["detail"]

    await engine.dispose()


@pytest.mark.asyncio
async def test_upload_project_file_rejects_oversized_payload(tmp_path, monkeypatch):
    db_file = tmp_path / "projects_api_oversized.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(
            Project.metadata.create_all,
            tables=[Project.__table__, ProjectNode.__table__],
        )

    app = FastAPI()
    app.include_router(projects_router.router)

    async def _override_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _override_db

    project_id = uuid.uuid4()
    async with session_maker() as session:
        session.add(Project(id=project_id, name="proj", owner_user_id=uuid.uuid4()))
        await session.commit()

    monkeypatch.setattr(projects_router, "MAX_FILE_SIZE", 3)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/projects/{project_id}/files/upload",
            files={"file": ("guide.md", b"1234", "text/markdown")},
        )

    assert response.status_code == 413

    await engine.dispose()


@pytest.mark.asyncio
async def test_upload_project_file_returns_503_when_storage_upload_fails(tmp_path):
    db_file = tmp_path / "projects_api_storage_fail.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(
            Project.metadata.create_all,
            tables=[Project.__table__, ProjectNode.__table__],
        )

    app = FastAPI()
    app.include_router(projects_router.router)

    async def _override_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _override_db

    project_id = uuid.uuid4()
    async with session_maker() as session:
        session.add(Project(id=project_id, name="proj", owner_user_id=uuid.uuid4()))
        await session.commit()

    projects_router.storage_service.upload_stream = AsyncMock(side_effect=RuntimeError("minio down"))
    projects_router.index_job_service.schedule_indexing = AsyncMock()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/projects/{project_id}/files/upload",
            files={"file": ("guide.md", b"# guide", "text/markdown")},
        )

    assert response.status_code == 503
    projects_router.index_job_service.schedule_indexing.assert_not_awaited()

    async with session_maker() as session:
        rows = (await session.execute(select(ProjectNode))).scalars().all()
        assert rows == []

    await engine.dispose()
