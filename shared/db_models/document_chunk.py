"""Shared DocumentChunk model used by worker runtime."""
import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class DocumentChunk(Base, TimestampMixin):
    __tablename__ = "document_chunk"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    rag_collection_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Vector] = mapped_column(Vector(1536))
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_metadata: Mapped[dict] = mapped_column(JSON, nullable=True)
