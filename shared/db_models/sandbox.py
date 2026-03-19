"""Shared SandboxSession model used by worker runtime."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class SandboxSession(Base, TimestampMixin):
    __tablename__ = "sandbox_sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    task_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("task_runs.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    container_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    image: Mapped[str] = mapped_column(String(255), nullable=False)
    cpu_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    terminated_at: Mapped[datetime | None] = mapped_column(nullable=True)

    task_run: Mapped["TaskRun"] = relationship(back_populates="sandbox_session")

