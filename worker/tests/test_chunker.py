"""Unit tests for chunking logic."""
from rag.chunker import chunk_text, iter_chunk_text_segments


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
    # Check indices are sequential
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


def test_iter_chunk_text_segments_streams_across_boundaries():
    """Incremental chunking should preserve overlap across segment boundaries."""
    chunks = list(
        iter_chunk_text_segments(
            ["alpha " * 40, "beta " * 40, "gamma " * 40],
            chunk_size=32,
            overlap=8,
        )
    )

    assert len(chunks) >= 2
    assert chunks[0]["chunk_index"] == 0
    assert chunks[1]["chunk_index"] == 1
    assert chunks[1]["start_pos"] < chunks[0]["end_pos"]
