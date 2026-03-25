from __future__ import annotations

import io
from unittest.mock import Mock

import pytest
from minio.error import S3Error

from app.services.storage import StorageService


@pytest.mark.asyncio
async def test_upload_stream_rewinds_stream_and_uses_to_thread(monkeypatch):
    service = StorageService()
    service._bucket_checked = True

    recorded: dict[str, object] = {}

    def put_object(bucket, object_name, stream, length, content_type, part_size=0, num_parallel_uploads=3):
        recorded["bucket"] = bucket
        recorded["object_name"] = object_name
        recorded["stream_pos"] = stream.tell()
        recorded["payload"] = stream.read()
        recorded["length"] = length
        recorded["content_type"] = content_type
        recorded["part_size"] = part_size
        recorded["num_parallel_uploads"] = num_parallel_uploads

    service.client = Mock()
    service.client.put_object = put_object

    called: dict[str, object] = {}

    async def fake_to_thread(func, *args):
        called["func_name"] = getattr(func, "__name__", "")
        return func(*args)

    monkeypatch.setattr("app.services.storage.asyncio.to_thread", fake_to_thread)

    stream = io.BytesIO(b"abcdef")
    stream.seek(3)

    result = await service.upload_stream("rags/test/file.txt", stream, 6, "text/plain")

    assert result == "rags/test/file.txt"
    assert called["func_name"] == "_blocking_put_object"
    assert recorded["object_name"] == "rags/test/file.txt"
    assert recorded["stream_pos"] == 0
    assert recorded["payload"] == b"abcdef"
    assert recorded["length"] == 6
    assert recorded["content_type"] == "text/plain"


@pytest.mark.asyncio
async def test_upload_stream_propagates_minio_errors():
    service = StorageService()
    service._bucket_checked = True
    service.client = Mock()
    service.client.put_object = Mock(
        side_effect=S3Error(
            code="SlowDown",
            message="too busy",
            resource="/bucket/object",
            request_id="req-1",
            host_id="host-1",
            response=None,
        )
    )

    with pytest.raises(S3Error):
        await service.upload_stream("rags/test/file.txt", io.BytesIO(b"abcdef"), 6, "text/plain")
