"""Unit tests for backend queue publisher service."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aio_pika import DeliveryMode

from app.services.queue_service import INDEX_JOB_QUEUE, TASK_RUN_QUEUE, QueueService


@pytest.mark.asyncio
async def test_connect_declares_required_queues():
    """Queue service should establish connection and declare both durable queues."""
    service = QueueService()
    mock_connection = AsyncMock()
    mock_channel = AsyncMock()
    mock_connection.channel = AsyncMock(return_value=mock_channel)

    with patch("app.services.queue_service.aio_pika.connect_robust", new=AsyncMock(return_value=mock_connection)):
        await service.connect()

    assert service.connection is mock_connection
    assert service.channel is mock_channel
    mock_channel.declare_queue.assert_any_call(TASK_RUN_QUEUE, durable=True)
    mock_channel.declare_queue.assert_any_call(INDEX_JOB_QUEUE, durable=True)


@pytest.mark.asyncio
async def test_publish_task_run_uses_persistent_message():
    """Task run messages should be published to task-runs with persistent delivery mode."""
    service = QueueService()
    published = {}
    mock_exchange = AsyncMock()

    async def _publish(message, routing_key):
        published["message"] = message
        published["routing_key"] = routing_key

    mock_exchange.publish = _publish
    service.channel = MagicMock(default_exchange=mock_exchange)

    task_run_id = uuid.uuid4()
    await service.publish_task_run(task_run_id)

    assert published["routing_key"] == TASK_RUN_QUEUE
    assert published["message"].delivery_mode == DeliveryMode.PERSISTENT
    assert published["message"].content_type == "application/json"


@pytest.mark.asyncio
async def test_publish_index_job_uses_persistent_message():
    """Index job messages should be published to index-jobs with persistent delivery mode."""
    service = QueueService()
    published = {}
    mock_exchange = AsyncMock()

    async def _publish(message, routing_key):
        published["message"] = message
        published["routing_key"] = routing_key

    mock_exchange.publish = _publish
    service.channel = MagicMock(default_exchange=mock_exchange)

    job_id = uuid.uuid4()
    await service.publish_index_job(job_id)

    assert published["routing_key"] == INDEX_JOB_QUEUE
    assert published["message"].delivery_mode == DeliveryMode.PERSISTENT


@pytest.mark.asyncio
async def test_publish_raises_when_not_connected():
    """Publishing without a connected channel should fail fast."""
    service = QueueService()
    with pytest.raises(RuntimeError):
        await service.publish_task_run(uuid.uuid4())


@pytest.mark.asyncio
async def test_close_resets_connection_handles():
    """close() should close and reset internal connection state."""
    service = QueueService()
    mock_connection = AsyncMock()
    service.connection = mock_connection
    service.channel = AsyncMock()

    await service.close()

    mock_connection.close.assert_awaited_once()
    assert service.connection is None
    assert service.channel is None

