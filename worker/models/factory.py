"""Factory for creating model provider instances."""
from models.base import BaseModelProvider
from models.openai_provider import OpenAIProvider
from models.anthropic_provider import AnthropicProvider
from models.types import ProviderType, ModelConfig
from models.exceptions import ConfigurationError
from config import settings

def create_model_provider(
    provider: ProviderType | None = None,
    model: str | None = None,
    config: ModelConfig | None = None,
) -> BaseModelProvider:
    """Create a model provider instance."""
    provider = provider or settings.model_provider
    model = model or settings.default_model
    config = config or ModelConfig(
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
    )

    if provider == ProviderType.OPENAI:
        if not settings.openai_api_key:
            raise ConfigurationError("OPENAI_API_KEY not configured", provider="openai")
        return OpenAIProvider(settings.openai_api_key, model, config)
    elif provider == ProviderType.ANTHROPIC:
        if not settings.anthropic_api_key:
            raise ConfigurationError("ANTHROPIC_API_KEY not configured", provider="anthropic")
        return AnthropicProvider(settings.anthropic_api_key, model, config)
    else:
        raise ConfigurationError(f"Unknown provider: {provider}")
