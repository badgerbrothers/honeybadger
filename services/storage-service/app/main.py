"""Storage service FastAPI application."""
from __future__ import annotations

from io import BytesIO
from urllib.parse import urlparse
import os
import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from minio import Minio
from minio.commonconfig import CopySource
from minio.error import S3Error
from pydantic import BaseModel
import structlog

app = FastAPI(title="Storage Service")
logger = structlog.get_logger()


class CopyRequest(BaseModel):
    source_object: str
    target_object: str


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


S3_ENDPOINT = os.getenv("S3_ENDPOINT", "localhost:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "badgers")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "badgers_dev_password")
S3_BUCKET = os.getenv("S3_BUCKET", "badgers-artifacts")
S3_SECURE = os.getenv("S3_SECURE", "false").lower() in {"1", "true", "yes", "on"}

_endpoint, _secure = _resolve_endpoint(S3_ENDPOINT, S3_SECURE)
minio_client = Minio(
    _endpoint,
    access_key=S3_ACCESS_KEY,
    secret_key=S3_SECRET_KEY,
    secure=_secure,
)
_bucket_checked = False


def _ensure_bucket() -> None:
    global _bucket_checked
    if _bucket_checked:
        return
    try:
        if not minio_client.bucket_exists(S3_BUCKET):
            minio_client.make_bucket(S3_BUCKET)
        _bucket_checked = True
    except Exception as exc:
        logger.warning("bucket_check_failed", error=str(exc), bucket=S3_BUCKET)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "storage-service"}


@app.get("/api/storage")
async def storage_root() -> dict[str, str]:
    return {"status": "ok", "service": "storage-service"}


@app.post("/api/storage/upload")
async def upload_file(
    file: UploadFile = File(...),
    object_name: str | None = None,
) -> dict[str, str | int]:
    """Upload a file object to MinIO and return object metadata."""
    data = await file.read()
    object_name = object_name or file.filename or f"upload-{uuid.uuid4().hex}"

    _ensure_bucket()
    try:
        minio_client.put_object(
            S3_BUCKET,
            object_name,
            BytesIO(data),
            length=len(data),
            content_type=file.content_type or "application/octet-stream",
        )
    except S3Error as exc:
        logger.error("upload_failed", object_name=object_name, error=str(exc))
        raise HTTPException(status_code=502, detail="storage upload failed") from exc

    logger.info("file_uploaded", object_name=object_name, size=len(data))
    return {
        "object_name": object_name,
        "bucket": S3_BUCKET,
        "size": len(data),
        "content_type": file.content_type or "application/octet-stream",
    }


@app.get("/api/storage/download/{object_name:path}")
async def download_file(object_name: str) -> StreamingResponse:
    """Download a file object from MinIO."""
    _ensure_bucket()
    response = None
    try:
        response = minio_client.get_object(S3_BUCKET, object_name)
        payload = response.read()
    except S3Error as exc:
        logger.error("download_failed", object_name=object_name, error=str(exc))
        raise HTTPException(status_code=404, detail="object not found") from exc
    finally:
        if response is not None:
            response.close()
            response.release_conn()

    logger.info("file_downloaded", object_name=object_name, size=len(payload))
    return StreamingResponse(
        BytesIO(payload),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{object_name}"'},
    )


@app.delete("/api/storage/object/{object_name:path}")
async def delete_file(object_name: str) -> dict[str, str]:
    """Delete a file object from MinIO."""
    _ensure_bucket()
    try:
        minio_client.remove_object(S3_BUCKET, object_name)
    except S3Error as exc:
        logger.error("delete_failed", object_name=object_name, error=str(exc))
        raise HTTPException(status_code=404, detail="object not found") from exc

    logger.info("file_deleted", object_name=object_name)
    return {"deleted": object_name}


@app.post("/api/storage/copy")
async def copy_file(request: CopyRequest) -> dict[str, str]:
    """Copy an object inside the configured bucket."""
    _ensure_bucket()
    try:
        minio_client.copy_object(
            S3_BUCKET,
            request.target_object,
            CopySource(S3_BUCKET, request.source_object),
        )
    except S3Error as exc:
        logger.error(
            "copy_failed",
            source_object=request.source_object,
            target_object=request.target_object,
            error=str(exc),
        )
        raise HTTPException(status_code=404, detail="copy failed") from exc

    logger.info(
        "file_copied",
        source_object=request.source_object,
        target_object=request.target_object,
    )
    return {"target_object": request.target_object}
