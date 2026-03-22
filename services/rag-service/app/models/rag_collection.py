"""Global reusable RAG collection model."""
from __future__ import annotations

import uuid

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class RagCollection(Base, TimestampMixin):
    """User-owned reusable RAG collection."""

    __tablename__ = "rag_collections"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "name", name="uq_rag_collections_owner_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    files: Mapped[list["RagCollectionFile"]] = relationship(
        back_populates="rag_collection",
        cascade="all, delete-orphan",
    )
