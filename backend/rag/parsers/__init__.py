"""Document parsers for RAG system."""
from pathlib import Path


class TxtParser:
    """Plain text parser."""

    def parse(self, file_path: Path) -> dict:
        """Parse text file."""
        return {"text": file_path.read_text(encoding="utf-8"), "metadata": {}}


class MarkdownParser:
    """Markdown parser."""

    def parse(self, file_path: Path) -> dict:
        """Parse markdown file."""
        return {"text": file_path.read_text(encoding="utf-8"), "metadata": {}}


class PdfParser:
    """PDF parser."""

    def parse(self, file_path: Path) -> dict:
        """Parse PDF file."""
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(file_path))
            text = "\n".join(page.extract_text() for page in reader.pages)
            return {"text": text, "metadata": {"pages": len(reader.pages)}}
        except Exception as e:
            raise ValueError(f"Failed to parse PDF: {e}")


__all__ = ["TxtParser", "MarkdownParser", "PdfParser"]
