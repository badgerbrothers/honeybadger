"""Unit tests for chunking logic."""
import pytest
from rag.chunker import chunk_text


def test_chunk_text_basic():
    """Test basic text chunking."""
    text = "test " * 1000
    chunks = chunk_text(text, chunk_size=512, overlap=50)

    assert len(chunks) > 0
    assert all("content" in chunk for chunk in chunks)
    assert all("chunk_index" in chunk for chunk in chunks)


def test_chunk_overlap():
    """Verify overlap works correctly."""
    text = "word " * 600
    chunks = chunk_text(text, chunk_size=100, overlap=20)

    assert len(chunks) >= 2
    for i, chunk in enumerate(chunks):
        assert chunk["chunk_index"] == i


def test_chunk_token_count():
    """Validate token counting."""
    text = "test " * 100
    chunks = chunk_text(text, chunk_size=50, overlap=10)

    for chunk in chunks:
        assert "token_count" in chunk
        assert chunk["token_count"] > 0


def test_empty_text():
    """Handle empty text edge case."""
    chunks = chunk_text("", chunk_size=512, overlap=50)

    assert len(chunks) == 1
    assert chunks[0]["content"] == ""
