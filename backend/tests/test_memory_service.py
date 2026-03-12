"""Memory service unit tests."""
import pytest
from unittest.mock import AsyncMock, patch
from app.services.memory_service import MemoryService
from app.models.conversation import Message, MessageRole


@pytest.mark.asyncio
async def test_summarize_conversation():
    """Test conversation summarization."""
    service = MemoryService()

    messages = [
        Message(role=MessageRole.USER, content="Hello, I need help with Python"),
        Message(role=MessageRole.ASSISTANT, content="I can help you with Python. What do you need?"),
    ]

    with patch.object(service.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value.choices = [
            AsyncMock(message=AsyncMock(content="User asked for Python help"))
        ]

        summary = await service.summarize_conversation(messages)
        assert summary == "User asked for Python help"
        assert mock_create.called


@pytest.mark.asyncio
async def test_generate_embedding():
    """Test embedding generation."""
    service = MemoryService()

    with patch.object(service.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value.data = [AsyncMock(embedding=[0.1, 0.2, 0.3])]

        embedding = await service._generate_embedding("test text")
        assert embedding == [0.1, 0.2, 0.3]
        assert mock_create.called
