"""Unit tests for MarkdownParser."""
import pytest
from pathlib import Path
from rag.parsers.markdown_parser import MarkdownParser
from rag.parsers.exceptions import FileReadError


def test_parse_success():
    """Test successful Markdown file parsing."""
    parser = MarkdownParser()
    result = parser.parse(Path("tests/fixtures/sample.md"))

    assert "text" in result
    assert "metadata" in result
    assert len(result["text"]) > 0


def test_parse_strips_formatting():
    """Test that HTML tags are removed."""
    parser = MarkdownParser()
    result = parser.parse(Path("tests/fixtures/sample.md"))

    text = result["text"]
    assert "Test Document" in text
    assert "test" in text
    assert "<strong>" not in text
    assert "<em>" not in text
    assert "<h1>" not in text


def test_parse_returns_metadata():
    """Test metadata structure."""
    parser = MarkdownParser()
    result = parser.parse(Path("tests/fixtures/sample.md"))

    assert isinstance(result["metadata"], dict)
    assert "heading_count" in result["metadata"]
    assert "word_count" in result["metadata"]
    assert result["metadata"]["heading_count"] >= 2


def test_parse_nonexistent_file():
    """Test parsing nonexistent file raises error."""
    parser = MarkdownParser()

    with pytest.raises(FileReadError):
        parser.parse(Path("tests/fixtures/nonexistent.md"))


def test_supported_extensions():
    """Test supported extensions."""
    parser = MarkdownParser()
    extensions = parser.supported_extensions()

    assert extensions == [".md", ".markdown"]
