"""MinIO storage service for project-service."""
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
    """Direct MinIO client for project-service."""

    def __init__(self) -> None:
        endpoint, secure = self._resolve_endpoint(settings.s3_endpoint, settings.s3_secure)
        public_endpoint, public_secure = self._resolve_endpoint(
            settings.s3_public_endpoint,
            settings.s3_public_secure,
        )
        self.client = Minio(
            endpoint,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            secure=secure,
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

    def _ensure_bucket(self) -> None:
        if self._bucket_checked:
            return
        try:
            if not self.client.bucket_exists(settings.s3_bucket):
                self.client.make_bucket(settings.s3_bucket)
            self._bucket_checked = True
        except Exception as exc:
            logger.warning("bucket_check_failed", error=str(exc))

    def _blocking_put_object(
        self,
        object_name: str,
        stream: BinaryIO,
        length: int,
        content_type: str,
    ) -> str:
        self._ensure_bucket()
        try:
            if hasattr(stream, "seek"):
                stream.seek(0)
            self.client.put_object(
                settings.s3_bucket,
                object_name,
                stream,
                length=length,
                content_type=content_type,
                part_size=settings.s3_multipart_part_size if length > settings.s3_multipart_part_size else 0,
            )
            return object_name
        except S3Error as exc:
            logger.error("upload_failed", object_name=object_name, error=str(exc))
            raise

    async def upload_file(
        self,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        return await asyncio.to_thread(
            self._blocking_put_object,
            object_name,
            io.BytesIO(data),
            len(data),
            content_type,
        )

    async def delete_file(self, object_name: str) -> None:
        self._ensure_bucket()
        await asyncio.to_thread(
            self.client.remove_object,
            settings.s3_bucket,
            object_name,
        )

    async def copy_file(self, source_object: str, target_object: str) -> str:
        self._ensure_bucket()
        await asyncio.to_thread(
            self.client.copy_object,
            settings.s3_bucket,
            target_object,
            CopySource(settings.s3_bucket, source_object),
        )
        return target_object

    async def create_multipart_upload(
        self,
        object_name: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        self._ensure_bucket()
        return await asyncio.to_thread(
            self.client._create_multipart_upload,
            settings.s3_bucket,
            object_name,
            {"Content-Type": content_type},
        )

    async def get_presigned_multipart_part_url(
        self,
        object_name: str,
        upload_id: str,
        part_number: int,
    ) -> str:
        return await asyncio.to_thread(
            self.public_client.get_presigned_url,
            "PUT",
            settings.s3_bucket,
            object_name,
            timedelta(seconds=settings.project_multipart_url_expiry_seconds),
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
        await asyncio.to_thread(
            self.client._abort_multipart_upload,
            settings.s3_bucket,
            object_name,
            upload_id,
        )

    async def stat_file(self, object_name: str):
        self._ensure_bucket()
        return await asyncio.to_thread(
            self.client.stat_object,
            settings.s3_bucket,
            object_name,
        )


storage_service = StorageService()
