"""Abstract base parser class for document parsers."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any
from .exceptions import FileReadError


class BaseParser(ABC):
    """Abstract base class for document parsers."""

    @abstractmethod
    def parse(self, file_path: Path) -> Dict[str, Any]:
        """Parse document and return text with metadata.

        Args:
            file_path: Path to document file

        Returns:
            Dict with 'text' (str) and 'metadata' (dict) keys
        """
        pass

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions.

        Returns:
            List of extensions (e.g., ['.txt', '.md'])
        """
        pass

    def _validate_file(self, file_path: Path) -> None:
        """Validate file exists and is readable.

        Args:
            file_path: Path to validate

        Raises:
            FileReadError: If file doesn't exist or isn't readable
        """
        if not file_path.exists():
            raise FileReadError(f"File not found: {file_path}")
        if not file_path.is_file():
            raise FileReadError(f"Not a file: {file_path}")
