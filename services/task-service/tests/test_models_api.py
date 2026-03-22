"""Tests for task model selection and catalog APIs."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.models.task import QueueStatus
from app.routers import tasks as tasks_router
from app.security.auth import CurrentUser, get_current_user


class _FakeSession:
    """Minimal async session stub for task creation routes."""

    def __init__(self) -> None:
        self.added = []

    def add(self, obj) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        return None

    async def refresh(self, obj) -> None:
        now = datetime.now(UTC).replace(tzinfo=None)
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        if getattr(obj, "queue_status", None) is None:
            obj.queue_status = QueueStatus.SCHEDULED
        if getattr(obj, "priority", None) is None:
            obj.priority = 0
        if getattr(obj, "created_at", None) is None:
            obj.created_at = now
        if getattr(obj, "updated_at", None) is None:
            obj.updated_at = now


@pytest.fixture
def test_app(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        tasks_router.settings,
        "supported_models_raw",
        "gpt-5.3-codex,gpt-4-turbo-preview,claude-3-sonnet-20240229",
    )
    monkeypatch.setattr(tasks_router.settings, "default_main_model", "gpt-5.3-codex")

    app = FastAPI()
    app.include_router(tasks_router.router)

    async def _override_db():
        yield _FakeSession()

    async def _override_current_user() -> CurrentUser:
        return CurrentUser(id=uuid.UUID("00000000-0000-0000-0000-000000000002"), email="test@badgers.local")

    async def _allow_owned_project_and_conversation(*args, **kwargs):
        return SimpleNamespace(active_rag_collection_id=None)

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_current_user
    monkeypatch.setattr(tasks_router, "_ensure_owned_project_and_conversation", _allow_owned_project_and_conversation)
    return app


def _task_payload(*, model: str | None = None) -> dict:
    payload: dict[str, str | int] = {
        "conversation_id": str(uuid.uuid4()),
        "project_id": str(uuid.uuid4()),
        "goal": "Model selection test",
    }
    if model is not None:
        payload["model"] = model
    return payload


@pytest.mark.asyncio
async def test_create_task_with_explicit_supported_model(test_app: FastAPI):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.post("/api/tasks/", json=_task_payload(model="gpt-4-turbo-preview"))

    assert response.status_code == 201
    assert response.json()["model"] == "gpt-4-turbo-preview"


@pytest.mark.asyncio
async def test_create_task_without_model_uses_default(test_app: FastAPI):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.post("/api/tasks/", json=_task_payload())

    assert response.status_code == 201
    assert response.json()["model"] == "gpt-5.3-codex"


@pytest.mark.asyncio
async def test_create_task_with_unsupported_model_returns_422(test_app: FastAPI):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.post("/api/tasks/", json=_task_payload(model="unknown-model"))

    assert response.status_code == 422
    body = response.json()
    assert "Unsupported model" in body["detail"]["message"]
    assert "gpt-5.3-codex" in body["detail"]["supported_models"]


@pytest.mark.asyncio
async def test_get_model_catalog_returns_default_and_supported_models(test_app: FastAPI):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response = await client.get("/api/tasks/models")

    assert response.status_code == 200
    body = response.json()
    assert body["default_model"] == "gpt-5.3-codex"
    assert body["supported_models"] == [
        "gpt-5.3-codex",
        "gpt-4-turbo-preview",
        "claude-3-sonnet-20240229",
    ]
