"""Docker SDK wrapper for container operations."""
from pathlib import Path
import docker
from docker.errors import DockerException, NotFound
from .exceptions import SandboxCreationError, SandboxExecutionError, SandboxCleanupError


class DockerBackend:
    """Low-level Docker SDK wrapper for container lifecycle management."""

    def __init__(self):
        """Initialize Docker client."""
        try:
            self.client = docker.from_env()
        except DockerException as e:
            raise SandboxCreationError(f"Failed to initialize Docker client: {e}")

    def create_container(
        self,
        image: str,
        mem_limit: str = "512m",
        cpu_quota: int = 50000,
        workspace_dir: str | None = None,
    ) -> str:
        """Create container with resource limits."""
        try:
            volumes = None
            if workspace_dir:
                Path(workspace_dir).mkdir(parents=True, exist_ok=True)
                volumes = {
                    str(Path(workspace_dir)): {"bind": "/workspace", "mode": "rw"},
                }
            container = self.client.containers.create(
                image=image,
                detach=True,
                mem_limit=mem_limit,
                cpu_quota=cpu_quota,
                network_mode="bridge",
                volumes=volumes,
                working_dir="/workspace",
            )
            return container.id
        except DockerException as e:
            raise SandboxCreationError(f"Failed to create container: {e}")

    def start_container(self, container_id: str):
        """Start container."""
        try:
            container = self.client.containers.get(container_id)
            container.start()
        except DockerException as e:
            raise SandboxCreationError(f"Failed to start container: {e}")

    def stop_container(self, container_id: str, timeout: int = 10):
        """Stop container gracefully."""
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=timeout)
        except NotFound:
            pass
        except DockerException as e:
            raise SandboxCleanupError(f"Failed to stop container: {e}")

    def remove_container(self, container_id: str, force: bool = False):
        """Remove container."""
        try:
            container = self.client.containers.get(container_id)
            container.remove(force=force)
        except NotFound:
            pass
        except DockerException as e:
            raise SandboxCleanupError(f"Failed to remove container: {e}")

    def execute_command(self, container_id: str, command: str) -> tuple[int, str]:
        """Execute command in container and return exit code and output."""
        try:
            container = self.client.containers.get(container_id)
            exit_code, output = container.exec_run(command)
            return exit_code, output.decode('utf-8')
        except DockerException as e:
            raise SandboxExecutionError(f"Failed to execute command: {e}")

    def get_container_logs(self, container_id: str) -> str:
        """Get container logs."""
        try:
            container = self.client.containers.get(container_id)
            return container.logs().decode('utf-8')
        except DockerException as e:
            raise SandboxExecutionError(f"Failed to get logs: {e}")
