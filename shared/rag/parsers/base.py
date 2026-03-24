"""Abstract base parser class for document parsers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .exceptions import FileReadError


class BaseParser(ABC):
    """Abstract base class for document parsers."""

    @abstractmethod
    def parse(self, file_path: Path) -> dict[str, Any]:
        """Parse document and return text with metadata."""

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return supported file extensions."""

    def _validate_file(self, file_path: Path) -> None:
        """Validate file exists and is readable."""
        if not file_path.exists():
            raise FileReadError(f"File not found: {file_path}")
        if not file_path.is_file():
            raise FileReadError(f"Not a file: {file_path}")
