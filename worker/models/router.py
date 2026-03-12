"""Model router for determining provider from model name."""
from models.registry import get_provider_for_model, is_model_supported
from models.types import ProviderType
from models.exceptions import ConfigurationError

class ModelRouter:
    """Routes model names to appropriate providers."""

    def normalize_model_name(self, model: str) -> str:
        """Normalize model name (lowercase, strip whitespace)."""
        return model.lower().strip()

    def validate_model(self, model: str) -> None:
        """Validate that model is supported."""
        if not is_model_supported(model):
            raise ConfigurationError(f"Unsupported model: {model}")

    def route(self, model: str) -> ProviderType:
        """Route model name to provider."""
        normalized = self.normalize_model_name(model)
        self.validate_model(normalized)
        return get_provider_for_model(normalized)
