"""HTTP client for reporting worker-side execution events to the backend."""
from __future__ import annotations

import mimetypes
from pathlib import Path

import httpx


class BackendClient:
    """Small HTTP client for backend coordination."""

    def __init__(self, base_url: str, internal_service_token: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.internal_service_token = internal_service_token or ""

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.internal_service_token:
            headers["X-Internal-Service-Token"] = self.internal_service_token
        return headers

    async def emit_run_event(self, run_id: str, event: dict) -> None:
        """Send a run event to the backend fan-out endpoint."""
        async with httpx.AsyncClient(base_url=self.base_url, timeout=10) as client:
            response = await client.post(
                f"/api/runs/{run_id}/events",
                json=event,
                headers=self._headers(),
            )
            response.raise_for_status()

    async def upload_artifact(
        self,
        project_id: str,
        task_run_id: str,
        file_path: str,
        artifact_type: str = "file",
    ) -> dict:
        """Upload a generated file as an artifact via the backend API."""
        path = Path(file_path)
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        async with httpx.AsyncClient(base_url=self.base_url, timeout=30) as client:
            with path.open("rb") as handle:
                response = await client.post(
                    "/api/artifacts/upload",
                    params={
                        "project_id": project_id,
                        "task_run_id": task_run_id,
                        "artifact_type": artifact_type,
                    },
                    files={"file": (path.name, handle, mime_type)},
                    headers=self._headers(),
                )
            response.raise_for_status()
            return response.json()
