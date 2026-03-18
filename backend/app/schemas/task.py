"""Task and TaskRun schemas."""
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
import uuid
from app.models.task import TaskStatus, QueueStatus

class TaskCreate(BaseModel):
    """Schema for creating a task."""
    conversation_id: uuid.UUID
    project_id: uuid.UUID
    goal: str = Field(..., min_length=1)
    skill: str | None = Field(None, max_length=100)
    model: str | None = Field(None, max_length=100)
    scheduled_at: datetime | None = None
    priority: int = Field(default=0, ge=0, le=100)
    assigned_agent: str | None = Field(None, max_length=100)

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
    queue_status: QueueStatus
    scheduled_at: datetime | None
    priority: int
    assigned_agent: str | None
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
    logs: list[dict] | None = None
    working_memory: dict | None = None
    created_at: datetime
    updated_at: datetime
