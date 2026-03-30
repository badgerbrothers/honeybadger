"""Document chunking with overlap strategy."""
from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any

import tiktoken


def _build_chunk(
    *,
    encoding: tiktoken.Encoding,
    tokens: list[int],
    chunk_index: int,
    start_pos: int,
) -> dict[str, Any]:
    """Build a chunk payload from encoded tokens."""
    return {
        "content": encoding.decode(tokens),
        "chunk_index": chunk_index,
        "start_pos": start_pos,
        "end_pos": start_pos + len(tokens),
        "token_count": len(tokens),
    }


def iter_chunk_text_segments(
    segments: Iterable[str],
    *,
    chunk_size: int = 512,
    overlap: int = 50,
) -> Iterator[dict[str, Any]]:
    """Incrementally split text segments into overlapping token chunks."""
    encoding = tiktoken.get_encoding("cl100k_base")
    buffer_tokens: list[int] = []
    chunk_index = 0
    start_pos = 0
    saw_any_tokens = False

    for segment in segments:
        if not segment:
            continue

        segment_tokens = encoding.encode(segment)
        if not segment_tokens:
            continue

        saw_any_tokens = True
        buffer_tokens.extend(segment_tokens)

        while len(buffer_tokens) >= chunk_size:
            chunk_tokens = buffer_tokens[:chunk_size]
            yield _build_chunk(
                encoding=encoding,
                tokens=chunk_tokens,
                chunk_index=chunk_index,
                start_pos=start_pos,
            )
            advance_by = max(len(chunk_tokens) - overlap, 1)
            start_pos += advance_by
            buffer_tokens = buffer_tokens[advance_by:]
            chunk_index += 1

    if buffer_tokens:
        yield _build_chunk(
            encoding=encoding,
            tokens=buffer_tokens,
            chunk_index=chunk_index,
            start_pos=start_pos,
        )
        return

    if not saw_any_tokens:
        yield _build_chunk(
            encoding=encoding,
            tokens=[],
            chunk_index=0,
            start_pos=0,
        )


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[dict[str, Any]]:
    """Split text into chunks with overlap."""
    chunks = list(iter_chunk_text_segments([text], chunk_size=chunk_size, overlap=overlap))

    return chunks
