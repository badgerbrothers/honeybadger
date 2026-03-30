"""Multipart upload session model for project files."""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import BigInteger, Enum as SQLEnum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class ProjectUploadSessionStatus(enum.Enum):
    """Lifecycle for a browser-direct multipart project upload."""

    INITIATED = "initiated"
    COMPLETED = "completed"
    ABORTED = "aborted"
    FAILED = "failed"


class ProjectUploadSession(Base, TimestampMixin):
    """Tracks one in-flight multipart upload for a project node."""

    __tablename__ = "project_upload_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    file_id: Mapped[uuid.UUID] = mapped_column(nullable=False, unique=True, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    upload_id: Mapped[str] = mapped_column(String(512), nullable=False, unique=True, index=True)
    part_size: Mapped[int] = mapped_column(Integer, nullable=False)
    part_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ProjectUploadSessionStatus] = mapped_column(
        SQLEnum(ProjectUploadSessionStatus),
        nullable=False,
        default=ProjectUploadSessionStatus.INITIATED,
    )
