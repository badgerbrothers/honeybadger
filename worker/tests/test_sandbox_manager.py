"""Unit tests for SandboxManager."""
from pathlib import Path
import pytest
import uuid
from unittest.mock import Mock, patch
from sandbox.manager import SandboxManager


@pytest.mark.asyncio
@patch('sandbox.manager.DockerBackend')
async def test_create_sandbox(mock_backend_class):
    """Test sandbox creation."""
    mock_backend = Mock()
    mock_backend.create_container.return_value = "container123"
    mock_backend_class.return_value = mock_backend

    manager = SandboxManager(task_run_id=uuid.uuid4())
    container_id = await manager.create()

    assert container_id == "container123"
    mock_backend.create_container.assert_called_once()
    mock_backend.start_container.assert_called_once_with("container123")


@pytest.mark.asyncio
@patch('sandbox.manager.DockerBackend')
async def test_destroy_sandbox(mock_backend_class):
    """Test sandbox cleanup."""
    mock_backend = Mock()
    mock_backend_class.return_value = mock_backend

    manager = SandboxManager(task_run_id=uuid.uuid4())
    manager.container_id = "container123"
    await manager.destroy()

    mock_backend.stop_container.assert_called_once_with("container123")
    mock_backend.remove_container.assert_called_once_with("container123", force=True)


@pytest.mark.asyncio
@patch('sandbox.manager.DockerBackend')
async def test_execute_command(mock_backend_class):
    """Test command execution."""
    mock_backend = Mock()
    mock_backend.execute_command.return_value = (0, "output")
    mock_backend_class.return_value = mock_backend

    manager = SandboxManager(task_run_id=uuid.uuid4())
    manager.container_id = "container123"
    exit_code, output = await manager.execute("echo test")

    assert exit_code == 0
    assert output == "output"


@pytest.mark.asyncio
@patch('sandbox.manager.DockerBackend')
async def test_context_manager(mock_backend_class):
    """Test context manager automatic cleanup."""
    mock_backend = Mock()
    mock_backend.create_container.return_value = "container123"
    mock_backend_class.return_value = mock_backend

    async with SandboxManager(task_run_id=uuid.uuid4()) as manager:
        assert manager.container_id == "container123"

    mock_backend.stop_container.assert_called_once()
    mock_backend.remove_container.assert_called_once()


@pytest.mark.asyncio
@patch('sandbox.manager.DockerBackend')
async def test_cleanup_on_exception(mock_backend_class):
    """Test cleanup happens on exception."""
    mock_backend = Mock()
    mock_backend.create_container.return_value = "container123"
    mock_backend_class.return_value = mock_backend

    with pytest.raises(ValueError):
        async with SandboxManager(task_run_id=uuid.uuid4()):
            raise ValueError("Test error")

    mock_backend.stop_container.assert_called_once()
    mock_backend.remove_container.assert_called_once()


@patch('sandbox.manager.DockerBackend')
def test_from_session_reuses_existing_container(mock_backend_class):
    """Manager should rebuild from pooled session metadata."""
    mock_backend = Mock()
    mock_backend_class.return_value = mock_backend
    sandbox_session = Mock()
    sandbox_session.task_run_id = uuid.uuid4()
    sandbox_session.image = "badgers-sandbox:latest"
    sandbox_session.memory_limit = 512
    sandbox_session.cpu_limit = 50000
    sandbox_session.workspace_dir = "C:/tmp/badgers"
    sandbox_session.container_id = "container123"

    manager = SandboxManager.from_session(sandbox_session)

    assert manager.container_id == "container123"
    assert manager.workspace_dir == "C:/tmp/badgers"
    assert manager.mem_limit == "512m"


@pytest.mark.asyncio
@patch('sandbox.manager.DockerBackend')
async def test_restart_sandbox(mock_backend_class):
    """Test sandbox restart delegates to Docker backend."""
    mock_backend = Mock()
    mock_backend_class.return_value = mock_backend

    manager = SandboxManager(task_run_id=uuid.uuid4())
    manager.container_id = "container123"
    await manager.restart()

    mock_backend.restart_container.assert_called_once_with("container123")


@patch('sandbox.manager.DockerBackend')
def test_reset_workspace_clears_contents(mock_backend_class, tmp_path):
    """Workspace reset should delete children but preserve root directory."""
    mock_backend = Mock()
    mock_backend_class.return_value = mock_backend

    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "file.txt").write_text("content", encoding="utf-8")
    (tmp_path / "root.txt").write_text("content", encoding="utf-8")

    manager = SandboxManager(task_run_id=uuid.uuid4(), workspace_dir=str(tmp_path))
    manager.reset_workspace()

    assert Path(tmp_path).exists()
    assert list(Path(tmp_path).iterdir()) == []
