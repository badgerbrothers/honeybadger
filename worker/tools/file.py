"""File operation tools."""
import os
from pathlib import Path
from tools.tool_base import Tool, ToolResult


def _resolve_path(workspace_dir: str, path: str) -> Path:
    """Resolve a workspace-relative path and prevent escaping the workspace root."""
    workspace = Path(workspace_dir).resolve()
    candidate = (workspace / path).resolve()
    if candidate != workspace and workspace not in candidate.parents:
        raise ValueError(f"Path escapes workspace: {path}")
    return candidate


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
            full_path = _resolve_path(self.workspace_dir, path)
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
            full_path = _resolve_path(self.workspace_dir, path)
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
            full_path = _resolve_path(self.workspace_dir, path)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            return ToolResult(
                success=True,
                output=f"Successfully wrote {len(content)} bytes to {path}",
                metadata={
                    "path": str(full_path),
                    "artifact": {
                        "path": str(full_path),
                        "name": full_path.name,
                        "artifact_type": "file",
                        "mime_type": "text/plain",
                        "size": len(content.encode("utf-8")),
                    },
                },
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
