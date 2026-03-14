"""Anthropic native model provider with tool calling."""
try:
    import anthropic
except ModuleNotFoundError:  # pragma: no cover - optional dependency in local/dev envs
    anthropic = None
from models.tool_calling import ModelProvider, Message, ModelResponse, ToolCall
from models.exceptions import ModelError


class AnthropicProvider(ModelProvider):
    """Anthropic native SDK provider."""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.client = anthropic.AsyncAnthropic(api_key=api_key) if anthropic else None
        self.model = model

    async def chat_completion(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> ModelResponse:
        try:
            if self.client is None:
                raise ModelError("Anthropic SDK not installed. Add `anthropic` to dependencies.")
            anthropic_messages = [{"role": msg.role, "content": msg.content} for msg in messages if msg.role != "system"]
            system = next((msg.content for msg in messages if msg.role == "system"), None)
            kwargs = {
                "model": self.model,
                "messages": anthropic_messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if system:
                kwargs["system"] = system
            if tools:
                kwargs["tools"] = tools

            response = await self.client.messages.create(**kwargs)

            content = None
            tool_calls = None
            for block in response.content:
                if block.type == "text":
                    content = block.text
                elif block.type == "tool_use":
                    if tool_calls is None:
                        tool_calls = []
                    tool_calls.append(ToolCall(id=block.id, name=block.name, arguments=block.input))

            return ModelResponse(
                content=content,
                tool_calls=tool_calls,
                finish_reason=response.stop_reason,
                usage={"prompt_tokens": response.usage.input_tokens, "completion_tokens": response.usage.output_tokens, "total_tokens": response.usage.input_tokens + response.usage.output_tokens}
            )
        except Exception as e:
            raise ModelError(f"Anthropic API call failed: {e}")
