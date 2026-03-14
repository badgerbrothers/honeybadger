"""Test configuration and fixtures."""
import os
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


INTEGRATION_TEST_DB = os.getenv("TEST_DATABASE_URL")


def pytest_collection_modifyitems(config, items):
    """Skip DB-backed API tests unless an explicit integration database is configured."""
    if INTEGRATION_TEST_DB:
        return

    skip_integration = pytest.mark.skip(
        reason="Integration database not configured. Set TEST_DATABASE_URL to run DB-backed API tests.",
    )
    for item in items:
        path = str(item.path)
        if "backend\\tests\\test_api_" in path and "contract" not in path:
            item.add_marker(skip_integration)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_test_db():
    """Initialize database tables before tests."""
    if not INTEGRATION_TEST_DB:
        return
    from app.database import init_db
    await init_db()


@pytest_asyncio.fixture
async def unit_app_client():
    """ASGI client for dependency-overridden contract tests."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def fake_project_factory():
    """Factory for lightweight project-like response objects."""

    def _factory(**kwargs):
        now = datetime.now(UTC)
        defaults = {
            "id": kwargs.pop("id", "11111111-1111-1111-1111-111111111111"),
            "name": kwargs.pop("name", "Test Project"),
            "description": kwargs.pop("description", "Test"),
            "created_at": kwargs.pop("created_at", now),
            "updated_at": kwargs.pop("updated_at", now),
        }
        defaults.update(kwargs)
        return SimpleNamespace(**defaults)

    return _factory


@pytest_asyncio.fixture(autouse=True)
def mock_storage_service():
    """Mock storage service for all tests."""
    with patch("app.services.storage.storage_service.upload_file", new_callable=AsyncMock) as mock_upload, \
         patch("app.services.storage.storage_service.delete_file", new_callable=AsyncMock) as mock_delete:
        mock_upload.return_value = None
        mock_delete.return_value = None
        yield {"upload": mock_upload, "delete": mock_delete}
