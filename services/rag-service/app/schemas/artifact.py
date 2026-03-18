"""Artifact schemas."""
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
import uuid
from app.models.artifact import ArtifactType

class ArtifactCreate(BaseModel):
    """Schema for creating an artifact."""
    name: str = Field(..., min_length=1, max_length=255)
    artifact_type: ArtifactType
    storage_path: str = Field(..., min_length=1, max_length=1024)
    size: int = Field(..., ge=0)
    mime_type: str | None = Field(None, max_length=100)

class ArtifactResponse(BaseModel):
    """Schema for artifact API responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    project_id: uuid.UUID
    task_run_id: uuid.UUID
    name: str
    artifact_type: ArtifactType
    storage_path: str
    size: int
    mime_type: str | None
    created_at: datetime
