"""Plain text document parser."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

from .base import BaseParser
from .exceptions import FileReadError, ParseError


class TxtParser(BaseParser):
    """Parser for plain text files."""

    def parse(self, file_path: Path) -> dict[str, Any]:
        """Parse text file with encoding detection."""
        self._validate_file(file_path)

        try:
            encoding_used = self._detect_encoding(file_path)
            text = file_path.read_text(encoding=encoding_used)
        except Exception as exc:
            if isinstance(exc, ParseError):
                raise
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

    def supports_incremental(self) -> bool:
        return True

    def iter_text_segments(self, file_path: Path, *, segment_chars: int = 16 * 1024) -> Iterator[str]:
        """Yield bounded text segments for large-file indexing."""
        self._validate_file(file_path)
        encoding_used = self._detect_encoding(file_path)
        try:
            with file_path.open("r", encoding=encoding_used) as handle:
                while True:
                    segment = handle.read(segment_chars)
                    if not segment:
                        break
                    yield segment
        except Exception as exc:
            raise FileReadError(f"Failed to read file: {exc}") from exc

    def _detect_encoding(self, file_path: Path) -> str:
        try:
            with file_path.open("r", encoding="utf-8") as handle:
                handle.read(4096)
            return "utf-8"
        except UnicodeDecodeError:
            try:
                with file_path.open("r", encoding="latin-1") as handle:
                    handle.read(4096)
                return "latin-1"
            except Exception as exc:
                raise ParseError(f"Failed to decode text file: {exc}") from exc
