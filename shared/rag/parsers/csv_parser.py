"""CSV document parser."""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

from .exceptions import FileReadError
from .txt_parser import TxtParser


class CsvParser(TxtParser):
    """Treat CSV as normalized text for retrieval and indexing."""

    def supported_extensions(self) -> list[str]:
        return [".csv"]

    def iter_text_segments(self, file_path: Path, *, segment_chars: int = 16 * 1024) -> Iterator[str]:
        self._validate_file(file_path)
        encoding_used = self._detect_encoding(file_path)
        try:
            with file_path.open("r", encoding=encoding_used) as handle:
                buffer: list[str] = []
                buffer_len = 0
                for raw_line in handle:
                    normalized = " ".join(part.strip() for part in raw_line.split(",") if part.strip())
                    if not normalized:
                        continue
                    normalized = normalized + "\n"
                    buffer.append(normalized)
                    buffer_len += len(normalized)
                    if buffer_len >= segment_chars:
                        yield "".join(buffer)
                        buffer = []
                        buffer_len = 0

                if buffer:
                    yield "".join(buffer)
        except Exception as exc:
            raise FileReadError(f"Failed to read file: {exc}") from exc
