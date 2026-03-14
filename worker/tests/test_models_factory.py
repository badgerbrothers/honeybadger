"""Tests for factory function."""
import pytest
from unittest.mock import patch
from models.anthropic_native import AnthropicProvider as AnthropicToolCallingProvider
from models.factory import create_model_provider
from models.openai_compat import OpenAIProvider as OpenAIToolCallingProvider
from models.types import ProviderType
from models.exceptions import ConfigurationError

@patch('config.settings')
def test_create_openai_provider(mock_settings):
    """Test OpenAI provider creation."""
    mock_settings.openai_api_key = "test-key"
    mock_settings.openai_base_url = None
    mock_settings.default_model = "gpt-4"
    mock_settings.temperature = 0.7
    mock_settings.max_tokens = 2000

    provider = create_model_provider()
    assert isinstance(provider, OpenAIToolCallingProvider)
    assert provider.model == "gpt-4"

@patch('config.settings')
def test_create_anthropic_provider(mock_settings):
    """Test Anthropic provider creation."""
    mock_settings.anthropic_api_key = "test-key"
    mock_settings.default_model = "claude-3-opus-20240229"
    mock_settings.temperature = 0.7
    mock_settings.max_tokens = 2000

    provider = create_model_provider(provider=ProviderType.ANTHROPIC)
    assert isinstance(provider, AnthropicToolCallingProvider)

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
