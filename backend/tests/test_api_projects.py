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

@pytest.mark.asyncio
async def test_upload_project_file():
    """Test file upload to project."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create project first
        create_response = await client.post("/api/projects", json={"name": "Test Project"})
        project_id = create_response.json()["id"]
        
        # Upload file
        files = {"file": ("test.txt", b"Test file content", "text/plain")}
        response = await client.post(f"/api/projects/{project_id}/files/upload", files=files)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test.txt"
        assert data["size"] == 17
        assert data["project_id"] == project_id

@pytest.mark.asyncio
async def test_upload_invalid_file_type():
    """Test upload with invalid file type."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_response = await client.post("/api/projects", json={"name": "Test Project"})
        project_id = create_response.json()["id"]
        
        files = {"file": ("test.exe", b"data", "application/x-msdownload")}
        response = await client.post(f"/api/projects/{project_id}/files/upload", files=files)
        
        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"]

@pytest.mark.asyncio
async def test_upload_file_too_large():
    """Test upload with file exceeding size limit."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_response = await client.post("/api/projects", json={"name": "Test Project"})
        project_id = create_response.json()["id"]
        
        # Create 51MB file
        large_content = b"x" * (51 * 1024 * 1024)
        files = {"file": ("large.txt", large_content, "text/plain")}
        response = await client.post(f"/api/projects/{project_id}/files/upload", files=files)
        
        assert response.status_code == 413
        assert "too large" in response.json()["detail"]

@pytest.mark.asyncio
async def test_list_project_files():
    """Test listing project files."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_response = await client.post("/api/projects", json={"name": "Test Project"})
        project_id = create_response.json()["id"]
        
        # Upload a file
        files = {"file": ("test.txt", b"content", "text/plain")}
        await client.post(f"/api/projects/{project_id}/files/upload", files=files)
        
        # List files
        response = await client.get(f"/api/projects/{project_id}/files")
        
        assert response.status_code == 200
        files_list = response.json()
        assert len(files_list) == 1
        assert files_list[0]["name"] == "test.txt"

@pytest.mark.asyncio
async def test_delete_project_file():
    """Test deleting project file."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_response = await client.post("/api/projects", json={"name": "Test Project"})
        project_id = create_response.json()["id"]
        
        # Upload a file
        files = {"file": ("test.txt", b"content", "text/plain")}
        upload_response = await client.post(f"/api/projects/{project_id}/files/upload", files=files)
        file_id = upload_response.json()["id"]
        
        # Delete file
        response = await client.delete(f"/api/projects/{project_id}/files/{file_id}")
        
        assert response.status_code == 204

@pytest.mark.asyncio
async def test_upload_to_nonexistent_project():
    """Test upload to non-existent project."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("test.txt", b"content", "text/plain")}
        response = await client.post(
            "/api/projects/00000000-0000-0000-0000-000000000000/files/upload",
            files=files
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
