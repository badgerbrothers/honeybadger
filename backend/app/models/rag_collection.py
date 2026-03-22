"""Global reusable RAG collection models."""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum as SQLEnum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class RagFileStatus(enum.Enum):
    """Lifecycle status for a file inside a RAG collection."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RagCollection(Base, TimestampMixin):
    """Global reusable RAG collection."""

    __tablename__ = "rag_collections"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "name", name="uq_rag_collections_owner_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    files: Mapped[list["RagCollectionFile"]] = relationship(
        back_populates="rag_collection",
        cascade="all, delete-orphan",
    )


class RagCollectionFile(Base, TimestampMixin):
    """File metadata that belongs to a RAG collection."""

    __tablename__ = "rag_collection_files"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    rag_collection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rag_collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[RagFileStatus] = mapped_column(
        SQLEnum(RagFileStatus),
        nullable=False,
        default=RagFileStatus.PENDING,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    rag_collection: Mapped["RagCollection"] = relationship(back_populates="files")
