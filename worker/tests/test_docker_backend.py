"""Unit tests for DockerBackend."""
import pytest
from unittest.mock import Mock, patch
from docker.errors import DockerException
from sandbox.docker_backend import DockerBackend
from sandbox.exceptions import SandboxCreationError


@patch('sandbox.docker_backend.docker.from_env')
def test_create_container_success(mock_from_env):
    """Test successful container creation."""
    mock_client = Mock()
    mock_container = Mock()
    mock_container.id = "test123"
    mock_client.containers.create.return_value = mock_container
    mock_from_env.return_value = mock_client

    backend = DockerBackend()
    container_id = backend.create_container("test-image")

    assert container_id == "test123"
    mock_client.containers.create.assert_called_once()


@patch('sandbox.docker_backend.docker.from_env')
def test_create_container_failure(mock_from_env):
    """Test container creation failure."""
    mock_client = Mock()
    mock_client.containers.create.side_effect = DockerException("Failed")
    mock_from_env.return_value = mock_client

    backend = DockerBackend()
    with pytest.raises(SandboxCreationError):
        backend.create_container("test-image")


@patch('sandbox.docker_backend.docker.from_env')
def test_start_container(mock_from_env):
    """Test container start."""
    mock_client = Mock()
    mock_container = Mock()
    mock_client.containers.get.return_value = mock_container
    mock_from_env.return_value = mock_client

    backend = DockerBackend()
    backend.start_container("test123")

    mock_container.start.assert_called_once()


@patch('sandbox.docker_backend.docker.from_env')
def test_stop_container(mock_from_env):
    """Test container stop."""
    mock_client = Mock()
    mock_container = Mock()
    mock_client.containers.get.return_value = mock_container
    mock_from_env.return_value = mock_client

    backend = DockerBackend()
    backend.stop_container("test123")

    mock_container.stop.assert_called_once_with(timeout=10)


@patch('sandbox.docker_backend.docker.from_env')
def test_remove_container(mock_from_env):
    """Test container removal."""
    mock_client = Mock()
    mock_container = Mock()
    mock_client.containers.get.return_value = mock_container
    mock_from_env.return_value = mock_client

    backend = DockerBackend()
    backend.remove_container("test123", force=True)

    mock_container.remove.assert_called_once_with(force=True)


@patch('sandbox.docker_backend.docker.from_env')
def test_execute_command(mock_from_env):
    """Test command execution."""
    mock_client = Mock()
    mock_container = Mock()
    mock_container.exec_run.return_value = (0, b"output")
    mock_client.containers.get.return_value = mock_container
    mock_from_env.return_value = mock_client

    backend = DockerBackend()
    exit_code, output = backend.execute_command("test123", "echo test")

    assert exit_code == 0
    assert output == "output"
