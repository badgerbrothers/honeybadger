"""Conversations API integration tests."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_create_conversation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        project_response = await client.post("/api/projects", json={"name": "Test Project"}, follow_redirects=True)
        project_id = project_response.json()["id"]
        response = await client.post("/api/conversations", json={"project_id": project_id, "title": "Test Conversation"}, follow_redirects=True)
        assert response.status_code == 201
        assert response.json()["title"] == "Test Conversation"

@pytest.mark.asyncio
async def test_list_conversations():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/conversations", follow_redirects=True)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_list_conversations_filtered():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        project_response = await client.post("/api/projects", json={"name": "Test Project"}, follow_redirects=True)
        project_id = project_response.json()["id"]
        await client.post("/api/conversations", json={"project_id": project_id, "title": "Test"}, follow_redirects=True)
        response = await client.get(f"/api/conversations?project_id={project_id}", follow_redirects=True)
        assert response.status_code == 200
        assert len(response.json()) >= 1

@pytest.mark.asyncio
async def test_get_conversation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        project_response = await client.post("/api/projects", json={"name": "Test Project"}, follow_redirects=True)
        project_id = project_response.json()["id"]
        create_response = await client.post("/api/conversations", json={"project_id": project_id, "title": "Test"}, follow_redirects=True)
        conversation_id = create_response.json()["id"]
        response = await client.get(f"/api/conversations/{conversation_id}")
        assert response.status_code == 200
        assert response.json()["id"] == conversation_id

@pytest.mark.asyncio
async def test_update_conversation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        project_response = await client.post("/api/projects", json={"name": "Test Project"}, follow_redirects=True)
        project_id = project_response.json()["id"]
        create_response = await client.post("/api/conversations", json={"project_id": project_id, "title": "Old"}, follow_redirects=True)
        conversation_id = create_response.json()["id"]
        response = await client.patch(f"/api/conversations/{conversation_id}", json={"title": "New"})
        assert response.status_code == 200
        assert response.json()["title"] == "New"

@pytest.mark.asyncio
async def test_delete_conversation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        project_response = await client.post("/api/projects", json={"name": "Test Project"}, follow_redirects=True)
        project_id = project_response.json()["id"]
        create_response = await client.post("/api/conversations", json={"project_id": project_id, "title": "Test"}, follow_redirects=True)
        conversation_id = create_response.json()["id"]
        response = await client.delete(f"/api/conversations/{conversation_id}")
        assert response.status_code == 204

@pytest.mark.asyncio
async def test_get_nonexistent_conversation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/conversations/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

@pytest.mark.asyncio
async def test_add_message_to_conversation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        project_response = await client.post("/api/projects", json={"name": "Test Project"}, follow_redirects=True)
        project_id = project_response.json()["id"]
        conv_response = await client.post("/api/conversations", json={"project_id": project_id, "title": "Test"}, follow_redirects=True)
        conversation_id = conv_response.json()["id"]
        response = await client.post(f"/api/conversations/{conversation_id}/messages", json={"role": "user", "content": "Hello"}, follow_redirects=True)
        assert response.status_code == 201
        assert response.json()["content"] == "Hello"

@pytest.mark.asyncio
async def test_list_messages():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        project_response = await client.post("/api/projects", json={"name": "Test Project"}, follow_redirects=True)
        project_id = project_response.json()["id"]
        conv_response = await client.post("/api/conversations", json={"project_id": project_id, "title": "Test"}, follow_redirects=True)
        conversation_id = conv_response.json()["id"]
        await client.post(f"/api/conversations/{conversation_id}/messages", json={"role": "user", "content": "Hello"}, follow_redirects=True)
        response = await client.get(f"/api/conversations/{conversation_id}/messages", follow_redirects=True)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
