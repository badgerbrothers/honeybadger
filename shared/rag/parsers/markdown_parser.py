"""Markdown document parser."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import markdown

from .base import BaseParser
from .exceptions import FileReadError, ParseError


class MarkdownParser(BaseParser):
    """Parser for Markdown files."""

    def parse(self, file_path: Path) -> dict[str, Any]:
        """Parse Markdown file and extract plain text."""
        self._validate_file(file_path)

        try:
            md_content = file_path.read_text(encoding="utf-8")
        except Exception as exc:
            raise FileReadError(f"Failed to read file: {exc}") from exc

        try:
            html = markdown.markdown(md_content)
            text = self._strip_html_tags(html)
        except Exception as exc:
            raise ParseError(f"Failed to parse Markdown: {exc}") from exc

        heading_count = len(re.findall(r"^#+\s", md_content, re.MULTILINE))
        word_count = len(text.split())

        return {
            "text": text,
            "metadata": {
                "heading_count": heading_count,
                "word_count": word_count,
            },
        }

    def _strip_html_tags(self, html: str) -> str:
        """Remove HTML tags from string."""
        return re.sub(r"<[^>]+>", "", html)

    def supported_extensions(self) -> list[str]:
        """Return supported file extensions."""
        return [".md", ".markdown"]
