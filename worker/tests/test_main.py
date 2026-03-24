"""Tests for worker main loop."""
import pytest
import uuid
import types
import sys
from unittest.mock import AsyncMock, Mock, patch


@pytest.mark.asyncio
async def test_get_next_pending_task_returns_none_when_empty():
    """Test that get_next_pending_task returns None when no tasks available."""
    from worker.main import get_next_pending_task

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=None)))

    result = await get_next_pending_task(mock_session)

    assert result is None


@pytest.mark.asyncio
async def test_get_next_pending_task_claims_task():
    """Test that get_next_pending_task claims a PENDING task."""
    from worker.main import get_next_pending_task
    from db_models import TaskRun, TaskStatus

    mock_task_run = Mock(spec=TaskRun)
    mock_task_run.id = uuid.uuid4()
    mock_task_run.status = TaskStatus.PENDING
    mock_task_run.logs = None

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=mock_task_run)))
    mock_session.commit = AsyncMock()

    result = await get_next_pending_task(mock_session)

    assert result == mock_task_run
    assert result.status == TaskStatus.RUNNING
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_claim_task_run_by_id_claims_pending_run():
    """Specific pending TaskRun should transition to RUNNING exactly once."""
    from worker.main import claim_task_run_by_id
    from db_models import TaskRun, TaskStatus

    task_run_id = uuid.uuid4()
    mock_task_run = Mock(spec=TaskRun)
    mock_task_run.id = task_run_id
    mock_task_run.status = TaskStatus.PENDING
    mock_task_run.started_at = None
    mock_task_run.logs = None

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=mock_task_run)))
    mock_session.commit = AsyncMock()

    result = await claim_task_run_by_id(mock_session, task_run_id)

    assert result == mock_task_run
    assert mock_task_run.status == TaskStatus.RUNNING
    assert mock_task_run.started_at is not None
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_claim_task_run_by_id_skips_non_pending_run():
    """Repeated delivery should not reclaim a non-pending TaskRun."""
    from worker.main import claim_task_run_by_id
    from db_models import TaskRun, TaskStatus

    task_run_id = uuid.uuid4()
    mock_task_run = Mock(spec=TaskRun)
    mock_task_run.id = task_run_id
    mock_task_run.status = TaskStatus.COMPLETED

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=mock_task_run)))
    mock_session.commit = AsyncMock()

    result = await claim_task_run_by_id(mock_session, task_run_id)

    assert result is None
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_execute_task_run_success():
    """Test successful task execution."""
    from worker.main import execute_task_run
    from db_models import Task, TaskRun, TaskStatus
    task_run_id = uuid.uuid4()
    task_id = uuid.uuid4()

    mock_task = Mock(spec=Task)
    mock_task.id = task_id
    mock_task.goal = "test goal"
    mock_task.model = None
    mock_task.skill = None
    mock_task.current_run_id = task_run_id

    mock_task_run = Mock(spec=TaskRun)
    mock_task_run.id = task_run_id
    mock_task_run.task_id = task_id
    mock_task_run.status = TaskStatus.RUNNING
    mock_task_run.logs = None

    mock_session = AsyncMock()

    # Mock database queries
    mock_session.execute = AsyncMock(side_effect=[
        Mock(scalar_one=Mock(return_value=mock_task_run)),
        Mock(scalar_one=Mock(return_value=mock_task)),
        Mock(scalar_one_or_none=Mock(return_value=None)),
    ])
    mock_session.add = Mock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    # Mock sandbox
    fake_sandbox_module = types.ModuleType("sandbox.manager")
    mock_sandbox_cls = Mock()
    mock_sandbox = AsyncMock()
    mock_sandbox.create = AsyncMock(return_value="container_123")
    mock_sandbox.destroy = AsyncMock()
    mock_sandbox_cls.return_value = mock_sandbox
    fake_sandbox_module.SandboxManager = mock_sandbox_cls

    with patch.dict(sys.modules, {"sandbox.manager": fake_sandbox_module}), \
         patch('worker.main.BackendClient') as mock_backend_client_cls, \
         patch('worker.main.retrieve_project_context', new=AsyncMock(return_value=None)):
        mock_backend_client = AsyncMock()
        mock_backend_client.emit_run_event = AsyncMock()
        mock_backend_client_cls.return_value = mock_backend_client

        # Mock model provider
        with patch('worker.main.settings.default_main_model', 'gpt-5.3-codex'), \
             patch('worker.main.create_model_provider') as mock_model:
            mock_model.return_value = Mock()

            # Mock tools
            with patch('worker.main.get_all_tools') as mock_tools:
                mock_tools.return_value = []

                # Mock agent
                with patch('worker.main.Agent') as mock_agent_cls:
                    mock_agent = AsyncMock()
                    mock_agent.run = AsyncMock(return_value="test result")
                    mock_agent_cls.return_value = mock_agent

                    await execute_task_run(task_run_id, mock_session)

                    assert mock_task_run.status == TaskStatus.COMPLETED
                    assert mock_sandbox.destroy.called
                    _, kwargs = mock_model.call_args
                    assert kwargs["model"] == "gpt-5.3-codex"


