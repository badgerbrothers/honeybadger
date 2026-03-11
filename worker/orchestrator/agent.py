"""Agent orchestration loop."""
import uuid
import structlog
from models.tool_calling import ModelProvider, Message
from tools.tool_base import Tool
from orchestrator.exceptions import AgentExecutionError, MaxIterationsError

logger = structlog.get_logger(__name__)


class Agent:
    """Agent orchestrator with reasoning-action-observation loop."""

    def __init__(
        self,
        task_run_id: uuid.UUID,
        model: ModelProvider,
        tools: list[Tool],
        max_iterations: int = 20
    ):
        self.task_run_id = task_run_id
        self.model = model
        self.tools = {tool.name: tool for tool in tools}
        self.max_iterations = max_iterations
        self.messages: list[Message] = []
        self.iteration = 0

    async def run(self, goal: str, system_prompt: str | None = None) -> str:
        """Execute agent loop until completion."""
        logger.info("agent_started", task_run_id=str(self.task_run_id), goal=goal)

        if system_prompt:
            self.messages.append(Message(role="system", content=system_prompt))
        self.messages.append(Message(role="user", content=goal))

        tool_schemas = [tool.to_openai_tool() for tool in self.tools.values()]

        while self.iteration < self.max_iterations:
            self.iteration += 1
            logger.info("agent_iteration", task_run_id=str(self.task_run_id), iteration=self.iteration)

            try:
                response = await self.model.chat_completion(
                    messages=self.messages,
                    tools=tool_schemas,
                    temperature=0.7
                )

                if response.tool_calls:
                    logger.info("tool_calls_requested", task_run_id=str(self.task_run_id), count=len(response.tool_calls))

                    self.messages.append(Message(
                        role="assistant",
                        content=response.content or "",
                        tool_calls=[{"id": tc.id, "name": tc.name, "arguments": tc.arguments} for tc in response.tool_calls]
                    ))

                    for tool_call in response.tool_calls:
                        result = await self._execute_tool(tool_call.name, tool_call.arguments)

                        self.messages.append(Message(
                            role="user",
                            content=f"Tool {tool_call.name} result: {result.output if result.success else f'ERROR: {result.error}'}",
                            tool_call_id=tool_call.id
                        ))

                elif response.finish_reason == "stop":
                    logger.info("agent_completed", task_run_id=str(self.task_run_id), iterations=self.iteration)
                    return response.content or ""

                else:
                    raise AgentExecutionError(f"Unexpected finish reason: {response.finish_reason}")

            except Exception as e:
                logger.error("agent_error", task_run_id=str(self.task_run_id), error=str(e))
                raise AgentExecutionError(f"Agent execution failed: {e}")

        raise MaxIterationsError(f"Agent exceeded maximum iterations: {self.max_iterations}")

    async def _execute_tool(self, tool_name: str, arguments: dict):
        """Execute a tool by name."""
        logger.info("executing_tool", task_run_id=str(self.task_run_id), tool=tool_name, args=arguments)

        if tool_name not in self.tools:
            from tools.tool_base import ToolResult
            return ToolResult(success=False, output="", error=f"Unknown tool: {tool_name}")

        try:
            tool = self.tools[tool_name]
            result = await tool.execute(**arguments)
            logger.info("tool_executed", task_run_id=str(self.task_run_id), tool=tool_name, success=result.success)
            return result
        except Exception as e:
            logger.error("tool_execution_failed", task_run_id=str(self.task_run_id), tool=tool_name, error=str(e))
            from tools.tool_base import ToolResult
            return ToolResult(success=False, output="", error=str(e))
