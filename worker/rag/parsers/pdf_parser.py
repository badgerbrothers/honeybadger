"""PDF document parser."""
from pypdf import PdfReader
from pathlib import Path
from typing import Dict, Any
from .base import BaseParser
from .exceptions import ParseError


class PdfParser(BaseParser):
    """Parser for PDF files."""

    def parse(self, file_path: Path) -> Dict[str, Any]:
        """Parse PDF file and extract text.

        Args:
            file_path: Path to PDF file

        Returns:
            Dict with 'text' and 'metadata' keys
        """
        self._validate_file(file_path)

        try:
            reader = PdfReader(file_path)
        except Exception as e:
            raise ParseError(f"Failed to read PDF: {e}")

        text_parts = []
        failed_pages = []
        for i, page in enumerate(reader.pages):
            try:
                text_parts.append(page.extract_text())
            except Exception:
                failed_pages.append(i + 1)

        if not text_parts:
            raise ParseError("Failed to extract text from any page")

        text = "\n\n--- Page Break ---\n\n".join(text_parts)

        metadata = {
            "page_count": len(reader.pages),
        }
        if failed_pages:
            metadata["failed_pages"] = failed_pages

        if reader.metadata:
            if reader.metadata.author:
                metadata["author"] = reader.metadata.author
            if reader.metadata.title:
                metadata["title"] = reader.metadata.title

        return {
            "text": text,
            "metadata": metadata
        }

    def supported_extensions(self) -> list[str]:
        """Return supported file extensions."""
        return [".pdf"]
