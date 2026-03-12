"""Artifact API integration tests."""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from app.main import app


@pytest.mark.asyncio
async def test_get_artifact():
    """Test GET /api/artifacts/{artifact_id}."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create project
        project_response = await client.post("/api/projects", json={"name": "Test Project"}, follow_redirects=True)
        project_id = project_response.json()["id"]

        # Create conversation
        conv_response = await client.post("/api/conversations", json={"project_id": project_id, "title": "Test"}, follow_redirects=True)
        conversation_id = conv_response.json()["id"]

        # Create task
        task_response = await client.post("/api/tasks", json={"conversation_id": conversation_id, "project_id": project_id, "goal": "Test task"}, follow_redirects=True)
        task_id = task_response.json()["id"]

        # Create task run
        run_response = await client.post(f"/api/tasks/{task_id}/runs", json={}, follow_redirects=True)
        run_id = run_response.json()["id"]

        # Mock MinIO operations
        with patch("app.services.storage.storage_service.upload_file", new_callable=AsyncMock) as mock_upload:
            mock_upload.return_value = "test-path"

            # Upload artifact
            files = {"file": ("test.txt", b"test content", "text/plain")}
            upload_response = await client.post(
                f"/api/artifacts/upload?project_id={project_id}&task_run_id={run_id}",
                files=files,
                follow_redirects=True
            )

            if upload_response.status_code == 201:
                artifact_id = upload_response.json()["id"]

                # Get artifact
                response = await client.get(f"/api/artifacts/{artifact_id}")
                assert response.status_code == 200
                assert response.json()["name"] == "test.txt"


@pytest.mark.asyncio
async def test_get_nonexistent_artifact():
    """Test GET /api/artifacts/{artifact_id} with invalid ID."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import uuid
        fake_id = uuid.uuid4()
        response = await client.get(f"/api/artifacts/{fake_id}")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_artifact():
    """Test DELETE /api/artifacts/{artifact_id}."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create project
        project_response = await client.post("/api/projects", json={"name": "Test Project"}, follow_redirects=True)
        project_id = project_response.json()["id"]

        # Create conversation
        conv_response = await client.post("/api/conversations", json={"project_id": project_id, "title": "Test"}, follow_redirects=True)
        conversation_id = conv_response.json()["id"]

        # Create task
        task_response = await client.post("/api/tasks", json={"conversation_id": conversation_id, "project_id": project_id, "goal": "Test task"}, follow_redirects=True)
        task_id = task_response.json()["id"]

        # Create task run
        run_response = await client.post(f"/api/tasks/{task_id}/runs", json={}, follow_redirects=True)
        run_id = run_response.json()["id"]

        with patch("app.services.storage.storage_service.upload_file", new_callable=AsyncMock) as mock_upload, \
             patch("app.services.storage.storage_service.delete_file", new_callable=AsyncMock):
            mock_upload.return_value = "test-path"

            files = {"file": ("test.txt", b"test content", "text/plain")}
            upload_response = await client.post(
                f"/api/artifacts/upload?project_id={project_id}&task_run_id={run_id}",
                files=files,
                follow_redirects=True
            )

            if upload_response.status_code == 201:
                artifact_id = upload_response.json()["id"]
                response = await client.delete(f"/api/artifacts/{artifact_id}")
                assert response.status_code == 204
