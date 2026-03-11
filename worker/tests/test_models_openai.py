"""Tests for OpenAI provider."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from models.openai_provider import OpenAIProvider
from models.types import Message, ModelConfig
from models.exceptions import InvalidRequestError, ProviderError

@pytest.fixture
def openai_provider():
    """Create OpenAI provider for testing."""
    config = ModelConfig()
    return OpenAIProvider(api_key="test-key", model="gpt-4", config=config)

@pytest.mark.asyncio
async def test_generate_success(openai_provider):
    """Test successful generation."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Hello, world!"
    mock_response.model = "gpt-4"
    mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15)

    with patch.object(openai_provider.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response

        messages = [Message(role="user", content="Hello")]
        response = await openai_provider.generate(messages)

        assert response.content == "Hello, world!"
        assert response.model == "gpt-4"
        assert response.usage.total_tokens == 15

@pytest.mark.asyncio
async def test_generate_empty_messages(openai_provider):
    """Test generation with empty messages."""
    with pytest.raises(InvalidRequestError):
        await openai_provider.generate([])

@pytest.mark.asyncio
async def test_generate_error(openai_provider):
    """Test generation error handling."""
    with patch.object(openai_provider.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = Exception("API error")

        messages = [Message(role="user", content="Hello")]
        with pytest.raises(ProviderError):
            await openai_provider.generate(messages)

@pytest.mark.asyncio
async def test_stream_success(openai_provider):
    """Test successful streaming."""
    async def mock_stream():
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta.content = "Hello"
        chunk1.choices[0].finish_reason = None
        yield chunk1

        chunk2 = MagicMock()
        chunk2.choices = [MagicMock()]
        chunk2.choices[0].delta.content = " world"
        chunk2.choices[0].finish_reason = "stop"
        yield chunk2

    with patch.object(openai_provider.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_stream()

        messages = [Message(role="user", content="Hello")]
        chunks = []
        async for chunk in openai_provider.stream(messages):
            chunks.append(chunk.content)

        assert chunks == ["Hello", " world"]
