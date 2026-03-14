"""Contract tests for execution-oriented APIs without a live database."""
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
import uuid

import pytest

from app.database import get_db
from app.main import app
from app.models.artifact import ArtifactType


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


def _fake_run(**kwargs):
    now = datetime.now(UTC)
    defaults = {
        "id": kwargs.pop("id", uuid.uuid4()),
        "task_id": kwargs.pop("task_id", uuid.uuid4()),
        "status": kwargs.pop("status", "pending"),
        "started_at": kwargs.pop("started_at", None),
        "completed_at": kwargs.pop("completed_at", None),
        "error_message": kwargs.pop("error_message", None),
        "logs": kwargs.pop("logs", []),
        "working_memory": kwargs.pop("working_memory", None),
        "created_at": kwargs.pop("created_at", now),
        "updated_at": kwargs.pop("updated_at", now),
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _fake_artifact(**kwargs):
    now = datetime.now(UTC)
    defaults = {
        "id": kwargs.pop("id", uuid.uuid4()),
        "project_id": kwargs.pop("project_id", uuid.uuid4()),
        "task_run_id": kwargs.pop("task_run_id", uuid.uuid4()),
        "name": kwargs.pop("name", "result.txt"),
        "artifact_type": kwargs.pop("artifact_type", ArtifactType.FILE),
        "storage_path": kwargs.pop("storage_path", "p/r/a/result.txt"),
        "size": kwargs.pop("size", 42),
        "mime_type": kwargs.pop("mime_type", "text/plain"),
        "created_at": kwargs.pop("created_at", now),
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


@pytest.mark.asyncio
async def test_contract_retry_task_creates_run(unit_app_client):
    """Retry endpoint should delegate to run creation and return a run payload."""
    task_id = uuid.uuid4()
    run_id = uuid.uuid4()
    fake_run = _fake_run(id=run_id, task_id=task_id)

    with patch("app.routers.tasks.create_task_run", new=AsyncMock(return_value=fake_run)):
        response = await unit_app_client.post(f"/api/tasks/{task_id}/retry")

    assert response.status_code == 201
    payload = response.json()
    assert payload["id"] == str(run_id)
    assert payload["task_id"] == str(task_id)


@pytest.mark.asyncio
async def test_contract_ingest_run_event_appends_logs(unit_app_client):
    """Run event ingest should append logs and return accepted."""
    run_id = uuid.uuid4()
    fake_run = _fake_run(id=run_id, logs=[{"type": "run_started"}])
    session = AsyncMock()
    session.execute.return_value = _ScalarResult(fake_run)

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    with patch("app.routers.runs.broadcaster.broadcast", new=AsyncMock()) as mock_broadcast:
        response = await unit_app_client.post(
            f"/api/runs/{run_id}/events",
            json={"type": "step", "message": "sandbox_created"},
        )

    assert response.status_code == 202
    assert response.json() == {"accepted": True}
    assert len(fake_run.logs) == 2
    assert fake_run.logs[-1]["type"] == "step"
    session.commit.assert_called_once()
    mock_broadcast.assert_awaited_once()


@pytest.mark.asyncio
async def test_contract_list_artifacts_endpoints(unit_app_client):
    """Artifact list routes should serialize artifact-like objects."""
    project_id = uuid.uuid4()
    run_id = uuid.uuid4()
    artifact = _fake_artifact(project_id=project_id, task_run_id=run_id)
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_ScalarResult([artifact]))

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    by_project = await unit_app_client.get(f"/api/artifacts/list/project/{project_id}")
    assert by_project.status_code == 200
    assert by_project.json()[0]["project_id"] == str(project_id)

    by_run = await unit_app_client.get(f"/api/artifacts/list/run/{run_id}")
    assert by_run.status_code == 200
    assert by_run.json()[0]["task_run_id"] == str(run_id)


@pytest.mark.asyncio
async def test_contract_save_artifact_to_project(unit_app_client):
    """Saving artifact to project should create a project node and copy in storage."""
    artifact = _fake_artifact()
    session = AsyncMock()
    session.execute.return_value = _ScalarResult(artifact)
    session.add = Mock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    with patch("app.routers.artifacts.storage_service.copy_file", new=AsyncMock()) as mock_copy:
        response = await unit_app_client.post(f"/api/artifacts/{artifact.id}/save-to-project")

    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == str(artifact.project_id)
    assert payload["name"] == artifact.name
    mock_copy.assert_awaited_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_contract_rag_index_and_search(unit_app_client):
    """RAG routes should delegate to rag service contract methods."""
    project_id = uuid.uuid4()
    node_id = uuid.uuid4()
    job_id = uuid.uuid4()
    fake_job = SimpleNamespace(id=job_id, status=SimpleNamespace(value="pending"))

    with patch("app.routers.rag.rag_service.requeue_node", new=AsyncMock(return_value=fake_job)) as mock_requeue:
        index_response = await unit_app_client.post(
            f"/api/projects/{project_id}/documents/index",
            json={"node_id": str(node_id)},
        )
    assert index_response.status_code == 200
    assert index_response.json()["job_id"] == str(job_id)
    mock_requeue.assert_awaited_once()

    chunks = [{"id": 1, "content": "abc", "file_path": "f.md", "chunk_index": 0, "similarity": 0.9, "metadata": {}}]
    with patch("app.routers.rag.rag_service.search", new=AsyncMock(return_value=chunks)) as mock_search:
        search_response = await unit_app_client.post(
            f"/api/projects/{project_id}/search",
            json={"query": "what is this", "top_k": 3, "threshold": 0.5},
        )
    assert search_response.status_code == 200
    assert search_response.json()["chunks"] == chunks
    mock_search.assert_awaited_once()

