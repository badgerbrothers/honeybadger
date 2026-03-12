"""Test configuration and fixtures."""
import pytest
import pytest_asyncio

@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_test_db():
    """Initialize database tables before tests."""
    from app.database import init_db
    await init_db()

@pytest_asyncio.fixture(scope="function", autouse=True)
async def cleanup_db():
    """Cleanup database connections after each test."""
    yield
    from app.database import engine
    await engine.dispose()
