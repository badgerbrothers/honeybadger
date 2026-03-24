"""Plain text document parser."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import BaseParser
from .exceptions import FileReadError, ParseError


class TxtParser(BaseParser):
    """Parser for plain text files."""

    def parse(self, file_path: Path) -> dict[str, Any]:
        """Parse text file with encoding detection."""
        self._validate_file(file_path)

        encoding_used = "utf-8"

        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                text = file_path.read_text(encoding="latin-1")
                encoding_used = "latin-1"
            except Exception as exc:
                raise ParseError(f"Failed to decode text file: {exc}") from exc
        except Exception as exc:
            raise FileReadError(f"Failed to read file: {exc}") from exc

        line_count = len(text.splitlines())
        file_size = file_path.stat().st_size

        return {
            "text": text,
            "metadata": {
                "encoding": encoding_used,
                "line_count": line_count,
                "file_size": file_size,
            },
        }

    def supported_extensions(self) -> list[str]:
        """Return supported file extensions."""
        return [".txt"]
