"""Model abstraction for tool calling."""
from abc import ABC, abstractmethod
from typing import Any
from dataclasses import dataclass


@dataclass
class Message:
    """Chat message."""
    role: str
    content: str
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None


@dataclass
class ToolCall:
    """Tool call from model."""
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ModelResponse:
    """Model completion response."""
    content: str | None
    tool_calls: list[ToolCall] | None
    finish_reason: str
    usage: dict[str, int] | None = None


class ModelProvider(ABC):
    """Abstract model provider interface."""

    @abstractmethod
    async def chat_completion(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> ModelResponse:
        """Generate chat completion with optional tool use."""
        pass
