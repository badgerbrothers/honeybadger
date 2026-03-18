"""Queue service for publishing tasks to RabbitMQ."""
from __future__ import annotations

import asyncio
import json
import uuid

import aio_pika
import structlog
from aio_pika import DeliveryMode, Message

from app.config import settings

logger = structlog.get_logger(__name__)

TASK_RUN_QUEUE = "task-runs"
INDEX_JOB_QUEUE = "index-jobs"


class QueueService:
    """RabbitMQ publisher for task distribution."""

    def __init__(self):
        self.connection: aio_pika.abc.AbstractRobustConnection | None = None
        self.channel: aio_pika.abc.AbstractRobustChannel | None = None

    async def connect(self):
        """Initialize RabbitMQ connection and declare required queues."""
        max_attempts = 20
        retry_delay_seconds = 1.5
        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                self.connection = await aio_pika.connect_robust(settings.rabbitmq_url)
                self.channel = await self.connection.channel()
                await self.channel.declare_queue(TASK_RUN_QUEUE, durable=True)
                await self.channel.declare_queue(INDEX_JOB_QUEUE, durable=True)
                logger.info(
                    "queue_service_connected",
                    rabbitmq_host=settings.rabbitmq_host,
                    rabbitmq_port=settings.rabbitmq_port,
                    attempt=attempt,
                )
                return
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "queue_service_connect_retry",
                    rabbitmq_host=settings.rabbitmq_host,
                    rabbitmq_port=settings.rabbitmq_port,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    error=str(exc),
                )
                if attempt < max_attempts:
                    await asyncio.sleep(retry_delay_seconds)

        if last_error is not None:
            raise last_error
        raise RuntimeError("Failed to connect to RabbitMQ")

    async def publish_task_run(self, task_run_id: uuid.UUID):
        """Publish TaskRun to task-runs queue."""
        await self._publish(TASK_RUN_QUEUE, {"task_run_id": str(task_run_id)})
        logger.info("task_run_published", task_run_id=str(task_run_id))

    async def publish_index_job(self, job_id: uuid.UUID):
        """Publish DocumentIndexJob to index-jobs queue."""
        await self._publish(INDEX_JOB_QUEUE, {"job_id": str(job_id)})
        logger.info("index_job_published", job_id=str(job_id))

    async def _publish(self, routing_key: str, payload: dict):
        """Publish payload to RabbitMQ default exchange."""
        if self.channel is None:
            raise RuntimeError("Queue service is not connected")

        message = Message(
            body=json.dumps(payload).encode(),
            delivery_mode=DeliveryMode.PERSISTENT,
            content_type="application/json",
        )
        await self.channel.default_exchange.publish(message, routing_key=routing_key)

    async def close(self):
        """Close connection."""
        if self.connection:
            await self.connection.close()
            self.connection = None
            self.channel = None
            logger.info("queue_service_closed")


queue_service = QueueService()
