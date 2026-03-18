"""MinIO storage service."""
from urllib.parse import urlparse

from minio import Minio
from minio.commonconfig import CopySource
from minio.error import S3Error
import io
import structlog
from app.config import settings

logger = structlog.get_logger()


class StorageService:
    """MinIO storage service for artifacts."""

    def __init__(self):
        endpoint, secure = self._resolve_endpoint(settings.s3_endpoint, settings.s3_secure)
        self.client = Minio(
            endpoint,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            secure=secure
        )
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

    async def upload_file(self, object_name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Upload file to MinIO."""
        self._ensure_bucket()
        try:
            self.client.put_object(
                settings.s3_bucket,
                object_name,
                io.BytesIO(data),
                length=len(data),
                content_type=content_type
            )
            return object_name
        except S3Error as e:
            logger.error("upload_failed", object_name=object_name, error=str(e))
            raise

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


storage_service = StorageService()
