"""Artifact model."""
from __future__ import annotations
from sqlalchemy import String, ForeignKey, Integer, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
import enum
from .base import Base, TimestampMixin

class ArtifactType(enum.Enum):
    FILE = "file"
    SCREENSHOT = "screenshot"
    REPORT = "report"
    CODE = "code"
    DATA = "data"

class Artifact(Base, TimestampMixin):
    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    task_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("task_runs.id", ondelete="CASCADE"), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    artifact_type: Mapped[ArtifactType] = mapped_column(SQLEnum(ArtifactType), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="artifacts")
    task_run: Mapped["TaskRun"] = relationship(back_populates="artifacts")
