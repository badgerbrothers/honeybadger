"""Unit tests for TxtParser."""
import pytest
from pathlib import Path
from rag.parsers.txt_parser import TxtParser
from rag.parsers.exceptions import FileReadError


def test_parse_success():
    """Test successful text file parsing."""
    parser = TxtParser()
    result = parser.parse(Path("tests/fixtures/sample.txt"))

    assert "text" in result
    assert "metadata" in result
    assert len(result["text"]) > 0
    assert "Hello World!" in result["text"]


def test_parse_returns_text_and_metadata():
    """Test parse returns correct structure."""
    parser = TxtParser()
    result = parser.parse(Path("tests/fixtures/sample.txt"))

    assert isinstance(result["text"], str)
    assert isinstance(result["metadata"], dict)
    assert "encoding" in result["metadata"]
    assert "line_count" in result["metadata"]
    assert "file_size" in result["metadata"]


def test_parse_nonexistent_file():
    """Test parsing nonexistent file raises error."""
    parser = TxtParser()

    with pytest.raises(FileReadError):
        parser.parse(Path("tests/fixtures/nonexistent.txt"))


def test_supported_extensions():
    """Test supported extensions."""
    parser = TxtParser()
    extensions = parser.supported_extensions()

    assert extensions == [".txt"]
