"""Tests for worker main loop."""
import pytest
import uuid
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime


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
    from backend.app.models.task import TaskRun, TaskStatus

    mock_task_run = Mock(spec=TaskRun)
    mock_task_run.id = uuid.uuid4()
    mock_task_run.status = TaskStatus.PENDING

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=Mock(scalar_one_or_none=Mock(return_value=mock_task_run)))
    mock_session.commit = AsyncMock()

    result = await get_next_pending_task(mock_session)

    assert result == mock_task_run
    assert result.status == TaskStatus.RUNNING
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_execute_task_run_success():
    """Test successful task execution."""
    from worker.main import execute_task_run
    from backend.app.models.task import Task, TaskRun, TaskStatus
    from backend.app.models.sandbox import SandboxSession

    task_run_id = uuid.uuid4()
    task_id = uuid.uuid4()

    mock_task = Mock(spec=Task)
    mock_task.id = task_id
    mock_task.goal = "test goal"
    mock_task.model = None
    mock_task.skill = None

    mock_task_run = Mock(spec=TaskRun)
    mock_task_run.id = task_run_id
    mock_task_run.task_id = task_id
    mock_task_run.status = TaskStatus.RUNNING

    mock_session = AsyncMock()

    # Mock database queries
    mock_session.execute = AsyncMock(side_effect=[
        Mock(scalar_one=Mock(return_value=mock_task_run)),
        Mock(scalar_one=Mock(return_value=mock_task))
    ])
    mock_session.add = Mock()
    mock_session.commit = AsyncMock()

    # Mock sandbox
    with patch('worker.main.SandboxManager') as mock_sandbox_cls:
        mock_sandbox = AsyncMock()
        mock_sandbox.create = AsyncMock(return_value="container_123")
        mock_sandbox.destroy = AsyncMock()
        mock_sandbox_cls.return_value = mock_sandbox

        # Mock model provider
        with patch('worker.main.create_model_provider') as mock_model:
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


@pytest.mark.asyncio
async def test_execute_task_run_failure_updates_status():
    """Test that failures are properly recorded."""
    from worker.main import execute_task_run
    from backend.app.models.task import Task, TaskRun, TaskStatus

    task_run_id = uuid.uuid4()
    task_id = uuid.uuid4()

    mock_task = Mock(spec=Task)
    mock_task.id = task_id
    mock_task.goal = "test goal"
    mock_task.model = None
    mock_task.skill = None

    mock_task_run = Mock(spec=TaskRun)
    mock_task_run.id = task_run_id
    mock_task_run.task_id = task_id
    mock_task_run.status = TaskStatus.RUNNING

    mock_session = AsyncMock()

    # Mock database queries to return task_run and task, then fail on sandbox creation
    mock_session.execute = AsyncMock(side_effect=[
        Mock(scalar_one=Mock(return_value=mock_task_run)),
        Mock(scalar_one=Mock(return_value=mock_task))
    ])
    mock_session.add = Mock()
    mock_session.commit = AsyncMock()

    # Mock sandbox to fail
    with patch('worker.main.SandboxManager') as mock_sandbox_cls:
        mock_sandbox = AsyncMock()
        mock_sandbox.create = AsyncMock(side_effect=Exception("Sandbox creation failed"))
        mock_sandbox_cls.return_value = mock_sandbox

        await execute_task_run(task_run_id, mock_session)

        assert mock_task_run.status == TaskStatus.FAILED
        assert mock_task_run.error_message == "Sandbox creation failed"
