"""Multipart upload session model for direct browser uploads."""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import BigInteger, Enum as SQLEnum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class RagUploadSessionStatus(enum.Enum):
    """Lifecycle for a browser-to-MinIO multipart upload session."""

    INITIATED = "initiated"
    COMPLETED = "completed"
    ABORTED = "aborted"
    FAILED = "failed"


class RagUploadSession(Base, TimestampMixin):
    """Tracks one in-flight multipart upload for a RAG collection file."""

    __tablename__ = "rag_upload_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    file_id: Mapped[uuid.UUID] = mapped_column(nullable=False, unique=True, index=True)
    rag_collection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rag_collections.id", ondelete="CASCADE"),
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
    status: Mapped[RagUploadSessionStatus] = mapped_column(
        SQLEnum(RagUploadSessionStatus),
        nullable=False,
        default=RagUploadSessionStatus.INITIATED,
    )
