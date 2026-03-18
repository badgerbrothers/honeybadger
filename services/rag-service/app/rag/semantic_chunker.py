"""Semantic chunking based on sentence boundaries and local cohesion."""
from __future__ import annotations

import re
from typing import Any

import tiktoken

try:
    import nltk
except Exception:  # pragma: no cover - optional runtime dependency
    nltk = None


class SemanticChunker:
    """Chunk text by sentence-level semantic boundaries."""

    def __init__(self, max_chunk_size: int = 512, overlap: int = 50):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def chunk_text(self, text: str) -> list[dict[str, Any]]:
        if not text.strip():
            return [
                {
                    "content": "",
                    "chunk_index": 0,
                    "start_pos": 0,
                    "end_pos": 0,
                    "token_count": 0,
                }
            ]

        sentences = self._split_sentences(text)
        if len(sentences) == 1:
            return self._token_split(text, base_index=0)

        similarities = self._adjacent_similarities(sentences)
        threshold = self._percentile(similarities, 0.25) if similarities else 0.0
        boundaries = [0]
        for idx, sim in enumerate(similarities):
            if sim <= threshold:
                boundaries.append(idx + 1)
        boundaries.append(len(sentences))

        chunks: list[dict[str, Any]] = []
        chunk_index = 0
        for i in range(len(boundaries) - 1):
            start = boundaries[i]
            end = boundaries[i + 1]
            content = " ".join(sentences[start:end]).strip()
            if not content:
                continue
            token_count = len(self.encoding.encode(content))
            if token_count <= self.max_chunk_size:
                chunks.append(
                    {
                        "content": content,
                        "chunk_index": chunk_index,
                        "start_pos": start,
                        "end_pos": end,
                        "token_count": token_count,
                    }
                )
                chunk_index += 1
                continue

            split_chunks = self._token_split(content, base_index=chunk_index)
            chunks.extend(split_chunks)
            chunk_index += len(split_chunks)

        return chunks

    def _split_sentences(self, text: str) -> list[str]:
        if nltk is not None:
            try:
                nltk.data.find("tokenizers/punkt")
                sentences = nltk.sent_tokenize(text)
                return [s.strip() for s in sentences if s.strip()]
            except LookupError:
                pass
        parts = re.split(r"(?<=[.!?。！？])\s+|\n+", text)
        return [p.strip() for p in parts if p.strip()]

    def _adjacent_similarities(self, sentences: list[str]) -> list[float]:
        sims: list[float] = []
        for idx in range(len(sentences) - 1):
            left = self._token_set(sentences[idx])
            right = self._token_set(sentences[idx + 1])
            if not left or not right:
                sims.append(0.0)
                continue
            intersection = len(left.intersection(right))
            union = len(left.union(right))
            sims.append(intersection / union if union else 0.0)
        return sims

    def _token_set(self, sentence: str) -> set[str]:
        return set(re.findall(r"[A-Za-z0-9_\\-]+", sentence.lower()))

    def _token_split(self, text: str, base_index: int) -> list[dict[str, Any]]:
        tokens = self.encoding.encode(text)
        if not tokens:
            return []

        chunks: list[dict[str, Any]] = []
        start = 0
        local_index = 0
        while start < len(tokens):
            end = min(start + self.max_chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunks.append(
                {
                    "content": self.encoding.decode(chunk_tokens),
                    "chunk_index": base_index + local_index,
                    "start_pos": start,
                    "end_pos": end,
                    "token_count": len(chunk_tokens),
                }
            )
            if end >= len(tokens):
                break
            start = max(end - self.overlap, 0)
            local_index += 1
        return chunks

    def _percentile(self, values: list[float], p: float) -> float:
        if not values:
            return 0.0
        sorted_values = sorted(values)
        idx = int((len(sorted_values) - 1) * p)
        return sorted_values[idx]
