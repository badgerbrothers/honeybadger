"""Python code execution tool."""
from typing import Any, Dict
import time
import base64
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
        if timeout <= 0 or timeout > 300:
            raise PythonExecutionError(f"Invalid timeout: {timeout}. Must be between 1 and 300 seconds")

        start_time = time.time()

        # Use base64 encoding for safe shell execution
        encoded_code = base64.b64encode(code.encode()).decode()
        command = f"timeout {timeout} python3 -c \"$(echo {encoded_code} | base64 -d)\""

        try:
            exit_code, output = await self.sandbox.execute(command)
            execution_time = time.time() - start_time

            return {
                "success": exit_code == 0,
                "stdout": output if exit_code == 0 else "",
                "stderr": output if exit_code != 0 else "",
                "exit_code": exit_code,
                "execution_time": execution_time
            }
        except Exception as e:
            raise PythonExecutionError(f"Failed to execute Python code: {e}") from e
