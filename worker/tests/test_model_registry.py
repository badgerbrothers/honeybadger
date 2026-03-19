"""Tests for model registry."""
import pytest
from models.registry import get_provider_for_model, is_model_supported, MODEL_REGISTRY
from models.types import ProviderType

def test_get_provider_for_openai_models():
    """Test get_provider_for_model with OpenAI models."""
    assert get_provider_for_model("gpt-4") == ProviderType.OPENAI
    assert get_provider_for_model("gpt-3.5-turbo") == ProviderType.OPENAI
    assert get_provider_for_model("gpt-5.3-codex") == ProviderType.OPENAI

def test_get_provider_for_anthropic_models():
    """Test get_provider_for_model with Anthropic models."""
    assert get_provider_for_model("claude-3-opus-20240229") == ProviderType.ANTHROPIC
    assert get_provider_for_model("claude-3-sonnet-20240229") == ProviderType.ANTHROPIC

def test_is_model_supported():
    """Test is_model_supported for valid/invalid models."""
    assert is_model_supported("gpt-4") is True
    assert is_model_supported("gpt-5.3-codex") is True
    assert is_model_supported("unknown-model") is False

def test_case_insensitive_matching():
    """Test case-insensitive model names."""
    assert get_provider_for_model("GPT-4") == ProviderType.OPENAI
    assert get_provider_for_model("Gpt-4") == ProviderType.OPENAI

def test_unknown_model_raises_error():
    """Test unknown model raises ValueError."""
    with pytest.raises(ValueError, match="Unsupported model"):
        get_provider_for_model("unknown-model")

def test_registry_not_empty():
    """Test MODEL_REGISTRY is not empty."""
    assert len(MODEL_REGISTRY) > 0
