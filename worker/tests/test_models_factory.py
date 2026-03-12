"""Tests for factory function."""
import pytest
from unittest.mock import patch
from models.factory import create_model_provider
from models.types import ProviderType
from models.exceptions import ConfigurationError
from models.openai_provider import OpenAIProvider
from models.anthropic_provider import AnthropicProvider

@patch('config.settings')
def test_create_openai_provider(mock_settings):
    """Test OpenAI provider creation."""
    mock_settings.openai_api_key = "test-key"
    mock_settings.default_model = "gpt-4"
    mock_settings.temperature = 0.7
    mock_settings.max_tokens = 2000

    provider = create_model_provider()
    assert isinstance(provider, OpenAIProvider)
    assert provider.model == "gpt-4"

@patch('config.settings')
def test_create_anthropic_provider(mock_settings):
    """Test Anthropic provider creation."""
    mock_settings.anthropic_api_key = "test-key"
    mock_settings.default_model = "claude-3-opus-20240229"
    mock_settings.temperature = 0.7
    mock_settings.max_tokens = 2000

    provider = create_model_provider(provider=ProviderType.ANTHROPIC)
    assert isinstance(provider, AnthropicProvider)

@patch('config.settings')
def test_missing_openai_key(mock_settings):
    """Test missing OpenAI API key raises error."""
    mock_settings.openai_api_key = None
    mock_settings.default_model = "gpt-4"
    mock_settings.temperature = 0.7
    mock_settings.max_tokens = 2000

    with pytest.raises(ConfigurationError):
        create_model_provider()

@patch('config.settings')
def test_missing_anthropic_key(mock_settings):
    """Test missing Anthropic API key raises error."""
    mock_settings.anthropic_api_key = None
    mock_settings.default_model = "claude-3-opus-20240229"
    mock_settings.temperature = 0.7
    mock_settings.max_tokens = 2000

    with pytest.raises(ConfigurationError):
        create_model_provider(provider=ProviderType.ANTHROPIC)
