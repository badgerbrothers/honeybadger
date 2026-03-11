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
