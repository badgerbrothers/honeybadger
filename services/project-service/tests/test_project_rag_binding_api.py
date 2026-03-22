"""Tests for project active RAG binding endpoints."""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import get_db
from app.models.project import Project
from app.models.rag_collection import RagCollection
from app.routers import project_rag as project_rag_router
from app.security.auth import CurrentUser, get_current_user


@pytest.mark.asyncio
async def test_put_and_get_project_rag_binding(tmp_path: Path):
    db_file = tmp_path / "project_rag_binding.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    project_id = uuid.uuid4()
    rag_id = uuid.uuid4()
    owner_user_id = uuid.uuid4()

    async with engine.begin() as conn:
        await conn.run_sync(
            Project.metadata.create_all,
            tables=[Project.__table__, RagCollection.__table__],
        )

    async with session_maker() as session:
        session.add(
            Project(
                id=project_id,
                name="P1",
                description=None,
                owner_user_id=owner_user_id,
            )
        )
        session.add(
            RagCollection(
                id=rag_id,
                owner_user_id=owner_user_id,
                name="shared-rag",
                description=None,
            )
        )
        await session.commit()

    app = FastAPI()
    app.include_router(project_rag_router.router)

    async def _override_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(id=owner_user_id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        put_resp = await client.put(
            f"/api/projects/{project_id}/rag",
            json={"rag_collection_id": str(rag_id)},
        )
        assert put_resp.status_code == 200
        assert put_resp.json()["rag_collection_id"] == str(rag_id)

        get_resp = await client.get(f"/api/projects/{project_id}/rag")
        assert get_resp.status_code == 200
        assert get_resp.json()["rag_collection_id"] == str(rag_id)

    await engine.dispose()
