"""Tool implementations."""
from .browser import BrowserTool
from .python import PythonTool
from .web import WebFetchTool
from .tool_base import Tool

__all__ = ["BrowserTool", "PythonTool", "WebFetchTool", "get_all_tools"]


def get_all_tools(sandbox_manager=None) -> list[Tool]:
    """Get all available tools.

    Args:
        sandbox_manager: Optional sandbox manager for PythonTool

    Returns:
        List of tool instances
    """
    tools = [
        BrowserTool(),
        WebFetchTool(),
    ]

    if sandbox_manager:
        tools.append(PythonTool(sandbox_manager))

    return tools
