"""Unit tests for model abstraction."""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from models.tool_calling import Message
from models.openai_compat import OpenAIProvider
from models.anthropic_native import AnthropicProvider


@pytest.mark.asyncio
@patch('models.openai_compat.openai.AsyncOpenAI')
async def test_openai_chat_completion(mock_openai):
    """Test OpenAI chat completion."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Hello", tool_calls=None), finish_reason="stop")]
    mock_response.usage = Mock(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    mock_openai.return_value = mock_client

    provider = OpenAIProvider(api_key="test-key")
    messages = [Message(role="user", content="Hi")]
    response = await provider.chat_completion(messages)

    assert response.content == "Hello"
    assert response.finish_reason == "stop"
    assert response.usage["total_tokens"] == 15


@pytest.mark.asyncio
@patch('models.anthropic_native.anthropic.AsyncAnthropic')
async def test_anthropic_chat_completion(mock_anthropic):
    """Test Anthropic chat completion."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock(type="text", text="Hello")]
    mock_response.stop_reason = "end_turn"
    mock_response.usage = Mock(input_tokens=10, output_tokens=5)
    mock_client.messages.create = AsyncMock(return_value=mock_response)
    mock_anthropic.return_value = mock_client

    provider = AnthropicProvider(api_key="test-key")
    messages = [Message(role="user", content="Hi")]
    response = await provider.chat_completion(messages)

    assert response.content == "Hello"
    assert response.finish_reason == "end_turn"
