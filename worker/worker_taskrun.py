"""TaskRun specialized worker using RabbitMQ queue consumption."""
from __future__ import annotations

import asyncio
import signal
import uuid

import structlog

from config import settings
from main import async_session_maker, configure_logging, engine, execute_task_run
from queueing.rabbitmq_client import RabbitMQClient

logger = structlog.get_logger(__name__)
shutdown_event = asyncio.Event()


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info("shutdown_signal_received", signal=signum)
    shutdown_event.set()


async def handle_task_run(payload: dict):
    """Handle one TaskRun message payload."""
    task_run_value = payload.get("task_run_id")
    if not task_run_value:
        raise ValueError("Missing task_run_id in payload")

    task_run_id = uuid.UUID(task_run_value)
    logger.info("task_run_received", task_run_id=str(task_run_id))
    async with async_session_maker() as session:
        await execute_task_run(task_run_id, session)


async def main():
    """Run the TaskRun queue worker."""
    configure_logging()
    if settings.worker_mode != "rabbitmq":
        logger.info("taskrun_worker_skipped", worker_mode=settings.worker_mode)
        return
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.info("taskrun_worker_starting")
    client = RabbitMQClient("task-runs")
    await client.connect()
    consume_task: asyncio.Task | None = None

    try:
        consume_task = asyncio.create_task(client.consume(handle_task_run, stop_event=shutdown_event))
        await shutdown_event.wait()
    except asyncio.CancelledError:
        logger.info("taskrun_worker_cancelled")
    finally:
        if consume_task:
            consume_task.cancel()
            await asyncio.gather(consume_task, return_exceptions=True)
        await client.close()
        await engine.dispose()
        logger.info("taskrun_worker_stopped")


if __name__ == "__main__":
    asyncio.run(main())
