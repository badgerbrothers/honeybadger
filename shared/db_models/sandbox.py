"""Shared SandboxSession model used by worker runtime."""
from __future__ import annotations

from enum import Enum
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class SandboxStatus(str, Enum):
    """Lifecycle states for pooled sandboxes."""

    AVAILABLE = "available"
    LEASED = "leased"
    RESETTING = "resetting"
    BROKEN = "broken"
    DRAINING = "draining"


class SandboxSession(Base, TimestampMixin):
    __tablename__ = "sandbox_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    task_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("task_runs.id", ondelete="CASCADE"), nullable=True, unique=True
    )

    container_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    image: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=SandboxStatus.AVAILABLE.value,
        server_default=SandboxStatus.AVAILABLE.value,
        index=True,
    )
    workspace_dir: Mapped[str] = mapped_column(String(512), nullable=False)
    cpu_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reuse_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    leased_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(nullable=True, index=True)
    last_health_check_at: Mapped[datetime | None] = mapped_column(nullable=True)
    lease_error: Mapped[str | None] = mapped_column(String(255), nullable=True)
    drain_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    terminated_at: Mapped[datetime | None] = mapped_column(nullable=True)

    task_run: Mapped["TaskRun | None"] = relationship(back_populates="sandbox_session")
