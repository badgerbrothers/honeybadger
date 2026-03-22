"""Schemas for RAG collection files."""
from __future__ import annotations

from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict

from app.models.rag_collection_file import RagFileStatus


class RagFileResponse(BaseModel):
    """Metadata response for a file in a RAG collection."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rag_collection_id: uuid.UUID
    storage_path: str
    file_name: str
    file_size: int
    mime_type: str | None
    status: RagFileStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class RagFileUploadResponse(RagFileResponse):
    """Upload response with optional indexing job id."""

    index_job_id: uuid.UUID | None = None
