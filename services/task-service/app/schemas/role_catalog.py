"""Role catalog response schemas."""
from typing import Literal

from pydantic import BaseModel, Field


class RoleCatalogItem(BaseModel):
    """Role document metadata and markdown content."""

    id: str = Field(..., min_length=1, max_length=200)
    name: str = Field(..., min_length=1, max_length=200)
    summary: str = Field(..., min_length=1, max_length=300)
    iconKind: Literal["browser", "terminal", "python", "file"] = "file"
    markdown: str = Field(default="")
    category: str = Field(default="general")
    path: str = Field(..., min_length=1)
