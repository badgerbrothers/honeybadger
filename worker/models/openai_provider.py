"""OpenAI provider implementation."""
from openai import AsyncOpenAI
from typing import AsyncIterator
import structlog
from models.base import BaseModelProvider
from models.types import Message, CompletionResponse, ModelConfig, StreamChunk, Usage
from models.exceptions import ProviderError, RateLimitError, InvalidRequestError

logger = structlog.get_logger(__name__)

class OpenAIProvider(BaseModelProvider):
    """OpenAI model provider."""

    def __init__(self, api_key: str, model: str, config: ModelConfig):
        super().__init__(api_key, model, config)
        self.client = AsyncOpenAI(api_key=api_key)

    async def generate(self, messages: list[Message]) -> CompletionResponse:
        """Generate completion from messages."""
        if not messages:
            raise InvalidRequestError("Messages list cannot be empty", provider="openai")

        try:
            logger.info("openai_generate", model=self.model, message_count=len(messages))

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                top_p=self.config.top_p,
            )

            usage = Usage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            ) if response.usage else None

            return CompletionResponse(
                content=response.choices[0].message.content or "",
                model=response.model,
                usage=usage,
            )
        except Exception as e:
            error_msg = str(e)
            if "rate_limit" in error_msg.lower():
                raise RateLimitError(f"OpenAI rate limit: {error_msg}", provider="openai")
            raise ProviderError(f"OpenAI error: {error_msg}", provider="openai", original_error=e)

    async def stream(self, messages: list[Message]) -> AsyncIterator[StreamChunk]:
        """Stream completion from messages."""
        if not messages:
            raise InvalidRequestError("Messages list cannot be empty", provider="openai")

        try:
            logger.info("openai_stream", model=self.model, message_count=len(messages))

            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                top_p=self.config.top_p,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield StreamChunk(
                        content=chunk.choices[0].delta.content,
                        finish_reason=chunk.choices[0].finish_reason,
                    )
        except Exception as e:
            error_msg = str(e)
            if "rate_limit" in error_msg.lower():
                raise RateLimitError(f"OpenAI rate limit: {error_msg}", provider="openai")
            raise ProviderError(f"OpenAI error: {error_msg}", provider="openai", original_error=e)
