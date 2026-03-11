"""Anthropic provider implementation."""
from anthropic import AsyncAnthropic
from typing import AsyncIterator
import structlog
from models.base import BaseModelProvider
from models.types import Message, CompletionResponse, ModelConfig, StreamChunk, Usage
from models.exceptions import ProviderError, RateLimitError, InvalidRequestError

logger = structlog.get_logger(__name__)

class AnthropicProvider(BaseModelProvider):
    """Anthropic model provider."""

    def __init__(self, api_key: str, model: str, config: ModelConfig):
        super().__init__(api_key, model, config)
        self.client = AsyncAnthropic(api_key=api_key)

    def _separate_system_message(self, messages: list[Message]) -> tuple[str | None, list[Message]]:
        """Separate system message from messages list."""
        system = None
        user_messages = []
        for msg in messages:
            if msg.role == "system":
                system = msg.content
            else:
                user_messages.append(msg)
        return system, user_messages

    async def generate(self, messages: list[Message]) -> CompletionResponse:
        """Generate completion from messages."""
        if not messages:
            raise InvalidRequestError("Messages list cannot be empty", provider="anthropic")

        try:
            logger.info("anthropic_generate", model=self.model, message_count=len(messages))

            system, user_messages = self._separate_system_message(messages)

            response = await self.client.messages.create(
                model=self.model,
                messages=[{"role": m.role, "content": m.content} for m in user_messages],
                system=system,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                top_p=self.config.top_p,
            )

            usage = Usage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            )

            return CompletionResponse(
                content=response.content[0].text if response.content else "",
                model=response.model,
                usage=usage,
            )
        except Exception as e:
            error_msg = str(e)
            if "rate_limit" in error_msg.lower():
                raise RateLimitError(f"Anthropic rate limit: {error_msg}", provider="anthropic")
            raise ProviderError(f"Anthropic error: {error_msg}", provider="anthropic", original_error=e)

    async def stream(self, messages: list[Message]) -> AsyncIterator[StreamChunk]:
        """Stream completion from messages."""
        if not messages:
            raise InvalidRequestError("Messages list cannot be empty", provider="anthropic")

        try:
            logger.info("anthropic_stream", model=self.model, message_count=len(messages))

            system, user_messages = self._separate_system_message(messages)

            async with self.client.messages.stream(
                model=self.model,
                messages=[{"role": m.role, "content": m.content} for m in user_messages],
                system=system,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                top_p=self.config.top_p,
            ) as stream:
                async for text in stream.text_stream:
                    yield StreamChunk(content=text, finish_reason=None)
        except Exception as e:
            error_msg = str(e)
            if "rate_limit" in error_msg.lower():
                raise RateLimitError(f"Anthropic rate limit: {error_msg}", provider="anthropic")
            raise ProviderError(f"Anthropic error: {error_msg}", provider="anthropic", original_error=e)
