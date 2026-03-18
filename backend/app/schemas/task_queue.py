"""Schemas for task queue and Kanban management."""
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.task import TaskResponse


class TaskKanbanResponse(BaseModel):
    """Tasks grouped by queue status for the Kanban board."""

    model_config = ConfigDict(from_attributes=True)

    scheduled: list[TaskResponse] = Field(default_factory=list)
    queued: list[TaskResponse] = Field(default_factory=list)
    in_progress: list[TaskResponse] = Field(default_factory=list)
    done: list[TaskResponse] = Field(default_factory=list)
