"""Memory API integration tests."""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from app.main import app


@pytest.mark.asyncio
async def test_create_conversation_summary():
    """Test conversation summary creation."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create project and conversation first
        project_response = await client.post("/api/projects", json={"name": "Test Project"}, follow_redirects=True)
        project_id = project_response.json()["id"]

        conv_response = await client.post(
            "/api/conversations",
            json={"project_id": project_id, "title": "Test Conversation"},
            follow_redirects=True
        )
        conversation_id = conv_response.json()["id"]

        # Add a message
        await client.post(
            f"/api/conversations/{conversation_id}/messages",
            json={"role": "user", "content": "Hello"},
            follow_redirects=True
        )

        # Mock the OpenAI call
        with patch("app.services.memory_service.memory_service.summarize_conversation") as mock_summarize:
            mock_summarize.return_value = "Test summary"

            # Create summary
            response = await client.post(f"/api/conversations/{conversation_id}/summarize")

            assert response.status_code == 201
            data = response.json()
            assert data["summary_text"] == "Test summary"
            assert data["conversation_id"] == conversation_id


@pytest.mark.asyncio
async def test_create_project_memory():
    """Test project memory creation."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        project_response = await client.post("/api/projects", json={"name": "Test Project"}, follow_redirects=True)
        project_id = project_response.json()["id"]

        with patch("app.services.memory_service.memory_service.generate_embedding") as mock_embed:
            mock_embed.return_value = [0.1] * 1536

            response = await client.post(
                f"/api/projects/{project_id}/memories",
                json={
                    "memory_type": "fact",
                    "content": "User prefers Python",
                    "memory_metadata": {"source": "conversation"}
                },
                follow_redirects=True
            )

            assert response.status_code == 201
            data = response.json()
            assert data["content"] == "User prefers Python"
            assert data["memory_type"] == "fact"
