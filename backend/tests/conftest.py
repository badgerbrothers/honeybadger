"""Test configuration and fixtures."""
import pytest_asyncio
from unittest.mock import AsyncMock, patch

@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_test_db():
    """Initialize database tables before tests."""
    from app.database import init_db
    await init_db()

@pytest_asyncio.fixture(autouse=True)
def mock_storage_service():
    """Mock storage service for all tests."""
    with patch("app.services.storage.storage_service.upload_file", new_callable=AsyncMock) as mock_upload, \
         patch("app.services.storage.storage_service.delete_file", new_callable=AsyncMock) as mock_delete:
        mock_upload.return_value = None
        mock_delete.return_value = None
        yield {"upload": mock_upload, "delete": mock_delete}
