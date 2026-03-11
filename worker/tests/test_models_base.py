"""Tests for base types and exceptions."""
import pytest
from models.types import Message, ModelConfig, CompletionResponse, Usage, StreamChunk
from models.exceptions import ModelError, ProviderError, ConfigurationError

def test_message_validation():
    """Test Message validation."""
    msg = Message(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"

def test_model_config_defaults():
    """Test ModelConfig defaults."""
    config = ModelConfig()
    assert config.temperature == 0.7
    assert config.max_tokens == 2000
    assert config.top_p == 1.0

def test_model_config_validation():
    """Test ModelConfig validation."""
    with pytest.raises(Exception):
        ModelConfig(temperature=3.0)  # Out of range

def test_completion_response():
    """Test CompletionResponse structure."""
    usage = Usage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
    response = CompletionResponse(content="Hello", model="gpt-4", usage=usage)
    assert response.content == "Hello"
    assert response.model == "gpt-4"
    assert response.usage.total_tokens == 30

def test_stream_chunk():
    """Test StreamChunk structure."""
    chunk = StreamChunk(content="Hello", finish_reason=None)
    assert chunk.content == "Hello"
    assert chunk.finish_reason is None

def test_exception_hierarchy():
    """Test exception hierarchy."""
    assert issubclass(ProviderError, ModelError)
    assert issubclass(ConfigurationError, ModelError)

def test_exception_context():
    """Test exception includes context."""
    error = ProviderError("Test error", provider="openai", original_error=ValueError("Original"))
    assert error.provider == "openai"
    assert error.original_error is not None
