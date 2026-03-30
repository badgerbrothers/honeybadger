"""Tests for worker storage downloads."""
from pathlib import Path
from unittest.mock import Mock

import pytest

from services.storage_client import StorageClient


class _FakeResponse:
    def __init__(self, chunks: list[bytes]):
        self._chunks = list(chunks)
        self.closed = False
        self.released = False

    def read(self, _: int | None = None) -> bytes:
        if not self._chunks:
            return b""
        return self._chunks.pop(0)

    def close(self) -> None:
        self.closed = True

    def release_conn(self) -> None:
        self.released = True


@pytest.mark.asyncio
async def test_download_to_path_streams_without_buffering_whole_file(tmp_path: Path):
    """Object download should write chunks incrementally to disk."""
    client = StorageClient()
    response = _FakeResponse([b"hello ", b"world", b""])
    client._client = Mock(get_object=Mock(return_value=response))

    destination = tmp_path / "nested" / "sample.txt"
    written_path = await client.download_to_path("documents/sample.txt", destination, chunk_size=4)

    assert written_path == destination
    assert destination.read_bytes() == b"hello world"
    assert response.closed is True
    assert response.released is True
