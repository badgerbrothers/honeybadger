"""Schemas for global RAG collections."""
from __future__ import annotations

from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class RagCollectionCreate(BaseModel):
    """Create payload for a global RAG collection."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class RagCollectionUpdate(BaseModel):
    """Patch payload for a global RAG collection."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None


class RagCollectionResponse(BaseModel):
    """RAG collection API response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
