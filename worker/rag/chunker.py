"""Document chunking with overlap strategy."""
import tiktoken
from typing import List, Dict, Any


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> List[Dict[str, Any]]:
    """Split text into chunks with overlap.

    Args:
        text: Text to chunk
        chunk_size: Target chunk size in tokens
        overlap: Overlap size in tokens

    Returns:
        List of chunk dicts with content, index, and positions
    """
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)

    if not tokens:
        return [{"content": "", "chunk_index": 0, "start_pos": 0, "end_pos": 0, "token_count": 0}]

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(tokens):
        end = start + chunk_size
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens)

        chunks.append({
            "content": chunk_text,
            "chunk_index": chunk_index,
            "start_pos": start,
            "end_pos": min(end, len(tokens)),
            "token_count": len(chunk_tokens)
        })

        start = end - overlap
        chunk_index += 1

    return chunks
