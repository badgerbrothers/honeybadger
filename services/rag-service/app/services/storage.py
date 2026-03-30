"""MinIO storage service."""
from __future__ import annotations

import asyncio
import io
from datetime import timedelta
from typing import BinaryIO
from urllib.parse import urlparse

from minio import Minio
from minio.commonconfig import CopySource
from minio.datatypes import Part
from minio.error import S3Error
import structlog
from app.config import settings

logger = structlog.get_logger()


class StorageService:
    """MinIO storage service for artifacts."""

    def __init__(self):
        endpoint, secure = self._resolve_endpoint(settings.s3_endpoint, settings.s3_secure)
        public_endpoint, public_secure = self._resolve_endpoint(
            settings.s3_public_endpoint,
            settings.s3_public_secure,
        )
        self.client = Minio(
            endpoint,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            secure=secure
        )
        self.public_client = Minio(
            public_endpoint,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            secure=public_secure,
        )
        self.client._region_map[settings.s3_bucket] = "us-east-1"
        self.public_client._region_map[settings.s3_bucket] = "us-east-1"
        self._bucket_checked = False

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

    def _ensure_bucket(self):
        """Ensure bucket exists."""
        if self._bucket_checked:
            return
        try:
            if not self.client.bucket_exists(settings.s3_bucket):
                self.client.make_bucket(settings.s3_bucket)
            self._bucket_checked = True
        except Exception as e:
            logger.warning("bucket_check_failed", error=str(e))

    def _blocking_put_object(
        self,
        object_name: str,
        stream: BinaryIO,
        length: int,
        content_type: str,
    ) -> str:
        """Upload a stream to MinIO using the blocking SDK."""
        self._ensure_bucket()
        part_size = (
            settings.s3_multipart_part_size
            if length > settings.s3_multipart_part_size
            else 0
        )
        try:
            if hasattr(stream, "seek"):
                stream.seek(0)
            self.client.put_object(
                settings.s3_bucket,
                object_name,
                stream,
                length=length,
                content_type=content_type,
                part_size=part_size,
                num_parallel_uploads=settings.s3_num_parallel_uploads,
            )
            return object_name
        except S3Error as e:
            logger.error("upload_failed", object_name=object_name, error=str(e))
            raise

    async def upload_stream(
        self,
        object_name: str,
        stream: BinaryIO,
        length: int,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload a file-like stream to MinIO without buffering the full payload in memory."""
        return await asyncio.to_thread(
            self._blocking_put_object,
            object_name,
            stream,
            length,
            content_type,
        )

    async def upload_file(self, object_name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Upload bytes to MinIO."""
        return await self.upload_stream(
            object_name=object_name,
            stream=io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

    async def download_file(self, object_name: str) -> bytes:
        """Download file from MinIO."""
        self._ensure_bucket()
        response = None
        try:
            response = self.client.get_object(settings.s3_bucket, object_name)
            return response.read()
        except S3Error as e:
            logger.error("download_failed", object_name=object_name, error=str(e))
            raise
        finally:
            if response is not None:
                response.close()
                response.release_conn()

    async def download_file_range(self, object_name: str, offset: int = 0, length: int = 0) -> bytes:
        """Download a byte range from MinIO."""
        self._ensure_bucket()
        response = None
        try:
            response = self.client.get_object(
                settings.s3_bucket,
                object_name,
                offset=offset,
                length=length,
            )
            return response.read()
        except S3Error as e:
            logger.error("download_range_failed", object_name=object_name, error=str(e))
            raise
        finally:
            if response is not None:
                response.close()
                response.release_conn()

    async def delete_file(self, object_name: str):
        """Delete file from MinIO."""
        self._ensure_bucket()
        try:
            self.client.remove_object(settings.s3_bucket, object_name)
        except S3Error as e:
            logger.error("delete_failed", object_name=object_name, error=str(e))
            raise

    async def copy_file(self, source_object: str, target_object: str) -> str:
        """Copy an object within the configured bucket."""
        self._ensure_bucket()
        try:
            self.client.copy_object(
                settings.s3_bucket,
                target_object,
                CopySource(settings.s3_bucket, source_object),
            )
            return target_object
        except S3Error as e:
            logger.error(
                "copy_failed",
                source_object=source_object,
                target_object=target_object,
                error=str(e),
            )
            raise

    async def create_multipart_upload(
        self,
        object_name: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Create an S3/MinIO multipart upload session."""
        self._ensure_bucket()
        headers = {"Content-Type": content_type}
        return await asyncio.to_thread(
            self.client._create_multipart_upload,
            settings.s3_bucket,
            object_name,
            headers,
        )

    async def get_presigned_multipart_part_url(
        self,
        object_name: str,
        upload_id: str,
        part_number: int,
        expires_seconds: int | None = None,
    ) -> str:
        """Return a browser-safe signed URL for one multipart upload part."""
        return await asyncio.to_thread(
            self.public_client.get_presigned_url,
            "PUT",
            settings.s3_bucket,
            object_name,
            timedelta(seconds=expires_seconds or settings.rag_multipart_url_expiry_seconds),
            None,
            None,
            None,
            {
                "partNumber": str(part_number),
                "uploadId": upload_id,
            },
        )

    async def complete_multipart_upload(
        self,
        object_name: str,
        upload_id: str,
        parts: list[tuple[int, str]],
    ) -> None:
        """Finalize an S3/MinIO multipart upload."""
        self._ensure_bucket()
        normalized_parts = [
            Part(part_number=part_number, etag=etag.strip().strip('"'))
            for part_number, etag in sorted(parts, key=lambda item: item[0])
        ]
        await asyncio.to_thread(
            self.client._complete_multipart_upload,
            settings.s3_bucket,
            object_name,
            upload_id,
            normalized_parts,
        )

    async def abort_multipart_upload(self, object_name: str, upload_id: str) -> None:
        """Abort an in-flight multipart upload."""
        self._ensure_bucket()
        await asyncio.to_thread(
            self.client._abort_multipart_upload,
            settings.s3_bucket,
            object_name,
            upload_id,
        )

    async def stat_file(self, object_name: str):
        """Fetch object metadata from MinIO."""
        self._ensure_bucket()
        return await asyncio.to_thread(
            self.client.stat_object,
            settings.s3_bucket,
            object_name,
        )


storage_service = StorageService()
