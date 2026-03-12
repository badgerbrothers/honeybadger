# Feature: Basic Agent Orchestrator

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Implement a basic agent orchestration system that executes a simple agent loop: receive task goal, call LLM to decide next action, execute file tools (list, read, write), and iterate until task completion. This is the core execution engine that will power autonomous task completion in the Badgers MVP.

The orchestrator manages the agent's reasoning loop, tool execution, and state tracking. It integrates with the sandbox manager (already implemented) and will use a unified model abstraction layer to call LLMs (OpenAI/Anthropic).

## User Story

As a task execution worker
I want to orchestrate an agent that can autonomously complete tasks using tools
So that users can delegate multi-step workflows without manual intervention

## Problem Statement

Currently, the worker has sandbox management but no agent execution logic. We need the core orchestration loop that:
1. Takes a task goal as input
2. Calls an LLM to reason about next steps
3. Executes tools (starting with file operations)
4. Tracks execution state and history
5. Iterates until task completion or failure

## Solution Statement

Implement a minimal agent orchestrator with:
- **Agent Loop**: Iterative reasoning-action-observation cycle
- **Model Abstraction**: Unified interface for OpenAI/Anthropic SDKs
- **Tool System**: Base tool interface + file operations (list, read, write)
- **State Management**: Track conversation history, tool calls, and execution status
- **Integration**: Use existing SandboxManager for isolated execution

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: High
**Primary Systems Affected**: worker/orchestrator, worker/models, worker/tools
**Dependencies**: openai>=1.10.0, anthropic>=0.18.0, structlog>=24.1.0, existing sandbox module

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `worker/sandbox/manager.py` (lines 1-56) - Why: SandboxManager context manager pattern to follow
- `worker/sandbox/exceptions.py` (lines 1-22) - Why: Exception hierarchy pattern for orchestrator exceptions
- `worker/pyproject.toml` (lines 1-29) - Why: Dependencies already available (openai, anthropic, structlog)
- `CLAUDE.md` (lines 88-116) - Why: Tool system design and architecture flow
- `.claude/PRD.md` (lines 242-301) - Why: Agent loop architecture and tool interface pattern

### New Files to Create

