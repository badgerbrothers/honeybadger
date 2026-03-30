"""Compatibility wrapper around shared chunking utilities."""

from shared.rag.chunker import chunk_text, iter_chunk_text_segments

__all__ = ["chunk_text", "iter_chunk_text_segments"]
