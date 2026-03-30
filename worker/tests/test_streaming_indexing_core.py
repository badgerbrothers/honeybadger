"""Focused tests for streaming indexing behavior."""
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

import rag  # noqa: F401
from shared.rag.indexing_core import DocumentIndexingCore


class _IncrementalParser:
    def __init__(self, segments: list[str]):
        self._segments = segments
        self.parse = Mock(side_effect=AssertionError("parse() should not be used for incremental mode"))

    def supported_extensions(self) -> list[str]:
        return [".txt"]

    def supports_incremental(self) -> bool:
        return True

    def iter_text_segments(self, file_path: Path):
        for segment in self._segments:
            yield segment


@pytest.mark.asyncio
async def test_iter_document_chunks_uses_incremental_parser_without_full_parse(tmp_path: Path):
    parser = _IncrementalParser(["alpha " * 80, "beta " * 80])
    core = DocumentIndexingCore(
        embedding_service=Mock(),
        parsers={".txt": parser},
        chunk_size=32,
        overlap=8,
    )

    file_path = tmp_path / "sample.txt"
    file_path.write_text("unused", encoding="utf-8")

    chunks = [chunk async for chunk in core.iter_document_chunks(str(file_path), use_semantic=False)]

    assert len(chunks) >= 2
    parser.parse.assert_not_called()
    assert chunks[0]["chunk_index"] == 0
    assert chunks[1]["start_pos"] < chunks[0]["end_pos"]


@pytest.mark.asyncio
async def test_generate_embeddings_respects_batch_size(tmp_path: Path):
    parser = _IncrementalParser(["alpha " * 80, "beta " * 80, "gamma " * 80])

    async def _fake_embeddings(batch: list[str]):
        return [[0.1] * 3 for _ in batch]

    embedding_service = Mock()
    embedding_service.generate_embeddings_batch = AsyncMock(side_effect=_fake_embeddings)
    core = DocumentIndexingCore(
        embedding_service=embedding_service,
        parsers={".txt": parser},
        chunk_size=32,
        overlap=8,
        batch_size=2,
    )

    file_path = tmp_path / "sample.txt"
    file_path.write_text("unused", encoding="utf-8")

    chunks = [chunk async for chunk in core.iter_document_chunks(str(file_path), use_semantic=False)]
    await core.generate_embeddings(chunks)

    assert embedding_service.generate_embeddings_batch.await_count >= 2
    for call in embedding_service.generate_embeddings_batch.await_args_list:
        assert len(call.args[0]) <= 2
