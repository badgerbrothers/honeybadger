"""Object storage helper for worker-side downloads."""
from __future__ import annotations

import asyncio
from pathlib import Path
from urllib.parse import urlparse

from config import settings


class StorageClient:
    """Thin MinIO/S3 client wrapper for worker use."""

    def __init__(self):
        self._client = None

    @property
    def client(self):
        """Lazily initialize the MinIO client so tests don't require the package until used."""
        if self._client is None:
            from minio import Minio

            endpoint, secure = self._resolve_endpoint(settings.s3_endpoint, settings.s3_secure)
            self._client = Minio(
                endpoint,
                access_key=settings.s3_access_key,
                secret_key=settings.s3_secret_key,
                secure=secure,
            )
        return self._client

    @staticmethod
    def _resolve_endpoint(raw_endpoint: str, default_secure: bool) -> tuple[str, bool]:
        """Normalize endpoint to MinIO-compatible host:port and secure flag."""
        endpoint = (raw_endpoint or "").strip()
        secure = default_secure
        if "://" in endpoint:
            parsed = urlparse(endpoint)
            endpoint = parsed.netloc or parsed.path
            if parsed.scheme in ("http", "https"):
                secure = parsed.scheme == "https"
        if "/" in endpoint:
            endpoint = endpoint.split("/", 1)[0]
        return endpoint, secure

    async def download_file(self, object_name: str) -> bytes:
        """Download an object from the configured bucket."""
        response = self.client.get_object(settings.s3_bucket, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def _blocking_download_to_path(
        self,
        object_name: str,
        destination_path: Path,
        *,
        chunk_size: int = 1024 * 1024,
    ) -> Path:
        """Download an object to a local path without buffering the whole file."""
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        response = self.client.get_object(settings.s3_bucket, object_name)
        try:
            with destination_path.open("wb") as handle:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    handle.write(chunk)
        finally:
            response.close()
            response.release_conn()
        return destination_path

    async def download_to_path(
        self,
        object_name: str,
        destination_path: str | Path,
        *,
        chunk_size: int = 1024 * 1024,
    ) -> Path:
        """Download an object directly to disk via a worker thread."""
        path = Path(destination_path)
        return await asyncio.to_thread(
            self._blocking_download_to_path,
            object_name,
            path,
            chunk_size=chunk_size,
        )


storage_client = StorageClient()
