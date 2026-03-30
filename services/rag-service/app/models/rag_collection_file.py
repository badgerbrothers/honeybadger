"""RAG collection file model."""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import BigInteger, Enum as SQLEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class RagFileStatus(enum.Enum):
    """Status for uploaded files in a RAG collection."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RagCollectionFile(Base, TimestampMixin):
    """Metadata for one file uploaded to a global RAG collection."""

    __tablename__ = "rag_collection_files"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    rag_collection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rag_collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[RagFileStatus] = mapped_column(
        SQLEnum(RagFileStatus),
        nullable=False,
        default=RagFileStatus.PENDING,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    rag_collection = relationship("RagCollection", back_populates="files")
