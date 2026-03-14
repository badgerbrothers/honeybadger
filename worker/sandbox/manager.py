"""High-level sandbox lifecycle manager."""
import shutil
import tempfile
import uuid
from pathlib import Path
from .docker_backend import DockerBackend
from .exceptions import SandboxError


class SandboxManager:
    """High-level sandbox lifecycle orchestration."""

    def __init__(
        self,
        task_run_id: uuid.UUID,
        image: str = "badgers-sandbox:latest",
        mem_limit: str = "512m",
        cpu_quota: int = 50000
    ):
        """Initialize sandbox manager."""
        self.task_run_id = task_run_id
        self.image = image
        self.mem_limit = mem_limit
        self.cpu_quota = cpu_quota
        self.container_id: str | None = None
        self.backend = DockerBackend()
        self.workspace_dir = str(Path(tempfile.mkdtemp(prefix=f"badgers-{task_run_id}-")))

    async def create(self):
        """Create sandbox container."""
        self.container_id = self.backend.create_container(
            image=self.image,
            mem_limit=self.mem_limit,
            cpu_quota=self.cpu_quota,
            workspace_dir=self.workspace_dir,
        )
        self.backend.start_container(self.container_id)
        return self.container_id

    async def destroy(self):
        """Stop and remove sandbox container."""
        try:
            if self.container_id:
                self.backend.stop_container(self.container_id)
                self.backend.remove_container(self.container_id, force=True)
        finally:
            shutil.rmtree(self.workspace_dir, ignore_errors=True)

    async def execute(self, command: str) -> tuple[int, str]:
        """Execute command in sandbox."""
        if not self.container_id:
            raise SandboxError("Sandbox not created")
        return self.backend.execute_command(self.container_id, command)

    async def __aenter__(self):
        """Context manager entry."""
        await self.create()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        await self.destroy()
        return False