@pytest.mark.asyncio
async def test_execute_task_run_failure_updates_status():
    """Test that failures are properly recorded."""
    from worker.main import execute_task_run
    from db_models import Task, TaskRun, TaskStatus

    task_run_id = uuid.uuid4()
    task_id = uuid.uuid4()

    mock_task = Mock(spec=Task)
    mock_task.id = task_id
    mock_task.goal = "test goal"
    mock_task.model = None
    mock_task.skill = None
    mock_task.current_run_id = task_run_id

    mock_task_run = Mock(spec=TaskRun)
    mock_task_run.id = task_run_id
    mock_task_run.task_id = task_id
    mock_task_run.status = TaskStatus.RUNNING
    mock_task_run.logs = None

    mock_session = AsyncMock()

    # Mock database queries to return task_run and task, then fail on sandbox creation
    mock_session.execute = AsyncMock(side_effect=[
        Mock(scalar_one=Mock(return_value=mock_task_run)),
        Mock(scalar_one=Mock(return_value=mock_task)),
        Mock(scalar_one_or_none=Mock(return_value=None)),
    ])
    mock_session.add = Mock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    # Mock sandbox to fail
    fake_sandbox_module = types.ModuleType("sandbox.manager")
    mock_sandbox_cls = Mock()
    mock_sandbox = AsyncMock()
    mock_sandbox.create = AsyncMock(side_effect=Exception("Sandbox creation failed"))
    mock_sandbox_cls.return_value = mock_sandbox
    fake_sandbox_module.SandboxManager = mock_sandbox_cls

    with patch.dict(sys.modules, {"sandbox.manager": fake_sandbox_module}), \
         patch('worker.main.BackendClient') as mock_backend_client_cls:
        mock_backend_client = AsyncMock()
        mock_backend_client.emit_run_event = AsyncMock()
        mock_backend_client_cls.return_value = mock_backend_client

        await execute_task_run(task_run_id, mock_session)

        assert mock_task_run.status == TaskStatus.FAILED
        assert mock_task_run.error_message == "Sandbox creation failed"


@pytest.mark.asyncio
async def test_execute_task_run_skips_when_sandbox_session_exists():
    """Duplicate execution should not create a second sandbox session."""
    from worker.main import execute_task_run
    from db_models import SandboxSession, Task, TaskRun, TaskStatus

    task_run_id = uuid.uuid4()
    task_id = uuid.uuid4()

    mock_task = Mock(spec=Task)
    mock_task.id = task_id
    mock_task.goal = "test goal"
    mock_task.model = None
    mock_task.skill = None
    mock_task.current_run_id = task_run_id

    mock_task_run = Mock(spec=TaskRun)
    mock_task_run.id = task_run_id
    mock_task_run.task_id = task_id
    mock_task_run.status = TaskStatus.RUNNING
    mock_task_run.logs = None

    mock_sandbox_session = Mock(spec=SandboxSession)
    mock_sandbox_session.container_id = "container_existing"
    mock_sandbox_session.terminated_at = None

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=[
        Mock(scalar_one=Mock(return_value=mock_task_run)),
        Mock(scalar_one=Mock(return_value=mock_task)),
        Mock(scalar_one_or_none=Mock(return_value=mock_sandbox_session)),
    ])
    mock_session.commit = AsyncMock()

    fake_sandbox_module = types.ModuleType("sandbox.manager")
    mock_sandbox_cls = Mock()
    fake_sandbox_module.SandboxManager = mock_sandbox_cls

    with patch.dict(sys.modules, {"sandbox.manager": fake_sandbox_module}):
        await execute_task_run(task_run_id, mock_session)

    mock_sandbox_cls.assert_not_called()


