"""Markdown document parser."""
import markdown
from pathlib import Path
from typing import Dict, Any
import re
from .base import BaseParser
from .exceptions import ParseError, FileReadError


class MarkdownParser(BaseParser):
    """Parser for Markdown files."""

    def parse(self, file_path: Path) -> Dict[str, Any]:
        """Parse Markdown file and extract plain text.

        Args:
            file_path: Path to Markdown file

        Returns:
            Dict with 'text' and 'metadata' keys
        """
        self._validate_file(file_path)

        try:
            md_content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            raise FileReadError(f"Failed to read file: {e}")

        try:
            html = markdown.markdown(md_content)
            text = self._strip_html_tags(html)
        except Exception as e:
            raise ParseError(f"Failed to parse Markdown: {e}")

        heading_count = len(re.findall(r'^#+\s', md_content, re.MULTILINE))
        word_count = len(text.split())

        return {
            "text": text,
            "metadata": {
                "heading_count": heading_count,
                "word_count": word_count,
            }
        }

    def _strip_html_tags(self, html: str) -> str:
        """Remove HTML tags from string."""
        return re.sub(r'<[^>]+>', '', html)

    def supported_extensions(self) -> list[str]:
        """Return supported file extensions."""
        return [".md", ".markdown"]
