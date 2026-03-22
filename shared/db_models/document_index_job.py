"""Shared DocumentIndexJob model used by worker runtime."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class DocumentIndexStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentIndexJob(Base, TimestampMixin):
    __tablename__ = "document_index_jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    project_node_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("project_nodes.id", ondelete="CASCADE"), nullable=True
    )
    rag_collection_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[DocumentIndexStatus] = mapped_column(
        SQLEnum(DocumentIndexStatus), nullable=False, default=DocumentIndexStatus.PENDING
    )
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
