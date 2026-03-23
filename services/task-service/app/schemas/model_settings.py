"""Schemas for persisted per-user model/provider settings."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ProviderId = Literal["openai", "anthropic", "relay"]


class ModelProviderSettings(BaseModel):
    """Settings for one configured provider."""

    enabled: bool = False
    api_key: str = Field(default="", max_length=4096)
    base_url: str = Field(default="", max_length=2048)
    main_model: str = Field(default="", min_length=1, max_length=200)
    note: str = Field(default="", max_length=2000)


class ModelSettingsPayload(BaseModel):
    """Base request/response payload for per-user model settings."""

    active_provider: ProviderId = "openai"
    providers: dict[ProviderId, ModelProviderSettings]


class ModelSettingsResponse(ModelSettingsPayload):
    """Response payload for model settings reads/writes."""

    updated_at: datetime | None = None
