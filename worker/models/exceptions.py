"""Custom exceptions for model operations."""
from typing import Any

class ModelError(Exception):
    """Base exception for model operations."""
    def __init__(self, message: str, provider: str | None = None, original_error: Any = None):
        self.provider = provider
        self.original_error = original_error
        super().__init__(message)

class ProviderError(ModelError):
    """Provider-specific error."""
    pass

class ConfigurationError(ModelError):
    """Configuration error (missing API keys, invalid config)."""
    pass

class RateLimitError(ModelError):
    """Rate limiting error."""
    def __init__(self, message: str, provider: str | None = None, retry_after: int | None = None):
        super().__init__(message, provider)
        self.retry_after = retry_after

class InvalidRequestError(ModelError):
    """Invalid request error."""
    pass
