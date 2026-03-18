"""Unit tests for task scheduler queue transitions."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.models.task import QueueStatus
from app.services.task_scheduler import TaskScheduler


class _ScalarResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return self._items


class _SessionContext:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_scheduler_moves_due_tasks():
    """Scheduler should move due scheduled tasks to queued."""
    due_task = SimpleNamespace(
        id=uuid.uuid4(),
        queue_status=QueueStatus.SCHEDULED,
        scheduled_at=(datetime.now(UTC) - timedelta(minutes=5)).replace(tzinfo=None),
    )
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_ScalarResult([due_task]))
    session.commit = AsyncMock()

    scheduler = TaskScheduler()
    with patch("app.services.task_scheduler.async_session_maker", return_value=_SessionContext(session)):
        moved_count = await scheduler._process_scheduled_tasks()

    assert moved_count == 1
    assert due_task.queue_status == QueueStatus.QUEUED
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_scheduler_ignores_future_tasks():
    """Scheduler should leave future tasks untouched."""
    future_task = SimpleNamespace(
        id=uuid.uuid4(),
        queue_status=QueueStatus.SCHEDULED,
        scheduled_at=(datetime.now(UTC) + timedelta(hours=1)).replace(tzinfo=None),
    )
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_ScalarResult([]))
    session.commit = AsyncMock()

    scheduler = TaskScheduler()
    with patch("app.services.task_scheduler.async_session_maker", return_value=_SessionContext(session)):
        moved_count = await scheduler._process_scheduled_tasks()

    assert moved_count == 0
    assert future_task.queue_status == QueueStatus.SCHEDULED
    session.commit.assert_not_called()
