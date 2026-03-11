"""Base tool class with common patterns."""
from abc import ABC, abstractmethod
from typing import Any, Dict
import structlog

logger = structlog.get_logger()


class BaseTool(ABC):
    """Base class for all tool implementations."""

    def __init__(self):
        """Initialize base tool."""
        self.logger = logger.bind(tool=self.__class__.__name__)

    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool with given parameters.

        Args:
            params: Tool-specific parameters

        Returns:
            Tool execution result
        """
        pass

    def _log_execution(self, params: Dict[str, Any]):
        """Log tool execution."""
        self.logger.info("tool_execution_started", params=params)

    def _log_result(self, result: Dict[str, Any]):
        """Log tool result."""
        self.logger.info("tool_execution_completed", result=result)

    def _log_error(self, error: Exception):
        """Log tool error."""
        self.logger.error("tool_execution_failed", error=str(error), error_type=type(error).__name__)
