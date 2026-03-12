"""RAG API integration tests."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_index_document():
    """Test document indexing endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/projects/test-proj/documents/index",
            json={"file_path": "test.txt", "content": "sample content"}
        )
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_search_chunks():
    """Test search endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/projects/test-proj/search",
            json={"query": "test", "top_k": 5}
        )
        assert response.status_code == 200
        assert "chunks" in response.json()


@pytest.mark.asyncio
async def test_list_chunks():
    """Test listing chunks endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/projects/test-proj/chunks")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
