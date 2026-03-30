"""DocumentIndexJob specialized worker using RabbitMQ queue consumption."""
from __future__ import annotations

import asyncio
import signal
import uuid

import structlog

from config import settings
from main import (
    async_session_maker,
    claim_document_index_job_by_id,
    configure_logging,
    engine,
    execute_document_index_job,
)
from queueing.rabbitmq_client import RabbitMQClient

logger = structlog.get_logger(__name__)
shutdown_event = asyncio.Event()


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info("shutdown_signal_received", signal=signum)
    shutdown_event.set()


async def handle_index_job(payload: dict):
    """Handle one document index job payload."""
    job_value = payload.get("job_id")
    if not job_value:
        raise ValueError("Missing job_id in payload")

    job_id = uuid.UUID(job_value)
    logger.info("index_job_received", job_id=str(job_id))
    async with async_session_maker() as session:
        claimed_job = await claim_document_index_job_by_id(session, job_id)
        if claimed_job is None:
            logger.info("index_job_skipped", job_id=str(job_id))
            return
        await execute_document_index_job(job_id, session)


async def main():
    """Run the index-job queue worker."""
    configure_logging()
    if settings.worker_mode != "rabbitmq":
        logger.info("indexjob_worker_skipped", worker_mode=settings.worker_mode)
        return
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.info("indexjob_worker_starting")
    client = RabbitMQClient("index-jobs", requeue_on_error=False)
    await client.connect()
    consume_task: asyncio.Task | None = None

    try:
        consume_task = asyncio.create_task(client.consume(handle_index_job, stop_event=shutdown_event))
        await shutdown_event.wait()
    except asyncio.CancelledError:
        logger.info("indexjob_worker_cancelled")
    finally:
        if consume_task:
            consume_task.cancel()
            await asyncio.gather(consume_task, return_exceptions=True)
        await client.close()
        await engine.dispose()
        logger.info("indexjob_worker_stopped")


if __name__ == "__main__":
    asyncio.run(main())
