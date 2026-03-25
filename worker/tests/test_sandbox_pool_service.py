"""Unit tests for SandboxPoolService."""
import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest

from sandbox.exceptions import SandboxHealthCheckError, SandboxPoolExhaustedError
from sandbox.pool_service import SandboxPoolService


@pytest.mark.asyncio
async def test_ensure_min_capacity_prewarms_to_minimum():
    """Pool should create sandboxes until configured minimum size is reached."""
    service = SandboxPoolService(min_size=2, max_size=4)
    mock_session = AsyncMock()

    with patch.object(service, "reap_stale_leases", new=AsyncMock(return_value=0)), \
         patch.object(service, "_acquire_pool_lock", new=AsyncMock()), \
         patch.object(service, "_count_active_sandboxes", new=AsyncMock(return_value=0)), \
         patch.object(service, "create_pooled_sandbox", new=AsyncMock()) as mock_create:
        created = await service.ensure_min_capacity(mock_session)

    assert created == 2
    assert mock_create.await_count == 2


@pytest.mark.asyncio
async def test_lease_sandbox_claims_available_session():
    """Available sandbox should transition to leased with task metadata."""
    service = SandboxPoolService(min_size=0, max_size=2)
    task_run_id = uuid.uuid4()
    sandbox_session = Mock()
    sandbox_session.container_id = "container123"
    sandbox_session.status = "available"
    sandbox_session.task_run_id = None
    sandbox_session.reuse_count = 0
    sandbox_session.last_used_at = None
    sandbox_session.last_health_check_at = None
    sandbox_session.lease_error = None
    sandbox_session.drain_reason = None
    sandbox_session.terminated_at = None

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()

    with patch.object(service, "reap_stale_leases", new=AsyncMock(return_value=0)), \
         patch.object(service, "get_leased_sandbox_for_task_run", new=AsyncMock(return_value=None)), \
         patch.object(service, "_select_available_sandbox", new=AsyncMock(return_value=sandbox_session)):
        leased = await service.lease_sandbox(mock_session, task_run_id)

    assert leased is sandbox_session
    assert sandbox_session.status == "leased"
    assert sandbox_session.task_run_id == task_run_id
    assert sandbox_session.reuse_count == 1
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_lease_sandbox_creates_when_pool_has_capacity():
    """Pool should create a new sandbox when none are available and capacity remains."""
    service = SandboxPoolService(min_size=0, max_size=1)
    task_run_id = uuid.uuid4()
    sandbox_session = Mock()
    sandbox_session.container_id = "container123"
    sandbox_session.status = "available"
    sandbox_session.task_run_id = None
    sandbox_session.reuse_count = 0
    sandbox_session.last_used_at = None
    sandbox_session.last_health_check_at = None
    sandbox_session.lease_error = None
    sandbox_session.drain_reason = None
    sandbox_session.terminated_at = None

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()

    with patch.object(service, "reap_stale_leases", new=AsyncMock(return_value=0)), \
         patch.object(service, "get_leased_sandbox_for_task_run", new=AsyncMock(return_value=None)), \
         patch.object(service, "_select_available_sandbox", new=AsyncMock(side_effect=[None, sandbox_session])), \
         patch.object(service, "_acquire_pool_lock", new=AsyncMock()), \
         patch.object(service, "_count_active_sandboxes", new=AsyncMock(return_value=0)), \
         patch.object(service, "create_pooled_sandbox", new=AsyncMock()) as mock_create:
        leased = await service.lease_sandbox(mock_session, task_run_id)

    assert leased is sandbox_session
    mock_create.assert_awaited_once()


@pytest.mark.asyncio
async def test_lease_sandbox_raises_when_pool_exhausted():
    """Lease should fail when pool is at max capacity and no sandbox is available."""
    service = SandboxPoolService(min_size=0, max_size=1)
    mock_session = AsyncMock()

    with patch.object(service, "reap_stale_leases", new=AsyncMock(return_value=0)), \
         patch.object(service, "get_leased_sandbox_for_task_run", new=AsyncMock(return_value=None)), \
         patch.object(service, "_select_available_sandbox", new=AsyncMock(return_value=None)), \
         patch.object(service, "_acquire_pool_lock", new=AsyncMock()), \
         patch.object(service, "_count_active_sandboxes", new=AsyncMock(return_value=1)):
        with pytest.raises(SandboxPoolExhaustedError):
            await service.lease_sandbox(mock_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_return_sandbox_sets_available_state():
    """Healthy sandbox should return to available state and clear lease metadata."""
    service = SandboxPoolService(min_size=0, max_size=2, max_reuse_count=10)
    sandbox_session = Mock()
    sandbox_session.container_id = "container123"
    sandbox_session.status = "leased"
    sandbox_session.task_run_id = uuid.uuid4()
    sandbox_session.leased_at = object()
    sandbox_session.reuse_count = 1
    sandbox_session.drain_reason = "old"
    sandbox_session.lease_error = "old"
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()

    await service.return_sandbox(mock_session, sandbox_session, healthy=True)

    assert sandbox_session.status == "available"
    assert sandbox_session.task_run_id is None
    assert sandbox_session.leased_at is None
    assert sandbox_session.drain_reason is None
    assert sandbox_session.lease_error is None
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_return_sandbox_recycles_unhealthy_session():
    """Unhealthy sandboxes should be recycled instead of returned."""
    service = SandboxPoolService(min_size=0, max_size=2, max_reuse_count=10)
    sandbox_session = Mock()
    sandbox_session.reuse_count = 1
    mock_session = AsyncMock()

    with patch.object(service, "recycle_sandbox", new=AsyncMock()) as mock_recycle:
        await service.return_sandbox(mock_session, sandbox_session, healthy=False)

    mock_recycle.assert_awaited_once()


@pytest.mark.asyncio
async def test_return_sandbox_recycles_after_max_reuse():
    """Sandboxes beyond max reuse count should be recycled."""
    service = SandboxPoolService(min_size=0, max_size=2, max_reuse_count=3)
    sandbox_session = Mock()
    sandbox_session.reuse_count = 3
    mock_session = AsyncMock()

    with patch.object(service, "recycle_sandbox", new=AsyncMock()) as mock_recycle:
        await service.return_sandbox(mock_session, sandbox_session, healthy=True)

    mock_recycle.assert_awaited_once()


@pytest.mark.asyncio
async def test_health_check_sandbox_raises_on_non_zero_exit():
    """Health checks should fail on non-zero exit code."""
    service = SandboxPoolService()
    sandbox_manager = AsyncMock()
    sandbox_manager.execute = AsyncMock(return_value=(1, "bad"))

    with pytest.raises(SandboxHealthCheckError):
        await service.health_check_sandbox(sandbox_manager)


@pytest.mark.asyncio
async def test_create_pooled_sandbox_persists_session():
    """Creating a pooled sandbox should persist the session row."""
    service = SandboxPoolService()
    mock_session = AsyncMock()
    mock_session.add = Mock()
    mock_session.commit = AsyncMock()

    with patch("sandbox.pool_service.SandboxManager") as mock_manager_cls:
        mock_manager = AsyncMock()
        mock_manager.create = AsyncMock(return_value="container123")
        mock_manager.workspace_dir = "/tmp/badgers-123"
        mock_manager_cls.return_value = mock_manager

        sandbox_session = await service.create_pooled_sandbox(mock_session)

    assert sandbox_session.container_id == "container123"
    assert sandbox_session.status == "available"
    assert sandbox_session.workspace_dir == "/tmp/badgers-123"
    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()