@pytest.mark.asyncio
async def test_get_next_pending_index_job_claims_job():
    """Test that get_next_pending_index_job claims a PENDING index job."""
    from worker.main import get_next_pending_index_job
    from db_models import DocumentIndexStatus

    mock_job = Mock()
    mock_job.id = uuid.uuid4()
    mock_job.status = DocumentIndexStatus.PENDING

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=mock_job)))
    mock_session.commit = AsyncMock()

    result = await get_next_pending_index_job(mock_session)

    assert result == mock_job
    assert result.status == DocumentIndexStatus.RUNNING
    assert result.started_at is not None
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_execute_document_index_job_success():
    """Document index job should download, index and mark job completed."""
    from worker.main import execute_document_index_job
    from db_models import DocumentIndexStatus

    job_id = uuid.uuid4()
    project_id = uuid.uuid4()
    node_id = uuid.uuid4()
    mock_job = Mock()
    mock_job.id = job_id
    mock_job.project_id = project_id
    mock_job.project_node_id = node_id
    mock_job.storage_path = "projects/p1/file.md"
    mock_job.file_name = "file.md"
    mock_job.status = DocumentIndexStatus.RUNNING

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=Mock(scalar_one=Mock(return_value=mock_job)))
    mock_session.commit = AsyncMock()

    fake_indexer_module = types.ModuleType("rag.indexer")
    fake_embeddings_module = types.ModuleType("rag.embeddings")
    mock_indexer_cls = Mock()
    mock_indexer = AsyncMock()
    mock_indexer.index_document = AsyncMock(return_value=7)
    mock_indexer_cls.return_value = mock_indexer
    fake_indexer_module.DocumentIndexer = mock_indexer_cls
    fake_embeddings_module.EmbeddingService = Mock(return_value=Mock())

    with patch.dict(sys.modules, {"rag.indexer": fake_indexer_module, "rag.embeddings": fake_embeddings_module}), \
         patch("worker.main.settings.openai_api_key", "test-key"), \
         patch("worker.main.storage_client.download_file", new=AsyncMock(return_value=b"hello")):
        await execute_document_index_job(job_id, mock_session)

    assert mock_job.status == DocumentIndexStatus.COMPLETED
    assert mock_job.chunk_count == 7
    assert mock_job.completed_at is not None
    assert mock_session.commit.await_count >= 1


@pytest.mark.asyncio
async def test_execute_document_index_job_fails_without_openai_key():
    """Document index job should fail fast when OPENAI_API_KEY is missing."""
    from worker.main import execute_document_index_job
    from db_models import DocumentIndexStatus

    job_id = uuid.uuid4()
    project_id = uuid.uuid4()
    node_id = uuid.uuid4()
    mock_job = Mock()
    mock_job.id = job_id
    mock_job.project_id = project_id
    mock_job.project_node_id = node_id
    mock_job.storage_path = "projects/p1/file.md"
    mock_job.file_name = "file.md"
    mock_job.status = DocumentIndexStatus.RUNNING

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=Mock(scalar_one=Mock(return_value=mock_job)))
    mock_session.commit = AsyncMock()

    with patch("worker.main.settings.openai_api_key", None), \
         patch("worker.main.storage_client.download_file", new=AsyncMock()) as mock_download:
        await execute_document_index_job(job_id, mock_session)

    assert mock_job.status == DocumentIndexStatus.FAILED
    assert "OPENAI_API_KEY" in (mock_job.error_message or "")
    mock_download.assert_not_called()


@pytest.mark.asyncio
async def test_upload_artifact_from_tool_result_emits_artifact_event():
    """Helper should emit artifact_created event when upload succeeds."""
    from worker.main import _upload_artifact_from_tool_result

    task_run = Mock()
    task_run.id = uuid.uuid4()
    events = []

    def schedule_event(event_type: str, **payload):
        events.append((event_type, payload))

    fake_upload = {"id": "a1", "name": "result.txt", "artifact_type": "file"}
    with patch("worker.main.upload_artifact_candidate", new=AsyncMock(return_value=fake_upload)):
        await _upload_artifact_from_tool_result(
            backend_client=Mock(),
            task_run=task_run,
            project_id=uuid.uuid4(),
            metadata={"artifact": {"path": "x"}},
            schedule_event=schedule_event,
        )

    assert events
    assert events[0][0] == "artifact_created"
    assert events[0][1]["artifact_id"] == "a1"


@pytest.mark.asyncio
async def test_retrieve_project_context_skips_when_rag_not_selected():
    """No RAG selected should skip retriever entirely."""
    from worker.main import retrieve_project_context

    mock_task = Mock()
    mock_task.goal = "test goal"
    mock_task.project_id = uuid.uuid4()
    mock_task.rag_collection_id = None

    mock_task_run = Mock()
    mock_session = AsyncMock()

    fake_embeddings_module = types.ModuleType("rag.embeddings")
    fake_retriever_module = types.ModuleType("rag.retriever")
    fake_embeddings_module.EmbeddingService = Mock()
    retriever_cls = Mock()
    fake_retriever_module.DocumentRetriever = retriever_cls

    with patch("worker.main.settings.openai_api_key", "test-key"), patch.dict(
        sys.modules,
        {"rag.embeddings": fake_embeddings_module, "rag.retriever": fake_retriever_module},
    ):
        result = await retrieve_project_context(mock_task, mock_task_run, mock_session)

    assert result is None
    retriever_cls.assert_not_called()
