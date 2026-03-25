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
        task_run_id: uuid.UUID | None = None,
        image: str = "badgers-sandbox:latest",
        mem_limit: str = "512m",
        cpu_quota: int = 50000,
        *,
        workspace_dir: str | None = None,
        container_id: str | None = None,
        backend: DockerBackend | None = None,
    ):
        """Initialize sandbox manager."""
        self.task_run_id = task_run_id
        self.image = image
        self.mem_limit = mem_limit
        self.cpu_quota = cpu_quota
        self.container_id = container_id
        self.backend = backend or DockerBackend()
        if workspace_dir is not None:
            self.workspace_dir = workspace_dir
            Path(self.workspace_dir).mkdir(parents=True, exist_ok=True)
        else:
            workspace_id = task_run_id or uuid.uuid4()
            self.workspace_dir = str(Path(tempfile.mkdtemp(prefix=f"badgers-{workspace_id}-")))

    @classmethod
    def from_session(
        cls,
        sandbox_session,
        *,
        backend: DockerBackend | None = None,
    ) -> "SandboxManager":
        """Rebuild a manager around an existing pooled sandbox row."""
        memory_limit = getattr(sandbox_session, "memory_limit", None)
        mem_limit = f"{memory_limit}m" if memory_limit else "512m"
        return cls(
            task_run_id=getattr(sandbox_session, "task_run_id", None),
            image=sandbox_session.image,
            mem_limit=mem_limit,
            cpu_quota=getattr(sandbox_session, "cpu_limit", 50000) or 50000,
            workspace_dir=sandbox_session.workspace_dir,
            container_id=sandbox_session.container_id,
            backend=backend,
        )

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

    async def restart(self) -> None:
        """Restart an existing sandbox container."""
        if not self.container_id:
            raise SandboxError("Sandbox not created")
        self.backend.restart_container(self.container_id)

    def reset_workspace(self) -> None:
        """Remove workspace contents while keeping the workspace root."""
        workspace = Path(self.workspace_dir)
        workspace.mkdir(parents=True, exist_ok=True)
        for child in workspace.iterdir():
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink(missing_ok=True)

    async def __aenter__(self):
        """Context manager entry."""
        await self.create()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        await self.destroy()
        return False
