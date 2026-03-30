"""Markdown document parser."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterator

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

    def supports_incremental(self) -> bool:
        return True

    def iter_text_segments(self, file_path: Path, *, segment_chars: int = 16 * 1024) -> Iterator[str]:
        """Yield normalized markdown text in bounded segments."""
        self._validate_file(file_path)

        try:
            with file_path.open("r", encoding="utf-8") as handle:
                buffer: list[str] = []
                buffer_len = 0
                for raw_line in handle:
                    normalized = self._normalize_markdown_line(raw_line)
                    if not normalized:
                        continue
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

    def _normalize_markdown_line(self, line: str) -> str:
        text = line.rstrip("\n")
        text = re.sub(r"^#{1,6}\s*", "", text)
        text = re.sub(r"^>\s*", "", text)
        text = re.sub(r"^\s*[-*+]\s+", "", text)
        text = re.sub(r"^\s*\d+\.\s+", "", text)
        text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        text = re.sub(r"`([^`]*)`", r"\1", text)
        text = re.sub(r"[*_~#>-]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return ""
        return text + "\n"
