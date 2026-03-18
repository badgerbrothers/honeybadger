"""HTTP client for the storage service."""
from __future__ import annotations

import httpx


class StorageClient:
    """Async client used by other services to call storage-service APIs."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient()

    async def upload_file(self, file_path: str, content: bytes) -> dict:
        response = await self.client.post(
            f"{self.base_url}/api/storage/upload",
            files={"file": (file_path, content)},
        )
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        await self.client.aclose()