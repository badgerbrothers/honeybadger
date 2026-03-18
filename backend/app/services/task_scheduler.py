"""Task scheduler for moving due scheduled tasks into the queue column."""
from __future__ import annotations

from datetime import UTC, datetime

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.database import async_session_maker
from app.models.task import QueueStatus, Task

logger = structlog.get_logger(__name__)


class TaskScheduler:
    """Periodic scheduler for queue status transitions."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone=UTC)
        self.running = False

    async def start(self) -> None:
        """Start scheduler jobs."""
        if self.running:
            return

        self.scheduler.add_job(
            self._process_scheduled_tasks,
            "interval",
            seconds=30,
            id="process_scheduled_tasks",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        self.scheduler.start()
        self.running = True
        logger.info("task_scheduler_started")

    async def stop(self) -> None:
        """Stop scheduler jobs."""
        if not self.running:
            return
        self.scheduler.shutdown(wait=False)
        self.running = False
        logger.info("task_scheduler_stopped")

    async def _process_scheduled_tasks(self) -> int:
        """Move due scheduled tasks to queued."""
        now = datetime.now(UTC).replace(tzinfo=None)
        async with async_session_maker() as session:
            result = await session.execute(
                select(Task).where(
                    Task.queue_status == QueueStatus.SCHEDULED,
                    Task.scheduled_at.is_not(None),
                    Task.scheduled_at <= now,
                )
            )
            due_tasks = result.scalars().all()

            for task in due_tasks:
                task.queue_status = QueueStatus.QUEUED

            if due_tasks:
                await session.commit()
                logger.info(
                    "scheduled_tasks_moved_to_queue",
                    count=len(due_tasks),
                    task_ids=[str(task.id) for task in due_tasks],
                )

        return len(due_tasks)


task_scheduler = TaskScheduler()
