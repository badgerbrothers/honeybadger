"""Task and TaskRun models."""
from __future__ import annotations
from sqlalchemy import String, ForeignKey, Text, Enum as SQLEnum, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import uuid
import enum
from .base import Base, TimestampMixin

class TaskStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class QueueStatus(enum.Enum):
    SCHEDULED = "scheduled"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    goal: Mapped[str] = mapped_column(Text, nullable=False)
    skill: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False, default="gpt-5.3-codex")
    current_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("task_runs.id", use_alter=True, name="fk_task_current_run"), nullable=True)
    queue_status: Mapped[QueueStatus] = mapped_column(
        SQLEnum(QueueStatus), nullable=False, default=QueueStatus.SCHEDULED, index=True
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(nullable=True, index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    assigned_agent: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    conversation: Mapped["Conversation"] = relationship(back_populates="tasks")
    project: Mapped["Project"] = relationship()
    runs: Mapped[list["TaskRun"]] = relationship(back_populates="task", cascade="all, delete-orphan", foreign_keys="TaskRun.task_id")

class TaskRun(Base, TimestampMixin):
    __tablename__ = "task_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)

    status: Mapped[TaskStatus] = mapped_column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    logs: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    working_memory: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    task: Mapped["Task"] = relationship(back_populates="runs", foreign_keys=[task_id])
    sandbox_session: Mapped["SandboxSession | None"] = relationship(back_populates="task_run")
    artifacts: Mapped[list["Artifact"]] = relationship(back_populates="task_run")
