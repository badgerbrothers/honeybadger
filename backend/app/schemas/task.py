"""Task and TaskRun schemas."""
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
import uuid
from app.models.task import TaskStatus

class TaskCreate(BaseModel):
    """Schema for creating a task."""
    conversation_id: uuid.UUID
    project_id: uuid.UUID
    goal: str = Field(..., min_length=1)
    skill: str | None = Field(None, max_length=100)

class TaskUpdate(BaseModel):
    """Schema for updating a task."""
    goal: str | None = Field(None, min_length=1)

class TaskResponse(BaseModel):
    """Schema for task API responses."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    project_id: uuid.UUID
    goal: str
    skill: str | None
    model: str
    current_run_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

class TaskRunResponse(BaseModel):
    """Schema for task run API responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    task_id: uuid.UUID
    status: TaskStatus
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
