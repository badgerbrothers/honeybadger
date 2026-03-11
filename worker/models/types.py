"""Shared types and enums for model abstraction."""
from pydantic import BaseModel, Field
from enum import Enum
from typing import Literal

class ProviderType(str, Enum):
    """Model provider types."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"

class Message(BaseModel):
    """Chat message."""
    role: Literal["system", "user", "assistant"]
    content: str

class ModelConfig(BaseModel):
    """Model configuration."""
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2000, gt=0)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)

class Usage(BaseModel):
    """Token usage information."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class CompletionResponse(BaseModel):
    """Model completion response."""
    content: str
    model: str
    usage: Usage | None = None

class StreamChunk(BaseModel):
    """Streaming response chunk."""
    content: str
    finish_reason: str | None = None
