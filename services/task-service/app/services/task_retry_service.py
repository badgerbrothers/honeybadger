"""Retry policy service for failed task runs."""
from __future__ import annotations

from datetime import UTC, datetime
import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.task import Task, TaskRun, TaskStatus
from app.services.queue_service import queue_service

logger = structlog.get_logger(__name__)

_RETRYABLE_FAILURE_CATEGORIES = {"model_api", "sandbox", "internal"}


def _utcnow() -> datetime:
    """Return naive UTC datetime to match DB column definitions."""
    return datetime.now(UTC).replace(tzinfo=None)


def _event_retryable(event: dict) -> bool:
    """Return whether a failed event is eligible for automatic retry."""
    retryable_hint = event.get("retryable_hint")
    if not isinstance(retryable_hint, bool):
        return False
    if not retryable_hint:
        return False

    error_category = str(event.get("error_category") or "").strip()
    if error_category and error_category not in _RETRYABLE_FAILURE_CATEGORIES:
        return False
    return True


class TaskRetryService:
    """Evaluate run failure events and schedule retry attempts when allowed."""

    async def maybe_schedule_retry(
        self,
        *,
        db: AsyncSession,
        run: TaskRun,
        task: Task,
        event: dict,
    ) -> TaskRun | None:
        """Create and publish a new TaskRun when retry policy allows."""
        if event.get("type") != "run_failed":
            return None

        if settings.task_run_auto_retry_limit <= 0:
            logger.info("task_retry_skipped", task_id=str(task.id), reason="auto_retry_disabled")
            return None

        if not _event_retryable(event):
            logger.info(
                "task_retry_skipped",
                task_id=str(task.id),
                task_run_id=str(run.id),
                reason="event_not_retryable",
            )
            return None

        if task.current_run_id is not None:
            logger.info(
                "task_retry_skipped",
                task_id=str(task.id),
                task_run_id=str(run.id),
                current_run_id=str(task.current_run_id),
                reason="task_has_active_run",
            )
            return None

        attempts_result = await db.execute(
            select(TaskRun.id).where(TaskRun.task_id == task.id)
        )
        existing_attempts = len(attempts_result.scalars().all())
        retries_used = max(0, existing_attempts - 1)
        if retries_used >= settings.task_run_auto_retry_limit:
            logger.info(
                "task_retry_skipped",
                task_id=str(task.id),
                task_run_id=str(run.id),
                retries_used=retries_used,
                retry_limit=settings.task_run_auto_retry_limit,
                reason="retry_limit_reached",
            )
            return None

        retry_run = TaskRun(task_id=task.id, status=TaskStatus.PENDING)
        db.add(retry_run)
        await db.flush()
        task.current_run_id = retry_run.id

        logs = list(run.logs or [])
        logs.append(
            {
                "type": "auto_retry_scheduled",
                "timestamp": _utcnow().isoformat(),
                "retry_run_id": str(retry_run.id),
                "trigger_run_id": str(run.id),
                "attempt_number": existing_attempts + 1,
            }
        )
        run.logs = logs
        await db.commit()

        try:
            await queue_service.publish_task_run(retry_run.id)
        except Exception as exc:
            logger.error(
                "task_retry_publish_failed",
                task_id=str(task.id),
                failed_run_id=str(run.id),
                retry_run_id=str(retry_run.id),
                error=str(exc),
                exc_info=True,
            )
            retry_run.status = TaskStatus.FAILED
            retry_run.error_message = "queue_publish_failed"
            if task.current_run_id == retry_run.id:
                task.current_run_id = None
            await db.commit()
            return None

        logger.info(
            "task_retry_scheduled",
            task_id=str(task.id),
            failed_run_id=str(run.id),
            retry_run_id=str(retry_run.id),
            attempt_number=existing_attempts + 1,
        )
        return retry_run


task_retry_service = TaskRetryService()
