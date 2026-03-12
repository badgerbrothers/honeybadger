"""Run API integration tests."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_get_run():
    """Test GET /api/runs/{run_id}."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create project, conversation, task, and run
        project_response = await client.post("/api/projects", json={"name": "Test Project"}, follow_redirects=True)
        project_id = project_response.json()["id"]
        conv_response = await client.post("/api/conversations", json={"project_id": project_id, "title": "Test"}, follow_redirects=True)
        conversation_id = conv_response.json()["id"]
        task_response = await client.post("/api/tasks", json={"conversation_id": conversation_id, "project_id": project_id, "goal": "Test"}, follow_redirects=True)
        task_id = task_response.json()["id"]
        run_response = await client.post(f"/api/tasks/{task_id}/runs", follow_redirects=True)
        run_id = run_response.json()["id"]

        # Test get run
        response = await client.get(f"/api/runs/{run_id}")
        assert response.status_code == 200
        assert response.json()["id"] == run_id


@pytest.mark.asyncio
async def test_get_nonexistent_run():
    """Test GET /api/runs/{run_id} with invalid ID."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import uuid
        fake_id = uuid.uuid4()
        response = await client.get(f"/api/runs/{fake_id}")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_cancel_run():
    """Test POST /api/runs/{run_id}/cancel."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create project, conversation, task, and run
        project_response = await client.post("/api/projects", json={"name": "Test Project"}, follow_redirects=True)
        project_id = project_response.json()["id"]
        conv_response = await client.post("/api/conversations", json={"project_id": project_id, "title": "Test"}, follow_redirects=True)
        conversation_id = conv_response.json()["id"]
        task_response = await client.post("/api/tasks", json={"conversation_id": conversation_id, "project_id": project_id, "goal": "Test"}, follow_redirects=True)
        task_id = task_response.json()["id"]
        run_response = await client.post(f"/api/tasks/{task_id}/runs", follow_redirects=True)
        run_id = run_response.json()["id"]

        # Test cancel run
        response = await client.post(f"/api/runs/{run_id}/cancel")
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"
        assert response.json()["completed_at"] is not None
