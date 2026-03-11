# Feature: Python Execution Tool

## Feature Description

Implement a Python code execution tool that runs Python code inside the Docker sandbox, captures stdout/stderr output, and returns execution results with timeout protection. This enables the AI agent to perform data processing, analysis, and computation tasks.

## User Story

As an AI agent
I want to execute Python code in an isolated sandbox environment
So that I can perform data analysis, computations, and scripting tasks safely

## Problem Statement

The agent needs to perform computational tasks like data processing, mathematical calculations, and script execution. Without a Python execution tool, the agent cannot leverage Python's rich ecosystem of libraries for tasks like data analysis with pandas, numerical computing with numpy, or web scraping with beautifulsoup4.

## Solution Statement

Implement a PythonTool class that integrates with the existing SandboxManager to execute Python code in isolated Docker containers. The tool will capture stdout/stderr, enforce timeout limits, handle execution errors gracefully, and return structured results including output and execution time.

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Low-Medium
**Primary Systems Affected**: worker/tools
**Dependencies**: SandboxManager (already implemented), Docker sandbox with Python

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `worker/tools/base.py` (lines 1-39) - Why: Base tool class pattern to inherit from
- `worker/tools/browser.py` (lines 1-50) - Why: Reference implementation showing tool structure
- `worker/sandbox/manager.py` (lines 1-56) - Why: SandboxManager.execute() method for running commands
- `worker/sandbox/exceptions.py` (lines 1-22) - Why: Exception hierarchy pattern
- `worker/tools/exceptions.py` (lines 1-27) - Why: Existing tool exceptions
- `worker/tests/test_browser_tools.py` (lines 1-30) - Why: Test pattern with pytest-asyncio
- `.claude/PRD.md` (lines 495-503) - Why: python.run tool specifications

### New Files to Create

