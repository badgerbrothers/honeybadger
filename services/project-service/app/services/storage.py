"""HTTP storage client service."""
from __future__ import annotations

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()


class StorageService:
    """Proxy storage operations to storage-service over HTTP."""

    def __init__(self) -> None:
        self.base_url = settings.storage_service_url.rstrip("/")

    async def upload_file(
        self,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/api/storage/upload",
                params={"object_name": object_name},
                files={"file": (object_name, data, content_type)},
            )
            response.raise_for_status()
            payload = response.json()
            return payload["object_name"]

    async def download_file(self, object_name: str) -> bytes:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.base_url}/api/storage/download/{object_name}"
            )
            response.raise_for_status()
            return response.content

    async def delete_file(self, object_name: str) -> None:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.delete(
                f"{self.base_url}/api/storage/object/{object_name}"
            )
            response.raise_for_status()

    async def copy_file(self, source_object: str, target_object: str) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/api/storage/copy",
                json={
                    "source_object": source_object,
                    "target_object": target_object,
                },
            )
            response.raise_for_status()
            payload = response.json()
            return payload["target_object"]


storage_service = StorageService()
