"""Projects API integration tests."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_create_project():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/projects", json={"name": "Test Project", "description": "Test"}, follow_redirects=True)
        assert response.status_code == 201
        assert response.json()["name"] == "Test Project"

@pytest.mark.asyncio
async def test_list_projects():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/projects", follow_redirects=True)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_get_nonexistent_project():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/projects/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