- `worker/tools/python.py` - Python execution tool implementation
- `worker/tests/test_python_tool.py` - Unit tests for Python tool

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [Python subprocess module](https://docs.python.org/3/library/subprocess.html)
  - Specific section: Capturing output
  - Why: Understanding stdout/stderr capture patterns
- [Docker exec command](https://docs.docker.com/engine/reference/commandline/exec/)
  - Specific section: Command execution in containers
  - Why: Understanding how commands execute in Docker containers

### Patterns to Follow

**Naming Conventions:**
```python
# From tools/base.py
class BaseTool(ABC):  # PascalCase for classes
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:  # snake_case for methods
        pass
```

**Error Handling:**
```python
# From tools/exceptions.py
class PythonExecutionError(ToolError):
    """Python code execution failed."""
    pass
```

**Async Execution Pattern:**
```python
# From sandbox/manager.py lines 41-45
async def execute(self, command: str) -> tuple[int, str]:
    """Execute command in sandbox."""
    if not self.container_id:
        raise SandboxError("Sandbox not created")
    return self.backend.execute_command(self.container_id, command)
```

**Tool Structure:**
```python
# From tools/browser.py
class BrowserTool(BaseTool):
    def __init__(self):
        super().__init__()
        # Initialize tool-specific attributes

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        self._log_execution(params)
        # Execute operation
        result = await self.operation(params)
        self._log_result(result)
        return result
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation

Create PythonTool class inheriting from BaseTool with proper exception handling and logging.

**Tasks:**
- Define PythonExecutionError exception
- Create PythonTool class structure
- Implement initialization with SandboxManager integration

### Phase 2: Core Implementation

Implement Python code execution with stdout/stderr capture and timeout protection.

**Tasks:**
- Implement execute() method with parameter validation
- Implement run() method for Python code execution
- Add timeout protection (30s default)
- Capture and parse stdout/stderr output

### Phase 3: Testing

Create comprehensive unit tests with mocked SandboxManager.

**Tasks:**
- Write unit tests for successful execution
- Test timeout scenarios
- Test error handling (syntax errors, runtime errors)
- Test stdout/stderr capture

---

## STEP-BY-STEP TASKS

### CREATE worker/tools/python.py

- **IMPLEMENT**: Python execution tool with SandboxManager integration
- **PATTERN**: Mirror `worker/tools/browser.py` structure
- **IMPORTS**: `from typing import Any, Dict`, `import time`, `from .base import BaseTool`, `from .exceptions import ToolError`
- **GOTCHA**: Must handle both syntax errors and runtime errors
- **VALIDATE**: `cd worker && uv run python -c "from tools.python import PythonTool; print('OK')"`

```python
"""Python code execution tool."""
from typing import Any, Dict
import time
import structlog
from .base import BaseTool
from .exceptions import ToolError

logger = structlog.get_logger()


class PythonExecutionError(ToolError):
    """Python code execution failed."""
    pass


class PythonTimeoutError(PythonExecutionError):
    """Python execution timed out."""
    pass


class PythonTool(BaseTool):
    """Execute Python code in sandbox."""

    def __init__(self, sandbox_manager):
        """Initialize Python tool with sandbox manager."""
        super().__init__()
        self.sandbox = sandbox_manager

    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Python code.

        Args:
            params: {
                "code": str - Python code to execute,
                "timeout": int (optional) - Timeout in seconds (default: 30)
            }

        Returns:
            {
                "success": bool,
                "stdout": str,
                "stderr": str,
                "exit_code": int,
                "execution_time": float
            }
        """
        self._log_execution(params)
        code = params.get("code")
        if not code:
            raise PythonExecutionError("Code is required")

        timeout = params.get("timeout", 30)
        result = await self.run(code, timeout)
        self._log_result(result)
        return result

    async def run(self, code: str, timeout: int = 30) -> Dict[str, Any]:
        """Run Python code in sandbox."""
        start_time = time.time()

        # Escape code for shell execution
        escaped_code = code.replace("'", "'\\''")
        command = f"timeout {timeout} python3 -c '{escaped_code}'"

        try:
            exit_code, output = await self.sandbox.execute(command)
            execution_time = time.time() - start_time

            # Parse output (stdout and stderr are combined in Docker exec)
            return {
                "success": exit_code == 0,
                "stdout": output if exit_code == 0 else "",
                "stderr": output if exit_code != 0 else "",
                "exit_code": exit_code,
                "execution_time": execution_time
            }
        except Exception as e:
            raise PythonExecutionError(f"Failed to execute Python code: {e}") from e
```

### UPDATE worker/tools/exceptions.py

- **IMPLEMENT**: Add Python-specific exceptions
- **PATTERN**: Follow existing exception hierarchy
- **VALIDATE**: `cd worker && uv run python -c "from tools.exceptions import PythonExecutionError"`

```python
class PythonExecutionError(ToolError):
    """Python code execution failed."""
    pass


class PythonTimeoutError(PythonExecutionError):
    """Python execution timed out."""
    pass
```

### UPDATE worker/tools/__init__.py

- **IMPLEMENT**: Export PythonTool
- **PATTERN**: Add to existing exports
- **VALIDATE**: `cd worker && uv run python -c "from tools import PythonTool"`

```python
"""Tool implementations."""
from .browser import BrowserTool
from .python import PythonTool

__all__ = ["BrowserTool", "PythonTool"]
```

### CREATE worker/tests/test_python_tool.py

- **IMPLEMENT**: Unit tests with mocked SandboxManager
- **PATTERN**: Mirror `test_browser_tools.py` structure
- **IMPORTS**: `pytest`, `AsyncMock`, `Mock`, `patch`
- **VALIDATE**: `cd worker && uv run pytest tests/test_python_tool.py -v`

```python
"""Unit tests for Python execution tool."""
import pytest
from unittest.mock import AsyncMock, Mock
from tools.python import PythonTool, PythonExecutionError


@pytest.mark.asyncio
async def test_python_execute_success():
    """Test successful Python code execution."""
    mock_sandbox = AsyncMock()
    mock_sandbox.execute.return_value = (0, "Hello, World!")

    tool = PythonTool(mock_sandbox)
    result = await tool.execute({"code": "print('Hello, World!')"})

    assert result["success"] is True
    assert result["stdout"] == "Hello, World!"
    assert result["exit_code"] == 0
    assert result["execution_time"] > 0


@pytest.mark.asyncio
async def test_python_execute_error():
    """Test Python code with syntax error."""
    mock_sandbox = AsyncMock()
    mock_sandbox.execute.return_value = (1, "SyntaxError: invalid syntax")

    tool = PythonTool(mock_sandbox)
    result = await tool.execute({"code": "print('missing quote)"})

    assert result["success"] is False
    assert "SyntaxError" in result["stderr"]
    assert result["exit_code"] == 1


@pytest.mark.asyncio
async def test_python_missing_code():
    """Test execution without code parameter."""
    mock_sandbox = AsyncMock()
    tool = PythonTool(mock_sandbox)

    with pytest.raises(PythonExecutionError, match="Code is required"):
        await tool.execute({})
```

---

## TESTING STRATEGY

### Unit Tests

**Scope**: Test Python tool in isolation with mocked SandboxManager

**Requirements**:
- Mock SandboxManager.execute() to avoid actual container execution
- Test success path with valid Python code
- Test error scenarios (syntax errors, runtime errors, missing parameters)
- Verify timeout parameter is passed correctly
- Use pytest-asyncio for async test support

### Integration Tests

**Scope**: Test with actual SandboxManager (optional, requires Docker)

**Requirements**:
- Test with real sandbox container
- Verify stdout/stderr capture works correctly
- Test timeout enforcement
- Test with common libraries (pandas, numpy)

### Edge Cases

- Empty code string
- Very long-running code (timeout test)
- Code with syntax errors
- Code with runtime errors (division by zero, import errors)
- Code that produces large output
- Code with special characters and quotes

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style

```bash
cd worker && uv run ruff check tools/python.py
```

### Level 2: Unit Tests

```bash
cd worker && uv run pytest tests/test_python_tool.py -v
```

### Level 3: All Tests

```bash
cd worker && uv run pytest tests/ -v
```

### Level 4: Manual Validation

```python
# Test script
import asyncio
from tools.python import PythonTool
from sandbox.manager import SandboxManager
import uuid

async def test():
    sandbox = SandboxManager(task_run_id=uuid.uuid4())
    async with sandbox:
        tool = PythonTool(sandbox)

        # Test simple print
        result = await tool.execute({"code": "print('Hello')"})
        print(f"Simple: {result}")

        # Test with pandas
        result = await tool.execute({"code": "import pandas as pd; print(pd.__version__)"})
        print(f"Pandas: {result}")

asyncio.run(test())
```

---

## ACCEPTANCE CRITERIA

- [ ] PythonTool class implements execute() method
- [ ] Code execution works in sandbox environment
- [ ] Stdout and stderr are captured correctly
- [ ] Timeout protection works (30s default)
- [ ] Exit code is returned
- [ ] Execution time is measured
- [ ] Unit tests pass (3+ tests)
- [ ] Code follows project conventions
- [ ] Proper error handling for missing/invalid parameters
- [ ] Logging uses structlog

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed
- [ ] All validation commands executed successfully
- [ ] Unit tests pass
- [ ] No linting errors
- [ ] Manual testing confirms tool works
- [ ] Acceptance criteria all met

---

## NOTES

**Design Decisions:**

1. **SandboxManager Integration**: PythonTool receives SandboxManager instance in constructor rather than creating its own, allowing flexibility in sandbox configuration
2. **Combined Output**: Docker exec combines stdout/stderr, so we parse based on exit code (0=stdout, non-0=stderr)
3. **Timeout via Linux timeout command**: Using `timeout` command for simplicity rather than Python's subprocess timeout
4. **Code Escaping**: Single quotes in code are escaped for safe shell execution

**Security Considerations:**

- Code runs in isolated Docker container
- Timeout prevents infinite loops
- No direct filesystem access outside /workspace/
- Resource limits enforced by Docker (CPU, memory)

**Limitations:**

- Stdout/stderr are combined (Docker exec limitation)
- No interactive input support
- No real-time output streaming (all output returned at end)
- Limited to pre-installed libraries in Docker image

