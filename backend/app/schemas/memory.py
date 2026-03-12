"""Memory schemas for conversation summaries and project knowledge."""
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
import uuid


class ConversationSummaryCreate(BaseModel):
    """Schema for creating a conversation summary."""
    conversation_id: uuid.UUID
    summary_text: str = Field(..., min_length=1)
    message_count: int = Field(..., ge=0)


class ConversationSummaryResponse(BaseModel):
    """Schema for conversation summary API responses."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    summary_text: str
    message_count: int
    created_at: datetime


class ProjectMemoryCreate(BaseModel):
    """Schema for creating a project memory."""
    memory_type: str = Field(..., max_length=50)
    content: str = Field(..., min_length=1)
    memory_metadata: dict | None = None


class ProjectMemoryResponse(BaseModel):
    """Schema for project memory API responses."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    memory_type: str
    content: str
    memory_metadata: dict | None
    created_at: datetime


class ProjectMemorySearch(BaseModel):
    """Schema for searching project memories."""
    query: str = Field(..., min_length=1)
    limit: int = Field(default=10, ge=1, le=100)
    threshold: float = Field(default=0.7, ge=0.0, le=1.0)
