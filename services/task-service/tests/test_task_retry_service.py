"""Tests for task retry policy and run_failed event ingestion."""
from __future__ import annotations

import uuid
import importlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.routers import runs as runs_router
from app.security.auth import require_internal_service_token
from app.services.task_retry_service import TaskRetryService

task_retry_service_module = importlib.import_module("app.services.task_retry_service")


@pytest.mark.asyncio
async def test_task_retry_service_schedules_retry_when_policy_allows(monkeypatch: pytest.MonkeyPatch):
    service = TaskRetryService()
    task_id = uuid.uuid4()
    failed_run_id = uuid.uuid4()

    task = SimpleNamespace(id=task_id, current_run_id=None)
    failed_run = SimpleNamespace(id=failed_run_id, task_id=task_id, logs=[])
    retry_run_holder = {}

    def add(obj) -> None:
        retry_run_holder["run"] = obj

    db = AsyncMock()
    db.add = Mock(side_effect=add)
    db.flush = AsyncMock(side_effect=lambda: setattr(retry_run_holder["run"], "id", uuid.uuid4()))
    db.commit = AsyncMock()
    db.execute = AsyncMock(return_value=Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=[failed_run_id])))))

    publish_task_run = AsyncMock()
    monkeypatch.setattr(task_retry_service_module.queue_service, "publish_task_run", publish_task_run)
    monkeypatch.setattr(task_retry_service_module.settings, "task_run_auto_retry_limit", 1)

    retry_run = await service.maybe_schedule_retry(
        db=db,
        run=failed_run,
        task=task,
        event={
            "type": "run_failed",
            "retryable_hint": True,
            "error_category": "model_api",
        },
    )

    assert retry_run is retry_run_holder["run"]
    assert task.current_run_id == retry_run.id
    assert failed_run.logs[-1]["type"] == "auto_retry_scheduled"
    publish_task_run.assert_awaited_once_with(retry_run.id)


@pytest.mark.asyncio
async def test_task_retry_service_skips_non_retryable_failure(monkeypatch: pytest.MonkeyPatch):
    service = TaskRetryService()
    task = SimpleNamespace(id=uuid.uuid4(), current_run_id=None)
    failed_run = SimpleNamespace(id=uuid.uuid4(), task_id=task.id, logs=[])

    db = AsyncMock()
    db.add = Mock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()

    publish_task_run = AsyncMock()
    monkeypatch.setattr(task_retry_service_module.queue_service, "publish_task_run", publish_task_run)
    monkeypatch.setattr(task_retry_service_module.settings, "task_run_auto_retry_limit", 1)

    retry_run = await service.maybe_schedule_retry(
        db=db,
        run=failed_run,
        task=task,
        event={
            "type": "run_failed",
            "retryable_hint": False,
            "error_category": "tool",
        },
    )

    assert retry_run is None
    db.add.assert_not_called()
    publish_task_run.assert_not_called()


@pytest.mark.asyncio
async def test_run_failed_event_triggers_retry_policy(monkeypatch: pytest.MonkeyPatch):
    run_id = uuid.uuid4()
    task_id = uuid.uuid4()
    run = SimpleNamespace(id=run_id, task_id=task_id, logs=[])
    task = SimpleNamespace(id=task_id, current_run_id=None)

    class _FakeSession:
        def __init__(self) -> None:
            self.execute = AsyncMock(side_effect=[
                Mock(scalar_one_or_none=Mock(return_value=run)),
                Mock(scalar_one_or_none=Mock(return_value=task)),
            ])
            self.commit = AsyncMock()

    session = _FakeSession()
    retry_spy = AsyncMock()

    app = FastAPI()
    app.include_router(runs_router.router)

    async def _override_db():
        yield session

    async def _allow_internal():
        return None

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[require_internal_service_token] = _allow_internal
    monkeypatch.setattr(runs_router.task_retry_service, "maybe_schedule_retry", retry_spy)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/runs/{run_id}/events",
            json={
                "type": "run_failed",
                "error_message": "rate limited",
                "error_category": "model_api",
                "retryable_hint": True,
                "failed_step": "agent_run",
            },
        )

    assert response.status_code == 202
    retry_spy.assert_awaited_once()
