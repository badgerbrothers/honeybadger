"""RAG API integration tests."""
import io
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_index_document():
    """Test document indexing endpoint with current request shape."""
    project_id = str(uuid.uuid4())
    node_id = str(uuid.uuid4())
    fake_job_id = str(uuid.uuid4())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.routers.rag.rag_service.requeue_node", new=AsyncMock(return_value=type("Job", (), {"id": uuid.UUID(fake_job_id), "status": type("S", (), {"value": "pending"})()})())):
            response = await client.post(
                f"/api/projects/{project_id}/documents/index",
                json={"node_id": node_id}
            )
    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == project_id
    assert payload["node_id"] == node_id
    assert payload["status"] == "pending"


@pytest.mark.asyncio
async def test_index_document_not_found():
    """Test index endpoint returns 404 when node does not exist."""
    project_id = str(uuid.uuid4())
    node_id = str(uuid.uuid4())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.routers.rag.rag_service.requeue_node", new=AsyncMock(return_value=None)):
            response = await client.post(
                f"/api/projects/{project_id}/documents/index",
                json={"node_id": node_id}
            )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_search_chunks():
    """Test search endpoint delegates to rag service."""
    project_id = str(uuid.uuid4())
    fake_chunks = [{"id": 1, "content": "sample", "file_path": "a.md", "chunk_index": 0, "similarity": 0.9, "metadata": {}}]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.routers.rag.rag_service.search", new=AsyncMock(return_value=fake_chunks)):
            response = await client.post(
                f"/api/projects/{project_id}/search",
                json={"query": "test", "top_k": 5, "threshold": 0.5}
            )
    assert response.status_code == 200
    assert response.json()["chunks"] == fake_chunks


@pytest.mark.asyncio
async def test_list_chunks():
    """Test listing chunks endpoint."""
    project_id = str(uuid.uuid4())
    fake_chunks = [{"id": 1, "file_path": "a.md", "chunk_index": 0, "token_count": 10}]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.routers.rag.rag_service.list_chunks", new=AsyncMock(return_value=fake_chunks)):
            response = await client.get(f"/api/projects/{project_id}/chunks")
    assert response.status_code == 200
    assert response.json() == fake_chunks


@pytest.mark.asyncio
async def test_delete_chunk():
    """Test deleting chunk endpoint."""
    project_id = str(uuid.uuid4())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.routers.rag.rag_service.delete_chunk", new=AsyncMock(return_value=True)):
            response = await client.delete(f"/api/projects/{project_id}/chunks/1")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_project_upload_schedules_rag_indexing():
    """Project file upload should schedule an indexing job."""
    project_id = str(uuid.uuid4())
    fake_job = type("Job", (), {"id": uuid.uuid4(), "status": type("S", (), {"value": "pending"})()})()
    file_content = b"# test\nhello"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        project_response = await client.post("/api/projects", json={"name": "RAG Test Project"}, follow_redirects=True)
        assert project_response.status_code == 201
        project_id = project_response.json()["id"]

        files = {"file": ("test.md", io.BytesIO(file_content), "text/markdown")}
        with patch("app.routers.projects.rag_service.schedule_indexing", new=AsyncMock(return_value=fake_job)) as mock_schedule:
            response = await client.post(
                f"/api/projects/{project_id}/files/upload",
                files=files,
                follow_redirects=True,
            )

    assert response.status_code == 201
    mock_schedule.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_validation_error_for_missing_query():
    """Search endpoint should reject invalid payload."""
    project_id = str(uuid.uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            f"/api/projects/{project_id}/search",
            json={"top_k": 5}
        )
    assert response.status_code == 422
