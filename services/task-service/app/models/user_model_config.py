"""Per-user persisted model/provider configuration."""
from __future__ import annotations

from typing import Any
import uuid

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class UserModelConfig(Base, TimestampMixin):
    """Persisted model/provider settings owned by a single authenticated user."""

    __tablename__ = "user_model_configs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(nullable=False, unique=True, index=True)
    active_provider: Mapped[str] = mapped_column(String(32), nullable=False, default="openai")
    providers_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
