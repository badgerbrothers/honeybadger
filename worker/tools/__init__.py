"""Tool implementations."""
from .browser import BrowserTool
from .file import FileListTool, FileReadTool, FileWriteTool
from .python import PythonTool
from .tool_base import Tool
from .web import WebFetchTool

__all__ = [
    "BrowserTool",
    "FileListTool",
    "FileReadTool",
    "FileWriteTool",
    "PythonTool",
    "WebFetchTool",
    "get_all_tools",
]


def get_all_tools(sandbox_manager=None) -> list[Tool]:
    """Get all available tools.

    Args:
        sandbox_manager: Optional sandbox manager for PythonTool

    Returns:
        List of tool instances
    """
    workspace_dir = getattr(sandbox_manager, "workspace_dir", "/workspace")
    tools = [
        BrowserTool(workspace_dir=workspace_dir),
        WebFetchTool(),
        FileListTool(workspace_dir=workspace_dir),
        FileReadTool(workspace_dir=workspace_dir),
        FileWriteTool(workspace_dir=workspace_dir),
    ]

    if sandbox_manager:
        tools.append(PythonTool(sandbox_manager))

    return tools
