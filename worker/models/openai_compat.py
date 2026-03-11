"""OpenAI-compatible model provider with tool calling."""
import openai
import json
from models.tool_calling import ModelProvider, Message, ModelResponse, ToolCall
from orchestrator.exceptions import ModelError


class OpenAIProvider(ModelProvider):
    """OpenAI-compatible API provider."""

    def __init__(self, api_key: str, base_url: str | None = None, model: str = "gpt-4"):
        self.client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    async def chat_completion(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> ModelResponse:
        try:
            openai_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
            kwargs = {"model": self.model, "messages": openai_messages, "temperature": temperature, "max_tokens": max_tokens}
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            response = await self.client.chat.completions.create(**kwargs)
            choice = response.choices[0]

            tool_calls = None
            if choice.message.tool_calls:
                try:
                    tool_calls = [
                        ToolCall(id=tc.id, name=tc.function.name, arguments=json.loads(tc.function.arguments))
                        for tc in choice.message.tool_calls
                    ]
                except json.JSONDecodeError as e:
                    raise ModelError(f"Invalid JSON in tool arguments: {e}")

            return ModelResponse(
                content=choice.message.content,
                tool_calls=tool_calls,
                finish_reason=choice.finish_reason,
                usage={"prompt_tokens": response.usage.prompt_tokens, "completion_tokens": response.usage.completion_tokens, "total_tokens": response.usage.total_tokens}
            )
        except Exception as e:
            raise ModelError(f"OpenAI API call failed: {e}")