- `worker/models/base.py` - Unified model interface abstraction
- `worker/models/openai_compat.py` - OpenAI-compatible API implementation
- `worker/models/anthropic_native.py` - Anthropic native SDK implementation
- `worker/tools/base.py` - Base tool interface and result types
- `worker/tools/file.py` - File operations (list, read, write)
- `worker/orchestrator/agent.py` - Main agent execution loop
- `worker/orchestrator/exceptions.py` - Orchestrator-specific exceptions
- `worker/tests/test_models.py` - Model abstraction tests
- `worker/tests/test_tools.py` - Tool execution tests
- `worker/tests/test_agent.py` - Agent orchestrator tests

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [OpenAI Chat Completions API](https://platform.openai.com/docs/api-reference/chat/create)
  - Specific section: Function calling with tools
  - Why: Required for tool-use pattern with OpenAI models
- [Anthropic Messages API](https://docs.anthropic.com/en/api/messages)
  - Specific section: Tool use (function calling)
  - Why: Required for tool-use pattern with Anthropic models
- [Anthropic Tool Use Guide](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
  - Specific section: Tool use workflow
  - Why: Shows proper tool call/result cycle

### Patterns to Follow

**Exception Hierarchy Pattern** (from `worker/sandbox/exceptions.py`):
```python
class BaseError(Exception):
    """Base exception."""
    pass

class SpecificError(BaseError):
    """Specific error case."""
    pass
```

**Async Context Manager Pattern** (from `worker/sandbox/manager.py:47-55`):
```python
async def __aenter__(self):
    await self.create()
    return self

async def __aexit__(self, exc_type, exc_val, exc_tb):
    await self.destroy()
    return False
```

**Structured Logging** (from tech stack):
```python
import structlog
logger = structlog.get_logger(__name__)
logger.info("event_name", key1=value1, key2=value2)
```

**Type Hints** (from existing code):
- Use Python 3.11+ type hints throughout
- Use `tuple[int, str]` not `Tuple[int, str]`
- Use `list[str]` not `List[str]`

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation - Model Abstraction Layer

Create unified interface for LLM providers to enable model-agnostic orchestration.

**Tasks:**
- Define base model interface with chat completion method
- Implement OpenAI-compatible provider
- Implement Anthropic native provider
- Add model configuration and provider selection

### Phase 2: Tool System Foundation

Build tool interface and basic file operations that agent can execute.

**Tasks:**
- Define base tool interface (name, description, schema, execute)
- Implement file.list tool
- Implement file.read tool
- Implement file.write tool
- Create tool registry for dynamic tool loading

### Phase 3: Agent Orchestrator Core

Implement the main agent execution loop with reasoning-action-observation cycle.

**Tasks:**
- Create orchestrator exception hierarchy
- Implement agent state management
- Build main agent loop (reason → act → observe)
- Add tool call parsing and execution
- Implement completion detection logic

### Phase 4: Testing & Validation

Comprehensive testing of all components with mocks and integration tests.

**Tasks:**
- Unit tests for model abstraction
- Unit tests for tool implementations
- Integration tests for agent loop
- Validation commands for linting and testing

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Task 1: CREATE worker/orchestrator/exceptions.py

- **IMPLEMENT**: Orchestrator exception hierarchy
- **PATTERN**: Mirror `worker/sandbox/exceptions.py` structure
- **IMPORTS**: None (base exceptions only)
- **VALIDATE**: `cd worker && uv run python -c "from orchestrator.exceptions import *"`

```python
"""Orchestrator exceptions."""

class OrchestratorError(Exception):
    """Base exception for orchestrator operations."""
    pass

class AgentExecutionError(OrchestratorError):
    """Agent execution failed."""
    pass

class ToolExecutionError(OrchestratorError):
    """Tool execution failed."""
    pass

class ModelError(OrchestratorError):
    """Model API call failed."""
    pass

class MaxIterationsError(OrchestratorError):
    """Agent exceeded maximum iterations."""
    pass
```

---


### Task 2: CREATE worker/models/base.py

- **IMPLEMENT**: Unified model interface with chat completion method
- **PATTERN**: Abstract base class with async methods
- **IMPORTS**: `from abc import ABC, abstractmethod`, `from typing import Any`, `from dataclasses import dataclass`
- **VALIDATE**: `cd worker && uv run python -c "from models.base import ModelProvider, Message, ToolCall"`

```python
"""Base model abstraction interface."""
from abc import ABC, abstractmethod
from typing import Any
from dataclasses import dataclass

@dataclass
class Message:
    """Chat message."""
    role: str  # "user", "assistant", "system"
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
    finish_reason: str  # "stop", "tool_calls", "length"
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
```

---

### Task 3: CREATE worker/models/openai_compat.py

- **IMPLEMENT**: OpenAI-compatible API provider
- **PATTERN**: Implement ModelProvider interface
- **IMPORTS**: `import openai`, `import json`, `from .base import ModelProvider, Message, ModelResponse, ToolCall`
- **GOTCHA**: Handle both tool_calls and regular content responses
- **VALIDATE**: `cd worker && uv run python -c "from models.openai_compat import OpenAIProvider"`

```python
"""OpenAI-compatible model provider."""
import openai
import json
from .base import ModelProvider, Message, ModelResponse, ToolCall
from ..orchestrator.exceptions import ModelError

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
                tool_calls = [
                    ToolCall(id=tc.id, name=tc.function.name, arguments=json.loads(tc.function.arguments))
                    for tc in choice.message.tool_calls
                ]

            return ModelResponse(
                content=choice.message.content,
                tool_calls=tool_calls,
                finish_reason=choice.finish_reason,
                usage={"prompt_tokens": response.usage.prompt_tokens, "completion_tokens": response.usage.completion_tokens, "total_tokens": response.usage.total_tokens}
            )
        except Exception as e:
            raise ModelError(f"OpenAI API call failed: {e}")
```

---

### Task 4: CREATE worker/models/anthropic_native.py

- **IMPLEMENT**: Anthropic native SDK provider
- **PATTERN**: Implement ModelProvider interface
- **IMPORTS**: `import anthropic`, `from .base import ModelProvider, Message, ModelResponse, ToolCall`
- **GOTCHA**: Anthropic uses different message format, extract system messages separately
- **VALIDATE**: `cd worker && uv run python -c "from models.anthropic_native import AnthropicProvider"`

```python
"""Anthropic native model provider."""
import anthropic
from .base import ModelProvider, Message, ModelResponse, ToolCall
from ..orchestrator.exceptions import ModelError

class AnthropicProvider(ModelProvider):
    """Anthropic native SDK provider."""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    async def chat_completion(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> ModelResponse:
        try:
            anthropic_messages = [{"role": msg.role, "content": msg.content} for msg in messages if msg.role != "system"]
            system = next((msg.content for msg in messages if msg.role == "system"), None)
            kwargs = {"model": self.model, "messages": anthropic_messages, "temperature": temperature, "max_tokens": max_tokens}
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
```

---

### Task 5: CREATE worker/tools/base.py

- **IMPLEMENT**: Base tool interface and result types
- **PATTERN**: Abstract base class with execute method
- **IMPORTS**: `from abc import ABC, abstractmethod`, `from dataclasses import dataclass`, `from typing import Any`
- **VALIDATE**: `cd worker && uv run python -c "from tools.base import Tool, ToolResult"`

```python
"""Base tool interface."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass
class ToolResult:
    """Tool execution result."""
    success: bool
    output: str
    error: str | None = None

class Tool(ABC):
    """Abstract tool interface."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name for LLM."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for LLM."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """JSON schema for tool parameters."""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute tool with parameters."""
        pass

    def to_openai_tool(self) -> dict:
        """Convert to OpenAI tool format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

    def to_anthropic_tool(self) -> dict:
        """Convert to Anthropic tool format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters
        }
```

---

### Task 6: CREATE worker/tools/file.py

- **IMPLEMENT**: File operations (list, read, write) as separate tool classes
- **PATTERN**: Implement Tool interface for each operation
- **IMPORTS**: `import os`, `from pathlib import Path`, `from .base import Tool, ToolResult`
- **GOTCHA**: All file operations are relative to sandbox working directory (/workspace)
- **VALIDATE**: `cd worker && uv run python -c "from tools.file import FileListTool, FileReadTool, FileWriteTool"`

```python
"""File operation tools."""
import os
from pathlib import Path
from .base import Tool, ToolResult

class FileListTool(Tool):
    """List files in directory."""

    def __init__(self, workspace_dir: str = "/workspace"):
        self.workspace_dir = workspace_dir

    @property
    def name(self) -> str:
        return "file_list"

    @property
    def description(self) -> str:
        return "List files and directories in a path. Returns list of file/directory names."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path to list (relative to workspace)"}
            },
            "required": ["path"]
        }

    async def execute(self, path: str = ".") -> ToolResult:
        try:
            full_path = Path(self.workspace_dir) / path
            if not full_path.exists():
                return ToolResult(success=False, output="", error=f"Path does not exist: {path}")
            if not full_path.is_dir():
                return ToolResult(success=False, output="", error=f"Path is not a directory: {path}")
            
            items = sorted(os.listdir(full_path))
            output = "\n".join(items) if items else "(empty directory)"
            return ToolResult(success=True, output=output)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

class FileReadTool(Tool):
    """Read file contents."""

    def __init__(self, workspace_dir: str = "/workspace"):
        self.workspace_dir = workspace_dir

    @property
    def name(self) -> str:
        return "file_read"

    @property
    def description(self) -> str:
        return "Read contents of a file. Returns file content as string."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read (relative to workspace)"}
            },
            "required": ["path"]
        }

    async def execute(self, path: str) -> ToolResult:
        try:
            full_path = Path(self.workspace_dir) / path
            if not full_path.exists():
                return ToolResult(success=False, output="", error=f"File does not exist: {path}")
            if not full_path.is_file():
                return ToolResult(success=False, output="", error=f"Path is not a file: {path}")
            
            content = full_path.read_text(encoding="utf-8")
            return ToolResult(success=True, output=content)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

class FileWriteTool(Tool):
    """Write content to file."""

    def __init__(self, workspace_dir: str = "/workspace"):
        self.workspace_dir = workspace_dir

    @property
    def name(self) -> str:
        return "file_write"

    @property
    def description(self) -> str:
        return "Write content to a file. Creates parent directories if needed."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to write (relative to workspace)"},
                "content": {"type": "string", "description": "Content to write to file"}
            },
            "required": ["path", "content"]
        }

    async def execute(self, path: str, content: str) -> ToolResult:
        try:
            full_path = Path(self.workspace_dir) / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            return ToolResult(success=True, output=f"Successfully wrote {len(content)} bytes to {path}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
```

---

### Task 7: CREATE worker/orchestrator/agent.py

- **IMPLEMENT**: Main agent execution loop with reasoning-action-observation cycle
- **PATTERN**: Async context manager for lifecycle, iterative loop with max iterations
- **IMPORTS**: `import uuid`, `import structlog`, `from ..models.base import ModelProvider, Message`, `from ..tools.base import Tool, ToolResult`
- **GOTCHA**: Must handle both tool_calls and final answer (stop) finish reasons
- **VALIDATE**: `cd worker && uv run python -c "from orchestrator.agent import Agent"`

```python
"""Agent orchestration loop."""
import uuid
import structlog
from ..models.base import ModelProvider, Message
from ..tools.base import Tool
from .exceptions import AgentExecutionError, MaxIterationsError, ToolExecutionError

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

        # Initialize with system and user messages
        if system_prompt:
            self.messages.append(Message(role="system", content=system_prompt))
        self.messages.append(Message(role="user", content=goal))

        # Convert tools to model format (assume OpenAI format for now)
        tool_schemas = [tool.to_openai_tool() for tool in self.tools.values()]

        while self.iteration < self.max_iterations:
            self.iteration += 1
            logger.info("agent_iteration", task_run_id=str(self.task_run_id), iteration=self.iteration)

            try:
                # Call model
                response = await self.model.chat_completion(
                    messages=self.messages,
                    tools=tool_schemas,
                    temperature=0.7
                )

                # Handle tool calls
                if response.tool_calls:
                    logger.info("tool_calls_requested", task_run_id=str(self.task_run_id), count=len(response.tool_calls))
                    
                    # Add assistant message with tool calls
                    self.messages.append(Message(
                        role="assistant",
                        content=response.content or "",
                        tool_calls=[{"id": tc.id, "name": tc.name, "arguments": tc.arguments} for tc in response.tool_calls]
                    ))

                    # Execute each tool call
                    for tool_call in response.tool_calls:
                        result = await self._execute_tool(tool_call.name, tool_call.arguments)
                        
                        # Add tool result as user message
                        self.messages.append(Message(
                            role="user",
                            content=f"Tool {tool_call.name} result: {result.output if result.success else f'ERROR: {result.error}'}",
                            tool_call_id=tool_call.id
                        ))

                # Handle completion
                elif response.finish_reason == "stop":
                    logger.info("agent_completed", task_run_id=str(self.task_run_id), iterations=self.iteration)
                    return response.content or ""

                else:
                    raise AgentExecutionError(f"Unexpected finish reason: {response.finish_reason}")

            except Exception as e:
                logger.error("agent_error", task_run_id=str(self.task_run_id), error=str(e))
                raise AgentExecutionError(f"Agent execution failed: {e}")

        raise MaxIterationsError(f"Agent exceeded maximum iterations: {self.max_iterations}")

    async def _execute_tool(self, tool_name: str, arguments: dict) -> ToolResult:
        """Execute a tool by name."""
        logger.info("executing_tool", task_run_id=str(self.task_run_id), tool=tool_name, args=arguments)

        if tool_name not in self.tools:
            return ToolResult(success=False, output="", error=f"Unknown tool: {tool_name}")

        try:
            tool = self.tools[tool_name]
            result = await tool.execute(**arguments)
            logger.info("tool_executed", task_run_id=str(self.task_run_id), tool=tool_name, success=result.success)
            return result
        except Exception as e:
            logger.error("tool_execution_failed", task_run_id=str(self.task_run_id), tool=tool_name, error=str(e))
            return ToolResult(success=False, output="", error=str(e))
```

---

### Task 8: CREATE worker/tests/test_models.py

- **IMPLEMENT**: Unit tests for model abstraction with mocked API calls
- **PATTERN**: Use pytest with AsyncMock for async methods
- **IMPORTS**: `import pytest`, `from unittest.mock import AsyncMock, Mock, patch`
- **VALIDATE**: `cd worker && uv run python -m pytest tests/test_models.py -v`

```python
"""Unit tests for model abstraction."""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from models.base import Message, ToolCall, ModelResponse
from models.openai_compat import OpenAIProvider
from models.anthropic_native import AnthropicProvider

@pytest.mark.asyncio
@patch('models.openai_compat.openai.AsyncOpenAI')
async def test_openai_chat_completion(mock_openai):
    """Test OpenAI chat completion."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Hello", tool_calls=None), finish_reason="stop")]
    mock_response.usage = Mock(prompt_tokens=10, completion_tokens=5, total_tokens=15)
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    mock_openai.return_value = mock_client

    provider = OpenAIProvider(api_key="test-key")
    messages = [Message(role="user", content="Hi")]
    response = await provider.chat_completion(messages)

    assert response.content == "Hello"
    assert response.finish_reason == "stop"
    assert response.usage["total_tokens"] == 15

@pytest.mark.asyncio
@patch('models.anthropic_native.anthropic.AsyncAnthropic')
async def test_anthropic_chat_completion(mock_anthropic):
    """Test Anthropic chat completion."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.content = [Mock(type="text", text="Hello")]
    mock_response.stop_reason = "end_turn"
    mock_response.usage = Mock(input_tokens=10, output_tokens=5)
    mock_client.messages.create = AsyncMock(return_value=mock_response)
    mock_anthropic.return_value = mock_client

    provider = AnthropicProvider(api_key="test-key")
    messages = [Message(role="user", content="Hi")]
    response = await provider.chat_completion(messages)

    assert response.content == "Hello"
    assert response.finish_reason == "end_turn"
```

---

### Task 9: CREATE worker/tests/test_tools.py

- **IMPLEMENT**: Unit tests for file tools with temporary directories
- **PATTERN**: Use pytest fixtures for temp workspace
- **IMPORTS**: `import pytest`, `from pathlib import Path`, `import tempfile`
- **VALIDATE**: `cd worker && uv run python -m pytest tests/test_tools.py -v`

```python
"""Unit tests for file tools."""
import pytest
from pathlib import Path
import tempfile
from tools.file import FileListTool, FileReadTool, FileWriteTool

@pytest.fixture
def temp_workspace():
    """Create temporary workspace directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

@pytest.mark.asyncio
async def test_file_list_tool(temp_workspace):
    """Test file list tool."""
    Path(temp_workspace, "file1.txt").touch()
    Path(temp_workspace, "file2.txt").touch()
    
    tool = FileListTool(workspace_dir=temp_workspace)
    result = await tool.execute(path=".")
    
    assert result.success
    assert "file1.txt" in result.output
    assert "file2.txt" in result.output

@pytest.mark.asyncio
async def test_file_read_tool(temp_workspace):
    """Test file read tool."""
    test_file = Path(temp_workspace, "test.txt")
    test_file.write_text("Hello World")
    
    tool = FileReadTool(workspace_dir=temp_workspace)
    result = await tool.execute(path="test.txt")
    
    assert result.success
    assert result.output == "Hello World"

@pytest.mark.asyncio
async def test_file_write_tool(temp_workspace):
    """Test file write tool."""
    tool = FileWriteTool(workspace_dir=temp_workspace)
    result = await tool.execute(path="output.txt", content="Test content")
    
    assert result.success
    assert Path(temp_workspace, "output.txt").read_text() == "Test content"

@pytest.mark.asyncio
async def test_file_read_nonexistent(temp_workspace):
    """Test reading nonexistent file."""
    tool = FileReadTool(workspace_dir=temp_workspace)
    result = await tool.execute(path="missing.txt")
    
    assert not result.success
    assert "does not exist" in result.error
```

---

### Task 10: CREATE worker/tests/test_agent.py

- **IMPLEMENT**: Integration tests for agent orchestrator
- **PATTERN**: Mock model and tools to test agent loop logic
- **IMPORTS**: `import pytest`, `import uuid`, `from unittest.mock import AsyncMock, Mock`
- **VALIDATE**: `cd worker && uv run python -m pytest tests/test_agent.py -v`

```python
"""Integration tests for agent orchestrator."""
import pytest
import uuid
from unittest.mock import AsyncMock, Mock
from orchestrator.agent import Agent
from models.base import ModelProvider, Message, ModelResponse, ToolCall
from tools.base import Tool, ToolResult

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
    
    # First call: request tool
    # Second call: complete after tool result
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
```

---

## TESTING STRATEGY

### Unit Tests

**Scope**: Test individual components in isolation with mocked dependencies

**Coverage Requirements**: 80%+ per project standards

**Test Files**:
- `test_models.py`: Model abstraction layer (OpenAI, Anthropic providers)
- `test_tools.py`: File tools (list, read, write) with temp directories
- `test_agent.py`: Agent orchestrator loop logic

**Fixtures**:
- `temp_workspace`: Temporary directory for file tool tests
- Mock model providers with AsyncMock
- Mock tool implementations for agent tests

### Integration Tests

**Scope**: Test agent loop with real tool execution (mocked model only)

**Key Scenarios**:
- Agent completes task without tools
- Agent executes single tool and completes
- Agent executes multiple tools in sequence
- Agent handles tool execution errors
- Agent respects max iterations limit

### Edge Cases

- Empty file operations (empty directory, empty file)
- Nonexistent file/directory access
- Tool execution failures
- Model API errors
- Max iterations exceeded
- Invalid tool names from model
- Malformed tool arguments

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
# Lint all worker code
cd worker && uv run ruff check .
```

**Expected**: "All checks passed!" or no output

### Level 2: Unit Tests

```bash
# Run all tests with verbose output
cd worker && uv run python -m pytest tests/ -v

# Run specific test files
cd worker && uv run python -m pytest tests/test_models.py -v
cd worker && uv run python -m pytest tests/test_tools.py -v
cd worker && uv run python -m pytest tests/test_agent.py -v
```

**Expected**: All tests pass

### Level 3: Import Validation

```bash
# Validate all modules can be imported
cd worker && uv run python -c "from orchestrator.exceptions import *"
cd worker && uv run python -c "from models.base import ModelProvider, Message, ToolCall"
cd worker && uv run python -c "from models.openai_compat import OpenAIProvider"
cd worker && uv run python -c "from models.anthropic_native import AnthropicProvider"
cd worker && uv run python -c "from tools.base import Tool, ToolResult"
cd worker && uv run python -c "from tools.file import FileListTool, FileReadTool, FileWriteTool"
cd worker && uv run python -c "from orchestrator.agent import Agent"
```

**Expected**: No import errors

### Level 4: Manual Validation

```bash
# Create simple test script to verify agent can run
cd worker && cat > test_agent_manual.py << 'SCRIPT'
import asyncio
import uuid
from models.base import ModelProvider, Message, ModelResponse
from tools.file import FileListTool
from orchestrator.agent import Agent

class DummyModel(ModelProvider):
    async def chat_completion(self, messages, tools=None, temperature=0.7, max_tokens=4096):
        return ModelResponse(content="Done", tool_calls=None, finish_reason="stop")

async def main():
    agent = Agent(
        task_run_id=uuid.uuid4(),
        model=DummyModel(),
        tools=[FileListTool()],
        max_iterations=5
    )
    result = await agent.run(goal="Test task")
    print(f"Result: {result}")

asyncio.run(main())
SCRIPT

uv run python test_agent_manual.py
rm test_agent_manual.py
```

**Expected**: Prints "Result: Done" without errors

---

## ACCEPTANCE CRITERIA

- [ ] Model abstraction layer supports both OpenAI and Anthropic providers
- [ ] Model providers correctly handle tool calling format for each API
- [ ] File tools (list, read, write) execute correctly in workspace directory
- [ ] Agent loop iterates through reasoning-action-observation cycle
- [ ] Agent correctly parses and executes tool calls from model
- [ ] Agent respects max iterations limit and raises appropriate error
- [ ] Agent completes when model returns stop finish reason
- [ ] All validation commands pass with zero errors
- [ ] Unit test coverage meets 80%+ requirement
- [ ] All imports work without errors
- [ ] Structured logging captures key events (agent start, iterations, tool calls)
- [ ] Exception hierarchy follows project patterns
- [ ] Code follows Python 3.11+ type hints conventions

---

## COMPLETION CHECKLIST

- [ ] All 10 tasks completed in order
- [ ] Each task validation passed immediately after implementation
- [ ] All validation commands executed successfully
- [ ] Linting passes (ruff check)
- [ ] All unit tests pass (pytest)
- [ ] All imports validated
- [ ] Manual agent test script runs successfully
- [ ] Acceptance criteria all met
- [ ] Code reviewed for quality and maintainability

---

## NOTES

### Design Decisions

**Model Abstraction Approach**: Unified interface with provider-specific implementations allows easy addition of new providers (local models, other APIs) without changing orchestrator code.

**Tool Format Conversion**: Each tool provides both OpenAI and Anthropic format converters. This keeps tool definitions provider-agnostic while supporting different API schemas.

**Message History Management**: Agent maintains full conversation history including tool calls and results. This enables the model to reason about previous actions and results.

**Workspace Directory Pattern**: File tools operate relative to a workspace directory (default `/workspace` for sandbox). This matches the sandbox container structure and provides isolation.

**Iteration Limit**: Max iterations prevents infinite loops. Default 20 iterations balances task complexity with resource constraints.

### Future Enhancements (Out of Scope for This Task)

- Additional tools (browser, python execution, web fetch)
- Streaming responses for real-time updates
- Tool result caching
- Parallel tool execution
- Agent memory/context management
- Integration with sandbox manager for actual container execution
- Database persistence of agent state
- WebSocket event streaming to frontend

### Integration Points

This orchestrator will integrate with:
- **Sandbox Manager** (`worker/sandbox/manager.py`): Execute agent within isolated container
- **Backend API**: Receive task goals, stream events, store results
- **RAG System** (future): Retrieve relevant context for tasks
- **Memory System** (future): Maintain conversation and project memory

### Testing Notes

- Model providers are tested with mocked API clients (no real API calls)
- File tools use temporary directories for isolation
- Agent tests mock both model and tools to test loop logic
- Integration tests verify tool execution but not model calls
- Manual validation script provides end-to-end smoke test

---

