"""Factory for creating model provider instances."""
from models.anthropic_native import AnthropicProvider
from models.openai_compat import OpenAIProvider
from models.tool_calling import ModelProvider
from models.types import ProviderType, ModelConfig
from models.exceptions import ConfigurationError
from models.router import ModelRouter


def create_model_provider(
    provider: ProviderType | None = None,
    model: str | None = None,
    config: ModelConfig | dict | None = None,
) -> ModelProvider:
    """Create a model provider instance."""
    from config import settings

    router = ModelRouter()
    model = model or settings.default_model
    if config is None:
        config = ModelConfig(
            temperature=settings.temperature,
            max_tokens=settings.max_tokens,
        )
    elif isinstance(config, dict):
        config = ModelConfig(
            temperature=config.get("temperature", settings.temperature),
            max_tokens=config.get("max_tokens", settings.max_tokens),
            top_p=config.get("top_p", 1.0),
        )

    # Auto-determine provider from model if not specified
    if provider is None:
        provider = router.route(model)

    if provider == ProviderType.OPENAI:
        if not settings.openai_api_key:
            raise ConfigurationError("OPENAI_API_KEY not configured", provider="openai")
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=model,
        )
    elif provider == ProviderType.ANTHROPIC:
        if not settings.anthropic_api_key:
            raise ConfigurationError("ANTHROPIC_API_KEY not configured", provider="anthropic")
        return AnthropicProvider(
            api_key=settings.anthropic_api_key,
            model=model,
        )
    else:
        raise ConfigurationError(f"Unknown provider: {provider}")
