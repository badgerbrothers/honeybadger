"""Project and ProjectNode models."""
from __future__ import annotations
from sqlalchemy import String, Integer, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid
import enum
from .base import Base, TimestampMixin

class NodeType(enum.Enum):
    FILE = "file"
    DIRECTORY = "directory"

class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    active_rag_collection_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)

    # Relationships
    nodes: Mapped[list["ProjectNode"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="project")
    artifacts: Mapped[list["Artifact"]] = relationship(back_populates="project")

class ProjectNode(Base, TimestampMixin):
    __tablename__ = "project_nodes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("project_nodes.id", ondelete="CASCADE"), nullable=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    node_type: Mapped[NodeType] = mapped_column(SQLEnum(NodeType), nullable=False)
    size: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="nodes")
    parent: Mapped["ProjectNode | None"] = relationship(remote_side=[id], back_populates="children")
    children: Mapped[list["ProjectNode"]] = relationship(back_populates="parent")
