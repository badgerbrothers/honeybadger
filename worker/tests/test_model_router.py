"""Tests for model router."""
import pytest
from models.router import ModelRouter
from models.types import ProviderType
from models.exceptions import ConfigurationError

@pytest.fixture
def router():
    """Create router for testing."""
    return ModelRouter()

def test_route_openai_models(router):
    """Test route() returns correct provider for OpenAI models."""
    assert router.route("gpt-4") == ProviderType.OPENAI
    assert router.route("gpt-3.5-turbo") == ProviderType.OPENAI

def test_route_anthropic_models(router):
    """Test route() returns correct provider for Anthropic models."""
    assert router.route("claude-3-opus-20240229") == ProviderType.ANTHROPIC

def test_validate_model_raises_for_unsupported(router):
    """Test validate_model() raises for unsupported models."""
    with pytest.raises(ConfigurationError, match="Unsupported model"):
        router.validate_model("unknown-model")

def test_normalize_model_name(router):
    """Test normalize_model_name() handles case and whitespace."""
    assert router.normalize_model_name("  GPT-4  ") == "gpt-4"
    assert router.normalize_model_name("Claude-3-Opus-20240229") == "claude-3-opus-20240229"

def test_route_with_whitespace(router):
    """Test route() handles whitespace in model names."""
    assert router.route("  gpt-4  ") == ProviderType.OPENAI
