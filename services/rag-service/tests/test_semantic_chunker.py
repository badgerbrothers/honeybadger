"""Unit tests for semantic chunking."""
from __future__ import annotations

from app.rag.semantic_chunker import SemanticChunker


def test_semantic_chunker_handles_empty_text():
    chunker = SemanticChunker(max_chunk_size=64, overlap=8)
    chunks = chunker.chunk_text("")
    assert len(chunks) == 1
    assert chunks[0]["token_count"] == 0


def test_semantic_chunker_respects_max_chunk_size():
    chunker = SemanticChunker(max_chunk_size=40, overlap=5)
    text = (
        "Machine learning improves retrieval quality. "
        "Hybrid search combines lexical and semantic results. "
        "Reranking improves precision for the final top documents. "
        "Query rewriting helps sparse user input."
    )
    chunks = chunker.chunk_text(text)

    assert len(chunks) > 0
    assert all(chunk["token_count"] <= 40 for chunk in chunks)
    assert [chunk["chunk_index"] for chunk in chunks] == list(range(len(chunks)))
