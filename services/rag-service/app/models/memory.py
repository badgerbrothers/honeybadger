"""Memory models for conversation summaries and project knowledge."""
from __future__ import annotations
from sqlalchemy import String, ForeignKey, Text, Integer, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
import uuid
from .base import Base, TimestampMixin


class ConversationSummary(Base, TimestampMixin):
    """Summary of conversation messages."""

    __tablename__ = "conversation_summaries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    conversation: Mapped["Conversation"] = relationship()


class ProjectMemory(Base, TimestampMixin):
    """Project-level memory with semantic search capability."""

    __tablename__ = "project_memories"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    memory_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Vector] = mapped_column(Vector(1536))
    memory_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship()

    __table_args__ = (
        Index("ix_project_memories_embedding", "embedding", postgresql_using="ivfflat"),
    )
