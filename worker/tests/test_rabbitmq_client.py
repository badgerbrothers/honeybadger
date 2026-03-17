"""Unit tests for worker RabbitMQ client message handling semantics."""
from unittest.mock import AsyncMock

import pytest

from queueing.rabbitmq_client import RabbitMQClient


@pytest.mark.asyncio
async def test_handle_message_acks_on_success():
    """Successful callback should ack the message."""
    client = RabbitMQClient("task-runs")
    callback = AsyncMock(return_value=None)
    message = AsyncMock()
    message.body = b'{"task_run_id":"00000000-0000-0000-0000-000000000001"}'

    await client._handle_message(message, callback)

    callback.assert_awaited_once()
    message.ack.assert_awaited_once()
    message.nack.assert_not_called()
    message.reject.assert_not_called()


@pytest.mark.asyncio
async def test_handle_message_ack_on_decode_error():
    """Malformed JSON payload should be acknowledged and dropped."""
    client = RabbitMQClient("task-runs")
    callback = AsyncMock(return_value=None)
    message = AsyncMock()
    message.body = b"not-json"

    await client._handle_message(message, callback)

    callback.assert_not_called()
    message.ack.assert_awaited_once()
    message.nack.assert_not_called()
    message.reject.assert_not_called()


@pytest.mark.asyncio
async def test_handle_message_reject_on_validation_error():
    """ValueError should reject without requeue to avoid poison-loop retries."""
    client = RabbitMQClient("task-runs")
    callback = AsyncMock(side_effect=ValueError("invalid payload"))
    message = AsyncMock()
    message.body = b'{"task_run_id":"bad"}'

    await client._handle_message(message, callback)

    message.reject.assert_awaited_once_with(requeue=False)
    message.ack.assert_not_called()
    message.nack.assert_not_called()


@pytest.mark.asyncio
async def test_handle_message_nack_on_transient_error():
    """Non-validation failures should nack with requeue enabled."""
    client = RabbitMQClient("task-runs")
    callback = AsyncMock(side_effect=RuntimeError("temporary downstream error"))
    message = AsyncMock()
    message.body = b'{"task_run_id":"00000000-0000-0000-0000-000000000002"}'

    await client._handle_message(message, callback)

    message.nack.assert_awaited_once_with(requeue=True)
    message.ack.assert_not_called()
    message.reject.assert_not_called()
