"""Unit tests for PdfParser."""
import pytest
from pathlib import Path
from rag.parsers.pdf_parser import PdfParser
from rag.parsers.exceptions import FileReadError, ParseError


def test_parse_success():
    """Test successful PDF file parsing."""
    parser = PdfParser()
    result = parser.parse(Path("tests/fixtures/sample.pdf"))

    assert "text" in result
    assert "metadata" in result
    assert len(result["text"]) > 0


def test_parse_returns_text_and_metadata():
    """Test parse returns correct structure with page_count."""
    parser = PdfParser()
    result = parser.parse(Path("tests/fixtures/sample.pdf"))

    assert isinstance(result["text"], str)
    assert isinstance(result["metadata"], dict)
    assert "page_count" in result["metadata"]
    assert result["metadata"]["page_count"] >= 1


def test_parse_nonexistent_file():
    """Test parsing nonexistent file raises error."""
    parser = PdfParser()

    with pytest.raises(FileReadError):
        parser.parse(Path("tests/fixtures/nonexistent.pdf"))


def test_parse_corrupted_pdf():
    """Test parsing corrupted PDF raises error."""
    parser = PdfParser()

    # Create a corrupted PDF file
    corrupted_path = Path("tests/fixtures/corrupted.pdf")
    corrupted_path.write_text("This is not a valid PDF file")

    try:
        with pytest.raises(ParseError):
            parser.parse(corrupted_path)
    finally:
        # Clean up
        if corrupted_path.exists():
            corrupted_path.unlink()


def test_supported_extensions():
    """Test supported extensions."""
    parser = PdfParser()
    extensions = parser.supported_extensions()

    assert extensions == [".pdf"]
