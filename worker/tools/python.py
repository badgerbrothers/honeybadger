"""Python code execution tool."""
import base64
import time
import structlog
from .exceptions import ToolError
from .tool_base import Tool, ToolResult

logger = structlog.get_logger()


class PythonExecutionError(ToolError):
    """Python code execution failed."""
    pass


class PythonTimeoutError(PythonExecutionError):
    """Python execution timed out."""
    pass


class PythonTool(Tool):
    """Execute Python code in sandbox."""

    def __init__(self, sandbox_manager):
        """Initialize Python tool with sandbox manager."""
        self.sandbox = sandbox_manager
        self.logger = logger.bind(tool=self.__class__.__name__)

    @property
    def name(self) -> str:
        return "python_execute"

    @property
    def description(self) -> str:
        return "Execute Python code inside the task sandbox and return stdout, stderr, and exit status."

    @property
    def parameters(self) -> dict[str, object]:
        return {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute."},
                "timeout": {"type": "integer", "description": "Timeout in seconds.", "default": 30},
            },
            "required": ["code"],
        }

    async def execute(self, **kwargs) -> ToolResult:
        """Execute Python code.

        Args:
            kwargs: code and optional timeout.
        """
        self.logger.info("tool_execution_started", params=kwargs)
        code = kwargs.get("code")
        if not code:
            raise PythonExecutionError("Code is required")

        timeout = kwargs.get("timeout", 30)
        result = await self.run(code, timeout)
        self.logger.info("tool_execution_completed", result=result)

        if result["success"]:
            output = result["stdout"] or "Python execution completed successfully."
        else:
            output = result["stderr"] or "Python execution failed."

        return ToolResult(
            success=result["success"],
            output=output,
            error=None if result["success"] else output,
            metadata=result,
        )

    async def run(self, code: str, timeout: int = 30) -> dict[str, object]:
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
