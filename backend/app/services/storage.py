"""MinIO storage service."""
from minio import Minio
from minio.error import S3Error
import io
import structlog
from app.config import settings

logger = structlog.get_logger()


class StorageService:
    """MinIO storage service for artifacts."""

    def __init__(self):
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )
        self._bucket_checked = False

    def _ensure_bucket(self):
        """Ensure bucket exists."""
        if self._bucket_checked:
            return
        try:
            if not self.client.bucket_exists(settings.minio_bucket):
                self.client.make_bucket(settings.minio_bucket)
            self._bucket_checked = True
        except Exception as e:
            logger.warning("bucket_check_failed", error=str(e))

    async def upload_file(self, object_name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Upload file to MinIO."""
        self._ensure_bucket()
        try:
            self.client.put_object(
                settings.minio_bucket,
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
        try:
            response = self.client.get_object(settings.minio_bucket, object_name)
            return response.read()
        except S3Error as e:
            logger.error("download_failed", object_name=object_name, error=str(e))
            raise

    async def delete_file(self, object_name: str):
        """Delete file from MinIO."""
        self._ensure_bucket()
        try:
            self.client.remove_object(settings.minio_bucket, object_name)
        except S3Error as e:
            logger.error("delete_failed", object_name=object_name, error=str(e))
            raise


storage_service = StorageService()
