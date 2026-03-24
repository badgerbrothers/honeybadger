"""RabbitMQ client for worker-side queue consumption."""
from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

import aio_pika
import structlog
from aio_pika.abc import (
    AbstractIncomingMessage,
    AbstractRobustChannel,
    AbstractRobustConnection,
    AbstractQueue,
)

from config import settings

logger = structlog.get_logger(__name__)


class RabbitMQClient:
    """Async RabbitMQ consumer with robust connection and explicit ack semantics."""

    def __init__(self, queue_name: str, *, requeue_on_error: bool = True):
        self.queue_name = queue_name
        self.requeue_on_error = requeue_on_error
        self.connection: AbstractRobustConnection | None = None
        self.channel: AbstractRobustChannel | None = None
        self.queue: AbstractQueue | None = None

    async def connect(self):
        """Establish connection and declare the target queue."""
        self.connection = await aio_pika.connect_robust(settings.rabbitmq_url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=1)
        self.queue = await self.channel.declare_queue(self.queue_name, durable=True)
        logger.info("rabbitmq_connected", queue=self.queue_name)

    async def consume(
        self,
        callback: Callable[[dict[str, Any]], Awaitable[None]],
        stop_event: asyncio.Event | None = None,
    ):
        """Consume messages from queue until cancelled or stop_event is set."""
        if self.queue is None:
            raise RuntimeError("RabbitMQ client is not connected")

        async with self.queue.iterator() as queue_iter:
            async for message in queue_iter:
                if stop_event and stop_event.is_set():
                    break
                await self._handle_message(message, callback)

    async def _handle_message(
        self,
        message: AbstractIncomingMessage,
        callback: Callable[[dict[str, Any]], Awaitable[None]],
    ):
        """Process one message with explicit ack/nack/reject behavior."""
        try:
            payload = json.loads(message.body.decode("utf-8"))
        except Exception as exc:
            logger.error(
                "rabbitmq_decode_failed",
                queue=self.queue_name,
                error=str(exc),
                exc_info=True,
            )
            await message.ack()
            return

        try:
            await callback(payload)
        except ValueError as exc:
            # Payload/validation issues should not endlessly retry.
            logger.error(
                "rabbitmq_message_rejected",
                queue=self.queue_name,
                error=str(exc),
            )
            await message.reject(requeue=False)
            return
        except Exception as exc:
            logger.error(
                "rabbitmq_message_failed",
                queue=self.queue_name,
                error=str(exc),
                exc_info=True,
                requeue=self.requeue_on_error,
            )
            if self.requeue_on_error:
                await message.nack(requeue=True)
            else:
                await message.ack()
            return

        await message.ack()

    async def close(self):
        """Close connection."""
        if self.connection:
            await self.connection.close()
            self.connection = None
            self.channel = None
            self.queue = None
            logger.info("rabbitmq_closed", queue=self.queue_name)
