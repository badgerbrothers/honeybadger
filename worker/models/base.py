"""Abstract base class for model providers."""
from abc import ABC, abstractmethod
from typing import AsyncIterator
from models.types import Message, CompletionResponse, ModelConfig, StreamChunk

class BaseModelProvider(ABC):
    """Abstract base class for model providers."""

    def __init__(self, api_key: str, model: str, config: ModelConfig):
        self.api_key = api_key
        self.model = model
        self.config = config
        self.validate_config()

    def validate_config(self) -> None:
        """Validate configuration."""
        if not self.api_key:
            raise ValueError("API key is required")
        if not self.model:
            raise ValueError("Model name is required")

    @abstractmethod
    async def generate(self, messages: list[Message]) -> CompletionResponse:
        """Generate completion from messages."""
        pass

    @abstractmethod
    async def stream(self, messages: list[Message]) -> AsyncIterator[StreamChunk]:
        """Stream completion from messages."""
        pass
