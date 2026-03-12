"""Test configuration and fixtures."""
import pytest
import asyncio

@pytest.fixture(scope="session", autouse=True)
def init_test_db():
    """Initialize database tables before tests."""
    from app.database import init_db
    asyncio.run(init_db())

@pytest.fixture(scope="function")
def event_loop():
    """Create a new event loop for each test."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
def reset_db():
    """Reset database connections between tests."""
    yield
    # After each test, dispose the engine to close all connections
    from app.database import engine
    asyncio.run(engine.dispose())
