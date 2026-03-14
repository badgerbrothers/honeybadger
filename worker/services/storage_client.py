"""Object storage helper for worker-side downloads."""
from __future__ import annotations

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


storage_client = StorageClient()
