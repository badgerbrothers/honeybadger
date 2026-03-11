"""Tests for Anthropic provider."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from models.anthropic_provider import AnthropicProvider
from models.types import Message, ModelConfig
from models.exceptions import InvalidRequestError, ProviderError

@pytest.fixture
def anthropic_provider():
    """Create Anthropic provider for testing."""
    config = ModelConfig()
    return AnthropicProvider(api_key="test-key", model="claude-3-opus-20240229", config=config)

@pytest.mark.asyncio
async def test_generate_success(anthropic_provider):
    """Test successful generation."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Hello, world!")]
    mock_response.model = "claude-3-opus-20240229"
    mock_response.usage = MagicMock(input_tokens=10, output_tokens=5)

    with patch.object(anthropic_provider.client.messages, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response

        messages = [Message(role="user", content="Hello")]
        response = await anthropic_provider.generate(messages)

        assert response.content == "Hello, world!"
        assert response.model == "claude-3-opus-20240229"
        assert response.usage.total_tokens == 15

@pytest.mark.asyncio
async def test_generate_with_system_message(anthropic_provider):
    """Test generation with system message separation."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Response")]
    mock_response.model = "claude-3-opus-20240229"
    mock_response.usage = MagicMock(input_tokens=10, output_tokens=5)

    with patch.object(anthropic_provider.client.messages, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response

        messages = [
            Message(role="system", content="You are helpful"),
            Message(role="user", content="Hello")
        ]
        await anthropic_provider.generate(messages)

        call_args = mock_create.call_args
        assert call_args.kwargs['system'] == "You are helpful"
        assert len(call_args.kwargs['messages']) == 1

@pytest.mark.asyncio
async def test_generate_empty_messages(anthropic_provider):
    """Test generation with empty messages."""
    with pytest.raises(InvalidRequestError):
        await anthropic_provider.generate([])

@pytest.mark.asyncio
async def test_generate_error(anthropic_provider):
    """Test generation error handling."""
    with patch.object(anthropic_provider.client.messages, 'create', new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = Exception("API error")

        messages = [Message(role="user", content="Hello")]
        with pytest.raises(ProviderError):
            await anthropic_provider.generate(messages)
