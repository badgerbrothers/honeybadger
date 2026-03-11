"""Plain text document parser."""
from pathlib import Path
from typing import Dict, Any
from .base import BaseParser
from .exceptions import ParseError, FileReadError


class TxtParser(BaseParser):
    """Parser for plain text files."""

    def parse(self, file_path: Path) -> Dict[str, Any]:
        """Parse text file with encoding detection.

        Args:
            file_path: Path to text file

        Returns:
            Dict with 'text' and 'metadata' keys
        """
        self._validate_file(file_path)

        text = ""
        encoding_used = "utf-8"

        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                text = file_path.read_text(encoding="latin-1")
                encoding_used = "latin-1"
            except Exception as e:
                raise ParseError(f"Failed to decode text file: {e}")
        except Exception as e:
            raise FileReadError(f"Failed to read file: {e}")

        line_count = len(text.splitlines())
        file_size = file_path.stat().st_size

        return {
            "text": text,
            "metadata": {
                "encoding": encoding_used,
                "line_count": line_count,
                "file_size": file_size,
            }
        }

    def supported_extensions(self) -> list[str]:
        """Return supported file extensions."""
        return [".txt"]
