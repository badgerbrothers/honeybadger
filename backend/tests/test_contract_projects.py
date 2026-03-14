"""Contract tests for project routes without a live database."""
from unittest.mock import AsyncMock, Mock

import pytest

from app.database import get_db
from app.main import app


class _ScalarResult:
    """Minimal async result wrapper for scalar queries."""

    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        return self

    def all(self):
        return self._value


@pytest.mark.asyncio
async def test_contract_list_projects(unit_app_client, fake_project_factory):
    """Projects list route should serialize project-like objects via dependency overrides."""
    project = fake_project_factory()
    session = AsyncMock()
    session.execute.return_value = _ScalarResult([project])

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    response = await unit_app_client.get("/api/projects/")

    assert response.status_code == 200
    assert response.json()[0]["name"] == "Test Project"


@pytest.mark.asyncio
async def test_contract_create_project(unit_app_client, fake_project_factory):
    """Projects create route should return the newly created project object without a live DB."""
    project = fake_project_factory(name="Created Project")
    session = AsyncMock()
    session.add = Mock()
    session.commit.return_value = None
    session.refresh = AsyncMock(side_effect=lambda obj: obj.__dict__.update(project.__dict__))

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    response = await unit_app_client.post(
        "/api/projects/",
        json={"name": "Created Project", "description": "Created in unit test"},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Created Project"


@pytest.mark.asyncio
async def test_contract_get_project_not_found(unit_app_client):
    """Projects detail route should return 404 when the dependency override yields no record."""
    session = AsyncMock()
    session.execute.return_value = _ScalarResult(None)

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    response = await unit_app_client.get("/api/projects/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
