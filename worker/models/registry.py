"""Model registry mapping model names to providers."""
from models.types import ProviderType

# Model registry mapping model names (lowercase) to providers
MODEL_REGISTRY = {
    # OpenAI models
    "gpt-4": ProviderType.OPENAI,
    "gpt-4-turbo": ProviderType.OPENAI,
    "gpt-4-turbo-preview": ProviderType.OPENAI,
    "gpt-3.5-turbo": ProviderType.OPENAI,
    "gpt-3.5-turbo-16k": ProviderType.OPENAI,
    # Anthropic models
    "claude-3-opus-20240229": ProviderType.ANTHROPIC,
    "claude-3-sonnet-20240229": ProviderType.ANTHROPIC,
    "claude-3-haiku-20240307": ProviderType.ANTHROPIC,
}

def get_provider_for_model(model: str) -> ProviderType:
    """Get provider for a given model name."""
    normalized = model.lower().strip()
    if normalized not in MODEL_REGISTRY:
        raise ValueError(f"Unsupported model: {model}")
    return MODEL_REGISTRY[normalized]

def is_model_supported(model: str) -> bool:
    """Check if a model is supported."""
    normalized = model.lower().strip()
    return normalized in MODEL_REGISTRY

def get_supported_models() -> list[str]:
    """Get list of all supported model names."""
    return list(MODEL_REGISTRY.keys())
