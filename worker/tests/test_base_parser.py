"""Unit tests for BaseParser abstract class."""
import pytest
from pathlib import Path
from rag.parsers.base import BaseParser
from rag.parsers.exceptions import FileReadError


def test_cannot_instantiate_base_parser():
    """Test that BaseParser cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseParser()


def test_validate_file_exists():
    """Test file validation with existing file."""
    # Create a concrete implementation for testing
    class TestParser(BaseParser):
        def parse(self, file_path: Path):
            return {"text": "", "metadata": {}}

        def supported_extensions(self):
            return [".test"]

    parser = TestParser()
    # Should not raise error for existing file
    parser._validate_file(Path("tests/fixtures/sample.txt"))


def test_validate_file_not_found():
    """Test file validation raises error for missing file."""
    class TestParser(BaseParser):
        def parse(self, file_path: Path):
            return {"text": "", "metadata": {}}

        def supported_extensions(self):
            return [".test"]

    parser = TestParser()

    with pytest.raises(FileReadError):
        parser._validate_file(Path("tests/fixtures/nonexistent.txt"))
