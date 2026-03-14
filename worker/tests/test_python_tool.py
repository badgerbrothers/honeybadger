"""Unit tests for Python execution tool."""
import pytest
from unittest.mock import AsyncMock
from tools.python import PythonTool, PythonExecutionError


@pytest.mark.asyncio
async def test_python_execute_success():
    """Test successful Python code execution."""
    mock_sandbox = AsyncMock()
    mock_sandbox.execute.return_value = (0, "Hello, World!")

    tool = PythonTool(mock_sandbox)
    result = await tool.execute(code="print('Hello, World!')")

    assert result.success is True
    assert "Hello, World!" in result.output
    assert result.metadata["stdout"] == "Hello, World!"
    assert result.metadata["exit_code"] == 0
    assert result.metadata["execution_time"] >= 0


@pytest.mark.asyncio
async def test_python_execute_error():
    """Test Python code with syntax error."""
    mock_sandbox = AsyncMock()
    mock_sandbox.execute.return_value = (1, "SyntaxError: invalid syntax")

    tool = PythonTool(mock_sandbox)
    result = await tool.execute(code="print('missing quote)")

    assert result.success is False
    assert "SyntaxError" in result.error
    assert "SyntaxError" in result.metadata["stderr"]
    assert result.metadata["exit_code"] == 1


@pytest.mark.asyncio
async def test_python_missing_code():
    """Test execution without code parameter."""
    mock_sandbox = AsyncMock()
    tool = PythonTool(mock_sandbox)

    with pytest.raises(PythonExecutionError, match="Code is required"):
        await tool.execute()
