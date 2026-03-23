"""Skill catalog response schemas."""
from typing import Literal

from pydantic import BaseModel, Field


SkillTool = Literal["browser", "shell", "python", "fileio"]


class SkillCatalogItem(BaseModel):
    """Skill markdown metadata and parsed tool hints."""

    id: str = Field(..., min_length=1, max_length=200)
    name: str = Field(..., min_length=1, max_length=200)
    summary: str = Field(..., min_length=1, max_length=300)
    iconKind: Literal["browser", "terminal", "python", "file"] = "file"
    tools: list[SkillTool] = Field(default_factory=list)
    markdown: str = Field(default="")
    category: str = Field(default="general")
    path: str = Field(..., min_length=1)
