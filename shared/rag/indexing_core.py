"""Shared indexing pipeline helpers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, Mapping

from .chunker import chunk_text, iter_chunk_text_segments
from .parsers import UnsupportedFormatError
from .semantic_chunker import SemanticChunker

DEFAULT_BATCH_SIZE = 2048
DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 50


class DocumentIndexingCore:
    """Reusable parse/chunk/embed pipeline independent of DB writes."""

    def __init__(
        self,
        embedding_service: Any,
        parsers: Mapping[str, Any],
        *,
        batch_size: int = DEFAULT_BATCH_SIZE,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_CHUNK_OVERLAP,
        semantic_chunker_cls: type[SemanticChunker] = SemanticChunker,
    ) -> None:
        self.embedding_service = embedding_service
        self.parsers = dict(parsers)
        self.batch_size = batch_size
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.semantic_chunker_cls = semantic_chunker_cls

    def get_parser(self, file_path: str):
        """Return the parser for the provided file path."""
        ext = Path(file_path).suffix.lower()
        parser = self.parsers.get(ext)
        if parser is None:
            raise UnsupportedFormatError(f"Unsupported file type: {ext}")
        return parser

    def supports_incremental_processing(self, file_path: str) -> bool:
        """Return whether the file can be processed incrementally."""
        parser = self.get_parser(file_path)
        return bool(parser.supports_incremental())

    async def parse_document(self, file_path: str) -> str:
        """Parse a document and return extracted text."""
        parser = self.get_parser(file_path)
        result = parser.parse(Path(file_path))
        return result["text"]

    async def chunk_document(self, text: str, *, use_semantic: bool = True) -> list[dict[str, Any]]:
        """Chunk a document using semantic or token-based chunking."""
        if use_semantic:
            semantic_chunker = self.semantic_chunker_cls(
                max_chunk_size=self.chunk_size,
                overlap=self.overlap,
            )
            return semantic_chunker.chunk_text(text)
        return chunk_text(text, chunk_size=self.chunk_size, overlap=self.overlap)

    async def iter_document_chunks(
        self,
        file_path: str,
        *,
        use_semantic: bool = True,
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield chunks for a document, using incremental parsing when available."""
        parser = self.get_parser(file_path)
        if use_semantic or not parser.supports_incremental():
            text = await self.parse_document(file_path)
            for chunk in await self.chunk_document(text, use_semantic=use_semantic):
                yield chunk
            return

        for chunk in iter_chunk_text_segments(
            parser.iter_text_segments(Path(file_path)),
            chunk_size=self.chunk_size,
            overlap=self.overlap,
        ):
            yield chunk

    async def iter_document_chunk_batches(
        self,
        file_path: str,
        *,
        use_semantic: bool = True,
        batch_size: int | None = None,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        """Yield document chunks in bounded batches."""
        effective_batch_size = batch_size or self.batch_size
        batch: list[dict[str, Any]] = []

        async for chunk in self.iter_document_chunks(file_path, use_semantic=use_semantic):
            batch.append(chunk)
            if len(batch) >= effective_batch_size:
                yield batch
                batch = []

        if batch:
            yield batch

    async def generate_embeddings(self, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Attach embeddings to chunk payloads in batches."""
        if not chunks:
            return []

        texts = [chunk["content"] for chunk in chunks]
        all_embeddings: list[list[float]] = []

        for index in range(0, len(texts), self.batch_size):
            batch = texts[index : index + self.batch_size]
            embeddings = await self.embedding_service.generate_embeddings_batch(batch)
            all_embeddings.extend(embeddings)

        hydrated_chunks: list[dict[str, Any]] = []
        for chunk, embedding in zip(chunks, all_embeddings):
            hydrated = dict(chunk)
            hydrated["embedding"] = embedding
            hydrated_chunks.append(hydrated)

        return hydrated_chunks

    async def prepare_document_chunks(
        self,
        file_path: str,
        *,
        use_semantic: bool = True,
    ) -> list[dict[str, Any]]:
        """Run parse, chunk, and embedding generation for a document."""
        chunks = [chunk async for chunk in self.iter_document_chunks(file_path, use_semantic=use_semantic)]
        return await self.generate_embeddings(chunks)

    @staticmethod
    def build_chunk_payloads(
        *,
        project_id: Any,
        rag_collection_id: Any,
        file_path: str,
        chunks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build DB-ready chunk payloads without committing to a concrete model."""
        payloads: list[dict[str, Any]] = []
        for chunk in chunks:
            payloads.append(
                {
                    "project_id": project_id,
                    "rag_collection_id": rag_collection_id,
                    "file_path": file_path,
                    "chunk_index": chunk["chunk_index"],
                    "content": chunk["content"],
                    "embedding": chunk["embedding"],
                    "token_count": chunk["token_count"],
                    "chunk_metadata": {
                        "start_pos": chunk["start_pos"],
                        "end_pos": chunk["end_pos"],
                    },
                }
            )
        return payloads
