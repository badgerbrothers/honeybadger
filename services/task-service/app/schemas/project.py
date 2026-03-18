"""Project and ProjectNode schemas."""
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
import uuid
from app.models.project import NodeType

class ProjectCreate(BaseModel):
    """Schema for creating a new project."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None

class ProjectUpdate(BaseModel):
    """Schema for updating a project."""
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None

class ProjectResponse(BaseModel):
    """Schema for project API responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

class ProjectNodeCreate(BaseModel):
    """Schema for creating a project node."""
    name: str = Field(..., min_length=1, max_length=255)
    node_type: NodeType
    parent_id: uuid.UUID | None = None
    path: str = Field(..., min_length=1, max_length=1024)
    size: int | None = None

class ProjectNodeUpdate(BaseModel):
    """Schema for updating a project node."""
    name: str | None = Field(None, min_length=1, max_length=255)
    path: str | None = Field(None, min_length=1, max_length=1024)
    size: int | None = None

class ProjectNodeResponse(BaseModel):
    """Schema for project node API responses."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    parent_id: uuid.UUID | None
    name: str
    path: str
    node_type: NodeType
    size: int | None
    created_at: datetime
    updated_at: datetime

class ProjectFileUploadResponse(BaseModel):
    """Schema for file upload response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    path: str
    size: int
    mime_type: str | None
    created_at: datetime
