"""Document chunking with overlap strategy."""
from __future__ import annotations

from typing import Any

import tiktoken


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[dict[str, Any]]:
    """Split text into chunks with overlap."""
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)

    if not tokens:
        return [{"content": "", "chunk_index": 0, "start_pos": 0, "end_pos": 0, "token_count": 0}]

    chunks: list[dict[str, Any]] = []
    start = 0
    chunk_index = 0

    while start < len(tokens):
        end = start + chunk_size
        chunk_tokens = tokens[start:end]
        chunk_content = encoding.decode(chunk_tokens)

        chunks.append(
            {
                "content": chunk_content,
                "chunk_index": chunk_index,
                "start_pos": start,
                "end_pos": min(end, len(tokens)),
                "token_count": len(chunk_tokens),
            }
        )

        start = end - overlap
        chunk_index += 1

    return chunks
