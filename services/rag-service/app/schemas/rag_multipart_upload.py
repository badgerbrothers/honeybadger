"""Schemas for browser-direct multipart uploads."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class RagMultipartUploadCreateRequest(BaseModel):
    """Request to initialize a multipart upload session."""

    file_name: str = Field(min_length=1, max_length=255)
    file_size: int = Field(gt=0)
    mime_type: str | None = Field(default=None, max_length=255)


class RagMultipartUploadPartUrl(BaseModel):
    """Signed upload URL for one multipart part."""

    part_number: int
    url: str


class RagMultipartUploadCreateResponse(BaseModel):
    """Response describing a multipart upload session."""

    upload_session_id: uuid.UUID
    file_id: uuid.UUID
    storage_path: str
    upload_id: str
    part_size: int
    part_count: int
    expires_in_seconds: int
    parts: list[RagMultipartUploadPartUrl]


class RagMultipartUploadCompletePart(BaseModel):
    """Completed multipart part metadata from the browser."""

    part_number: int = Field(ge=1)
    etag: str = Field(min_length=1)


class RagMultipartUploadCompleteRequest(BaseModel):
    """Request to finalize a multipart upload."""

    upload_session_id: uuid.UUID
    parts: list[RagMultipartUploadCompletePart] = Field(min_length=1)
