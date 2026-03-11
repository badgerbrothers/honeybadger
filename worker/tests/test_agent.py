"""Integration tests for agent orchestrator."""
import pytest
import uuid
from unittest.mock import AsyncMock, Mock
from orchestrator.agent import Agent
from models.tool_calling import ModelProvider, ModelResponse, ToolCall
from tools.tool_base import Tool, ToolResult


class MockTool(Tool):
    """Mock tool for testing."""

    @property
    def name(self) -> str:
        return "mock_tool"

    @property
    def description(self) -> str:
        return "A mock tool"

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    async def execute(self, **kwargs) -> ToolResult:
        return ToolResult(success=True, output="mock result")


@pytest.mark.asyncio
async def test_agent_completes_without_tools():
    """Test agent completes task without tool calls."""
    mock_model = Mock(spec=ModelProvider)
    mock_model.chat_completion = AsyncMock(return_value=ModelResponse(
        content="Task completed",
        tool_calls=None,
        finish_reason="stop"
    ))

    agent = Agent(task_run_id=uuid.uuid4(), model=mock_model, tools=[])
    result = await agent.run(goal="Test goal")

    assert result == "Task completed"
    assert agent.iteration == 1


@pytest.mark.asyncio
async def test_agent_executes_tool():
    """Test agent executes tool and completes."""
    mock_model = Mock(spec=ModelProvider)
    mock_tool = MockTool()

    mock_model.chat_completion = AsyncMock(side_effect=[
        ModelResponse(
            content="Using tool",
            tool_calls=[ToolCall(id="1", name="mock_tool", arguments={})],
            finish_reason="tool_calls"
        ),
        ModelResponse(
            content="Task completed with tool result",
            tool_calls=None,
            finish_reason="stop"
        )
    ])

    agent = Agent(task_run_id=uuid.uuid4(), model=mock_model, tools=[mock_tool])
    result = await agent.run(goal="Test goal")

    assert "Task completed" in result
    assert agent.iteration == 2


@pytest.mark.asyncio
async def test_agent_max_iterations():
    """Test agent raises error on max iterations."""
    mock_model = Mock(spec=ModelProvider)
    mock_model.chat_completion = AsyncMock(return_value=ModelResponse(
        content="Thinking",
        tool_calls=[ToolCall(id="1", name="mock_tool", arguments={})],
        finish_reason="tool_calls"
    ))

    agent = Agent(task_run_id=uuid.uuid4(), model=mock_model, tools=[MockTool()], max_iterations=3)

    with pytest.raises(Exception) as exc_info:
        await agent.run(goal="Test goal")

    assert "maximum iterations" in str(exc_info.value).lower()
