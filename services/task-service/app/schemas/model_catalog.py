"""Model catalog response schemas."""
from pydantic import BaseModel, Field


class ModelCatalogResponse(BaseModel):
    """Supported models metadata for task creation UI."""

    default_model: str = Field(..., min_length=1, max_length=100)
    supported_models: list[str] = Field(default_factory=list)
