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
from app.config import settings
from app.models.rag_collection import RagCollection
from app.models.rag_collection_file import RagCollectionFile
from app.models.rag_upload_session import RagUploadSession, RagUploadSessionStatus
from app.routers import rag_collections as rag_collections_router
from app.security.auth import CurrentUser, get_current_user


@pytest.mark.asyncio
async def test_create_rag_collection_multipart_upload_session(tmp_path: Path):
    db_file = tmp_path / "rag_collections_multipart_init.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    owner_user_id = uuid.uuid4()

    async with engine.begin() as conn:
        await conn.run_sync(
            RagCollection.metadata.create_all,
            tables=[
                RagCollection.__table__,
                RagCollectionFile.__table__,
                RagUploadSession.__table__,
            ],
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

    rag_collections_router.storage_service.create_multipart_upload = AsyncMock(return_value="upload-123")
    rag_collections_router.storage_service.get_presigned_multipart_part_url = AsyncMock(
        side_effect=[
            "http://upload/part-1",
            "http://upload/part-2",
        ]
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/rags/{rag_id}/files/multipart",
            json={
                "file_name": "guide.md",
                "file_size": settings.s3_multipart_part_size + 5,
                "mime_type": "text/markdown",
            },
        )

    assert resp.status_code == 201
    payload = resp.json()
    assert payload["upload_id"] == "upload-123"
    assert payload["part_count"] == 2
    assert payload["parts"][0]["part_number"] == 1
    assert payload["parts"][1]["part_number"] == 2

    async with session_maker() as session:
        stored = (await session.execute(select(RagUploadSession))).scalar_one()
        assert stored.upload_id == "upload-123"
        assert stored.status == RagUploadSessionStatus.INITIATED

    await engine.dispose()


@pytest.mark.asyncio
async def test_complete_rag_collection_multipart_upload_creates_file_and_schedules_indexing(tmp_path: Path):
    db_file = tmp_path / "rag_collections_multipart_complete.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    owner_user_id = uuid.uuid4()

    async with engine.begin() as conn:
        await conn.run_sync(
            RagCollection.metadata.create_all,
            tables=[
                RagCollection.__table__,
                RagCollectionFile.__table__,
                RagUploadSession.__table__,
            ],
        )

    app = FastAPI()
    app.include_router(rag_collections_router.router)

    async def _override_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(id=owner_user_id)

    rag_id = uuid.uuid4()
    upload_session_id = uuid.uuid4()
    file_id = uuid.uuid4()
    storage_path = f"rags/{rag_id}/files/{file_id}/guide.md"

    async with session_maker() as session:
        session.add(RagCollection(id=rag_id, owner_user_id=owner_user_id, name="shared-rag"))
        session.add(
            RagUploadSession(
                id=upload_session_id,
                file_id=file_id,
                rag_collection_id=rag_id,
                owner_user_id=owner_user_id,
                storage_path=storage_path,
                file_name="guide.md",
                file_size=42,
                mime_type="text/markdown",
                upload_id="upload-123",
                part_size=settings.s3_multipart_part_size,
                part_count=1,
                status=RagUploadSessionStatus.INITIATED,
            )
        )
        await session.commit()

    rag_collections_router.storage_service.complete_multipart_upload = AsyncMock()
    rag_collections_router.storage_service.stat_file = AsyncMock(return_value=SimpleNamespace(size=42))
    rag_collections_router.index_job_service.schedule_indexing = AsyncMock(
        return_value=SimpleNamespace(id=uuid.uuid4())
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            f"/api/rags/{rag_id}/files/multipart/complete",
            json={
                "upload_session_id": str(upload_session_id),
                "parts": [{"part_number": 1, "etag": '"etag-1"'}],
            },
        )

    assert resp.status_code == 201
    payload = resp.json()
    assert payload["id"] == str(file_id)
    assert payload["storage_path"] == storage_path
    assert payload["status"] == "pending"

    async with session_maker() as session:
        stored_file = (await session.execute(select(RagCollectionFile))).scalar_one()
        stored_session = (await session.execute(select(RagUploadSession))).scalar_one()
        assert stored_file.id == file_id
        assert stored_session.status == RagUploadSessionStatus.COMPLETED

    await engine.dispose()
