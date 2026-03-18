"""Tasks API integration tests."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_create_task():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        project_response = await client.post("/api/projects", json={"name": "Test Project"}, follow_redirects=True)
        project_id = project_response.json()["id"]
        conv_response = await client.post("/api/conversations", json={"project_id": project_id, "title": "Test"}, follow_redirects=True)
        conversation_id = conv_response.json()["id"]
        response = await client.post("/api/tasks", json={"conversation_id": conversation_id, "project_id": project_id, "goal": "Test task"}, follow_redirects=True)
        assert response.status_code == 201
        assert response.json()["goal"] == "Test task"

@pytest.mark.asyncio
async def test_list_tasks():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/tasks", follow_redirects=True)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

@pytest.mark.asyncio
async def test_list_tasks_filtered():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        project_response = await client.post("/api/projects", json={"name": "Test Project"}, follow_redirects=True)
        project_id = project_response.json()["id"]
        conv_response = await client.post("/api/conversations", json={"project_id": project_id, "title": "Test"}, follow_redirects=True)
        conversation_id = conv_response.json()["id"]
        await client.post("/api/tasks", json={"conversation_id": conversation_id, "project_id": project_id, "goal": "Test"}, follow_redirects=True)
        response = await client.get(f"/api/tasks?conversation_id={conversation_id}", follow_redirects=True)
        assert response.status_code == 200
        assert len(response.json()) >= 1

@pytest.mark.asyncio
async def test_get_task():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        project_response = await client.post("/api/projects", json={"name": "Test Project"}, follow_redirects=True)
        project_id = project_response.json()["id"]
        conv_response = await client.post("/api/conversations", json={"project_id": project_id, "title": "Test"}, follow_redirects=True)
        conversation_id = conv_response.json()["id"]
        create_response = await client.post("/api/tasks", json={"conversation_id": conversation_id, "project_id": project_id, "goal": "Test"}, follow_redirects=True)
        task_id = create_response.json()["id"]
        response = await client.get(f"/api/tasks/{task_id}")
        assert response.status_code == 200
        assert response.json()["id"] == task_id

@pytest.mark.asyncio
async def test_update_task():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        project_response = await client.post("/api/projects", json={"name": "Test Project"}, follow_redirects=True)
        project_id = project_response.json()["id"]
        conv_response = await client.post("/api/conversations", json={"project_id": project_id, "title": "Test"}, follow_redirects=True)
        conversation_id = conv_response.json()["id"]
        create_response = await client.post("/api/tasks", json={"conversation_id": conversation_id, "project_id": project_id, "goal": "Old"}, follow_redirects=True)
        task_id = create_response.json()["id"]
        response = await client.patch(f"/api/tasks/{task_id}", json={"goal": "New"})
        assert response.status_code == 200
        assert response.json()["goal"] == "New"

@pytest.mark.asyncio
async def test_delete_task():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        project_response = await client.post("/api/projects", json={"name": "Test Project"}, follow_redirects=True)
        project_id = project_response.json()["id"]
        conv_response = await client.post("/api/conversations", json={"project_id": project_id, "title": "Test"}, follow_redirects=True)
        conversation_id = conv_response.json()["id"]
        create_response = await client.post("/api/tasks", json={"conversation_id": conversation_id, "project_id": project_id, "goal": "Test"}, follow_redirects=True)
        task_id = create_response.json()["id"]
        response = await client.delete(f"/api/tasks/{task_id}")
        assert response.status_code == 204

@pytest.mark.asyncio
async def test_get_nonexistent_task():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/tasks/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

@pytest.mark.asyncio
async def test_create_task_run():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        project_response = await client.post("/api/projects", json={"name": "Test Project"}, follow_redirects=True)
        project_id = project_response.json()["id"]
        conv_response = await client.post("/api/conversations", json={"project_id": project_id, "title": "Test"}, follow_redirects=True)
        conversation_id = conv_response.json()["id"]
        task_response = await client.post("/api/tasks", json={"conversation_id": conversation_id, "project_id": project_id, "goal": "Test"}, follow_redirects=True)
        task_id = task_response.json()["id"]
        response = await client.post(f"/api/tasks/{task_id}/runs", follow_redirects=True)
        assert response.status_code == 201
        assert response.json()["status"] == "pending"

@pytest.mark.asyncio
async def test_list_task_runs():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        project_response = await client.post("/api/projects", json={"name": "Test Project"}, follow_redirects=True)
        project_id = project_response.json()["id"]
        conv_response = await client.post("/api/conversations", json={"project_id": project_id, "title": "Test"}, follow_redirects=True)
        conversation_id = conv_response.json()["id"]
        task_response = await client.post("/api/tasks", json={"conversation_id": conversation_id, "project_id": project_id, "goal": "Test"}, follow_redirects=True)
        task_id = task_response.json()["id"]
        await client.post(f"/api/tasks/{task_id}/runs", follow_redirects=True)
        response = await client.get(f"/api/tasks/{task_id}/runs", follow_redirects=True)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_update_task_queue_status():
    """Test updating task queue status."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        project_response = await client.post("/api/projects", json={"name": "Test Project"}, follow_redirects=True)
        project_id = project_response.json()["id"]
        conv_response = await client.post(
            "/api/conversations",
            json={"project_id": project_id, "title": "Test"},
            follow_redirects=True,
        )
        conversation_id = conv_response.json()["id"]
        task_response = await client.post(
            "/api/tasks",
            json={"conversation_id": conversation_id, "project_id": project_id, "goal": "Queue test"},
            follow_redirects=True,
        )
        task_id = task_response.json()["id"]

        response = await client.patch(
            f"/api/tasks/{task_id}/queue-status?queue_status=queued",
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert response.json()["queue_status"] == "queued"


@pytest.mark.asyncio
async def test_get_kanban_board():
    """Test fetching kanban board data grouped by status."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        project_response = await client.post("/api/projects", json={"name": "Test Project"}, follow_redirects=True)
        project_id = project_response.json()["id"]
        conv_response = await client.post(
            "/api/conversations",
            json={"project_id": project_id, "title": "Test"},
            follow_redirects=True,
        )
        conversation_id = conv_response.json()["id"]

        scheduled_task = await client.post(
            "/api/tasks",
            json={"conversation_id": conversation_id, "project_id": project_id, "goal": "Scheduled"},
            follow_redirects=True,
        )
        queued_task = await client.post(
            "/api/tasks",
            json={"conversation_id": conversation_id, "project_id": project_id, "goal": "Queued"},
            follow_redirects=True,
        )
        done_task = await client.post(
            "/api/tasks",
            json={"conversation_id": conversation_id, "project_id": project_id, "goal": "Done"},
            follow_redirects=True,
        )

        await client.patch(
            f"/api/tasks/{queued_task.json()['id']}/queue-status?queue_status=queued",
            follow_redirects=True,
        )
        await client.patch(
            f"/api/tasks/{done_task.json()['id']}/queue-status?queue_status=done",
            follow_redirects=True,
        )

        response = await client.get(f"/api/tasks/kanban?project_id={project_id}", follow_redirects=True)
        assert response.status_code == 200
        data = response.json()
        assert len(data["scheduled"]) == 1
        assert len(data["queued"]) == 1
        assert len(data["done"]) == 1
        assert data["scheduled"][0]["id"] == scheduled_task.json()["id"]
