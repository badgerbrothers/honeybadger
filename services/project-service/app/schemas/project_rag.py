"""Schemas for project to RAG binding APIs."""
from __future__ import annotations

from datetime import datetime
import uuid

from pydantic import BaseModel


class ProjectRagBindingUpdate(BaseModel):
    """Update payload for active project RAG binding."""

    rag_collection_id: uuid.UUID | None


class ProjectRagBindingResponse(BaseModel):
    """Project RAG binding response."""

    project_id: uuid.UUID
    rag_collection_id: uuid.UUID | None
    updated_at: datetime
