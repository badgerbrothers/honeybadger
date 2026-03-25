"""Tests for global RAG collection APIs."""
from __future__ import annotations

import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import get_db
from app.models.rag_collection import RagCollection
from app.models.rag_collection_file import RagCollectionFile
from app.routers import rag_collections as rag_collections_router
from app.security.auth import CurrentUser, get_current_user


@pytest.mark.asyncio
async def test_create_list_and_upload_rag_collection(tmp_path: Path):
    db_file = tmp_path / "rag_collections.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    owner_user_id = uuid.uuid4()

    async with engine.begin() as conn:
        await conn.run_sync(
            RagCollection.metadata.create_all,
            tables=[RagCollection.__table__, RagCollectionFile.__table__],
        )

    app = FastAPI()
    app.include_router(rag_collections_router.router)

    async def _override_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(id=owner_user_id)

    rag_collections_router.storage_service.upload_stream = AsyncMock(return_value="ok")
    rag_collections_router.index_job_service.schedule_indexing = AsyncMock(
        return_value=SimpleNamespace(id=uuid.uuid4())
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post(
            "/api/rags/",
            json={"name": "shared-rag", "description": "docs"},
        )
        assert create_resp.status_code == 201
        rag_id = create_resp.json()["id"]

        list_resp = await client.get("/api/rags/")
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1

        upload_resp = await client.post(
            f"/api/rags/{rag_id}/files/upload",
            files={"file": ("guide.md", b"# guide", "text/markdown")},
        )
        assert upload_resp.status_code == 201
        payload = upload_resp.json()
        assert payload["rag_collection_id"] == rag_id
        assert payload["file_name"] == "guide.md"
        assert payload["status"] == "pending"
        assert payload["index_job_id"] is not None
        rag_collections_router.storage_service.upload_stream.assert_awaited_once()

        files_resp = await client.get(f"/api/rags/{rag_id}/files")
        assert files_resp.status_code == 200
        rows = files_resp.json()
        assert len(rows) == 1
        assert rows[0]["file_name"] == "guide.md"

    await engine.dispose()


@pytest.mark.asyncio
async def test_upload_rag_collection_file_rejects_invalid_extension(tmp_path: Path):
    db_file = tmp_path / "rag_collections_invalid.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    owner_user_id = uuid.uuid4()

    async with engine.begin() as conn:
        await conn.run_sync(
            RagCollection.metadata.create_all,
            tables=[RagCollection.__table__, RagCollectionFile.__table__],
        )

    app = FastAPI()
    app.include_router(rag_collections_router.router)

    async def _override_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(id=owner_user_id)

    async with session_maker() as session:
        session.add(RagCollection(id=uuid.uuid4(), owner_user_id=owner_user_id, name="shared-rag"))
        await session.commit()
        rag_id = str((await session.execute(select(RagCollection))).scalar_one().id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        upload_resp = await client.post(
            f"/api/rags/{rag_id}/files/upload",
            files={"file": ("bad.exe", b"x", "application/octet-stream")},
        )

    assert upload_resp.status_code == 400
    assert "File type not allowed" in upload_resp.json()["detail"]

    await engine.dispose()


@pytest.mark.asyncio
async def test_upload_rag_collection_file_marks_failed_when_storage_upload_fails(tmp_path: Path):
    db_file = tmp_path / "rag_collections_storage_fail.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    owner_user_id = uuid.uuid4()

    async with engine.begin() as conn:
        await conn.run_sync(
            RagCollection.metadata.create_all,
            tables=[RagCollection.__table__, RagCollectionFile.__table__],
        )

    app = FastAPI()
    app.include_router(rag_collections_router.router)

    async def _override_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(id=owner_user_id)

    rag_id = uuid.uuid4()
    async with session_maker() as session:
        session.add(RagCollection(id=rag_id, owner_user_id=owner_user_id, name="shared-rag"))
        await session.commit()

    rag_collections_router.storage_service.upload_stream = AsyncMock(side_effect=RuntimeError("minio down"))
    rag_collections_router.index_job_service.schedule_indexing = AsyncMock()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        upload_resp = await client.post(
            f"/api/rags/{rag_id}/files/upload",
            files={"file": ("guide.md", b"# guide", "text/markdown")},
        )

    assert upload_resp.status_code == 503
    rag_collections_router.index_job_service.schedule_indexing.assert_not_awaited()

    await engine.dispose()
