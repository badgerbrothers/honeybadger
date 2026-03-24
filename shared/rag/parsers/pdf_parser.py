"""PDF document parser."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pypdf import PdfReader

from .base import BaseParser
from .exceptions import ParseError


class PdfParser(BaseParser):
    """Parser for PDF files."""

    def parse(self, file_path: Path) -> dict[str, Any]:
        """Parse PDF file and extract text."""
        self._validate_file(file_path)

        try:
            reader = PdfReader(file_path)
        except Exception as exc:
            raise ParseError(f"Failed to read PDF: {exc}") from exc

        text_parts = []
        failed_pages = []
        for idx, page in enumerate(reader.pages):
            try:
                text_parts.append(page.extract_text())
            except Exception:
                failed_pages.append(idx + 1)

        if not text_parts:
            raise ParseError("Failed to extract text from any page")

        text = "\n\n--- Page Break ---\n\n".join(text_parts)
        metadata: dict[str, Any] = {"page_count": len(reader.pages)}
        if failed_pages:
            metadata["failed_pages"] = failed_pages

        if reader.metadata:
            if reader.metadata.author:
                metadata["author"] = reader.metadata.author
            if reader.metadata.title:
                metadata["title"] = reader.metadata.title

        return {"text": text, "metadata": metadata}

    def supported_extensions(self) -> list[str]:
        """Return supported file extensions."""
        return [".pdf"]
