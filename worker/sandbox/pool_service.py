"""Sandbox pool orchestration service."""
from __future__ import annotations

from datetime import datetime, timedelta, UTC
import uuid

import structlog
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from config import settings
    from db_models import SandboxSession, SandboxStatus
except ModuleNotFoundError:  # pragma: no cover - package-import fallback
    from worker.config import settings
    from worker.db_models import SandboxSession, SandboxStatus

from .exceptions import SandboxHealthCheckError, SandboxPoolExhaustedError
from .manager import SandboxManager

logger = structlog.get_logger(__name__)
_POOL_LOCK_KEY = 734395823742


def utcnow() -> datetime:
    """Return naive UTC datetime to match current DB column definitions."""
    return datetime.now(UTC).replace(tzinfo=None)


def parse_memory_limit_to_mb(raw_limit: str) -> int:
    """Convert Docker memory limit string to megabytes."""
    normalized = (raw_limit or "").strip().lower()
    if not normalized:
        return 0
    if normalized.endswith("g"):
        return int(normalized[:-1]) * 1024
    if normalized.endswith("m"):
        return int(normalized[:-1])
    if normalized.endswith("k"):
        return max(int(normalized[:-1]) // 1024, 1)
    return int(normalized)


class SandboxPoolService:
    """Manage reusable pooled sandboxes for task execution."""

    def __init__(
        self,
        *,
        min_size: int | None = None,
        max_size: int | None = None,
        max_reuse_count: int | None = None,
        lease_timeout_seconds: int | None = None,
        healthcheck_command: str | None = None,
    ):
        self.min_size = min_size if min_size is not None else settings.sandbox_pool_min_size
        self.max_size = max_size if max_size is not None else settings.sandbox_pool_max_size
        self.max_reuse_count = (
            max_reuse_count
            if max_reuse_count is not None
            else settings.sandbox_max_reuse_count
        )
        self.lease_timeout_seconds = (
            lease_timeout_seconds
            if lease_timeout_seconds is not None
            else settings.sandbox_lease_timeout_seconds
        )
        self.healthcheck_command = (
            healthcheck_command
            if healthcheck_command is not None
            else settings.sandbox_healthcheck_command
        )

    async def ensure_min_capacity(self, session: AsyncSession) -> int:
        """Prewarm sandboxes until the configured minimum size is satisfied."""
        await self.reap_stale_leases(session)

        if self.min_size <= 0:
            return 0

        await self._acquire_pool_lock(session)
        active_count = await self._count_active_sandboxes(session)
        created = 0
        while active_count < self.min_size and active_count < self.max_size:
            await self.create_pooled_sandbox(session)
            created += 1
            active_count += 1

        if created:
            logger.info(
                "sandbox_pool_refilled",
                created=created,
                active_count=active_count,
                min_size=self.min_size,
            )
        return created

    async def create_pooled_sandbox(self, session: AsyncSession) -> SandboxSession:
        """Create and persist a reusable sandbox container."""
        manager = SandboxManager(
            task_run_id=None,
            image=settings.sandbox_image,
            mem_limit=settings.sandbox_memory_limit,
            cpu_quota=settings.sandbox_cpu_quota,
        )
        try:
            container_id = await manager.create()
            sandbox_session = SandboxSession(
                task_run_id=None,
                container_id=container_id,
                image=settings.sandbox_image,
                status=SandboxStatus.AVAILABLE.value,
                workspace_dir=manager.workspace_dir,
                cpu_limit=settings.sandbox_cpu_quota,
                memory_limit=parse_memory_limit_to_mb(settings.sandbox_memory_limit),
                reuse_count=0,
                leased_at=None,
                last_used_at=None,
                last_health_check_at=utcnow(),
                lease_error=None,
                drain_reason=None,
                terminated_at=None,
            )
            session.add(sandbox_session)
            await session.commit()
            logger.info("sandbox_created", container_id=container_id, pooled=True)
            return sandbox_session
        except Exception:
            try:
                await manager.destroy()
            except Exception as cleanup_error:  # pragma: no cover - best effort cleanup
                logger.warning("sandbox_create_cleanup_failed", error=str(cleanup_error))
            raise

    async def get_leased_sandbox_for_task_run(
        self,
        session: AsyncSession,
        task_run_id: uuid.UUID,
    ) -> SandboxSession | None:
        """Return any currently leased sandbox for the given task run."""
        result = await session.execute(
            select(SandboxSession).where(
                SandboxSession.task_run_id == task_run_id,
                SandboxSession.status == SandboxStatus.LEASED.value,
            )
        )
        return result.scalar_one_or_none()

    async def lease_sandbox(
        self,
        session: AsyncSession,
        task_run_id: uuid.UUID,
    ) -> SandboxSession:
        """Atomically lease an available sandbox to a TaskRun."""
        await self.reap_stale_leases(session)

        existing = await self.get_leased_sandbox_for_task_run(session, task_run_id)
        if existing is not None:
            return existing

        for _ in range(2):
            candidate = await self._select_available_sandbox(session)
            if candidate is not None:
                candidate.status = SandboxStatus.LEASED.value
                candidate.task_run_id = task_run_id
                candidate.leased_at = utcnow()
                candidate.last_used_at = candidate.leased_at
                candidate.last_health_check_at = None
                candidate.lease_error = None
                candidate.drain_reason = None
                candidate.terminated_at = None
                candidate.reuse_count = (candidate.reuse_count or 0) + 1
                await session.commit()
                logger.info(
                    "sandbox_leased",
                    task_run_id=str(task_run_id),
                    container_id=candidate.container_id,
                    reuse_count=candidate.reuse_count,
                )
                return candidate

            await self._acquire_pool_lock(session)
            active_count = await self._count_active_sandboxes(session)
            if active_count < self.max_size:
                await self.create_pooled_sandbox(session)
                continue
            break

        raise SandboxPoolExhaustedError("No sandbox available in pool")

    async def mark_resetting(
        self,
        session: AsyncSession,
        sandbox_session: SandboxSession,
    ) -> None:
        """Mark a leased sandbox as resetting before return."""
        sandbox_session.status = SandboxStatus.RESETTING.value
        await session.commit()

    async def return_sandbox(
        self,
        session: AsyncSession,
        sandbox_session: SandboxSession,
        *,
        healthy: bool = True,
    ) -> None:
        """Return a sandbox to the pool or recycle it if it is no longer healthy."""
        if not healthy:
            await self.recycle_sandbox(session, sandbox_session, reason="unhealthy_return")
            return

        if sandbox_session.reuse_count >= self.max_reuse_count:
            await self.recycle_sandbox(session, sandbox_session, reason="max_reuse_count_exceeded")
            return

        sandbox_session.status = SandboxStatus.AVAILABLE.value
        sandbox_session.task_run_id = None
        sandbox_session.leased_at = None
        sandbox_session.last_used_at = utcnow()
        sandbox_session.last_health_check_at = utcnow()
        sandbox_session.lease_error = None
        sandbox_session.drain_reason = None
        await session.commit()
        logger.info("sandbox_returned", container_id=sandbox_session.container_id)

    async def reset_sandbox(self, sandbox_manager: SandboxManager) -> None:
        """Reset container processes and workspace contents before reuse."""
        await sandbox_manager.restart()
        sandbox_manager.reset_workspace()

    async def health_check_sandbox(self, sandbox_manager: SandboxManager) -> None:
        """Validate the sandbox is still usable after reset."""
        exit_code, output = await sandbox_manager.execute(self.healthcheck_command)
        if exit_code != 0:
            raise SandboxHealthCheckError(
                f"Health check failed with exit code {exit_code}: {output}"
            )

    async def recycle_sandbox(
        self,
        session: AsyncSession,
        sandbox_session: SandboxSession,
        *,
        reason: str,
    ) -> None:
        """Destroy a broken sandbox and refill pool capacity."""
        sandbox_session.status = SandboxStatus.DRAINING.value
        sandbox_session.drain_reason = reason
        await session.commit()

        manager = SandboxManager.from_session(sandbox_session)
        destroy_error: str | None = None
        try:
            await manager.destroy()
        except Exception as exc:  # pragma: no cover - best effort cleanup
            destroy_error = str(exc)
            logger.warning(
                "sandbox_recycle_destroy_failed",
                container_id=sandbox_session.container_id,
                error=destroy_error,
            )

        sandbox_session.status = SandboxStatus.BROKEN.value
        sandbox_session.task_run_id = None
        sandbox_session.leased_at = None
        sandbox_session.last_used_at = utcnow()
        sandbox_session.last_health_check_at = None
        sandbox_session.lease_error = destroy_error
        sandbox_session.terminated_at = utcnow()
        await session.commit()

        logger.info(
            "sandbox_recycled",
            container_id=sandbox_session.container_id,
            reason=reason,
        )
        await self.ensure_min_capacity(session)

    async def reap_stale_leases(self, session: AsyncSession) -> int:
        """Recycle sandboxes whose leases appear abandoned."""
        if self.lease_timeout_seconds <= 0:
            return 0

        cutoff = utcnow() - timedelta(seconds=self.lease_timeout_seconds)
        result = await session.execute(
            select(SandboxSession).where(
                SandboxSession.status == SandboxStatus.LEASED.value,
                or_(
                    SandboxSession.leased_at.is_(None),
                    SandboxSession.leased_at < cutoff,
                ),
            )
        )
        stale_sandboxes = list(result.scalars())
        for sandbox_session in stale_sandboxes:
            await self.recycle_sandbox(session, sandbox_session, reason="lease_timeout")
        return len(stale_sandboxes)

    async def _select_available_sandbox(
        self,
        session: AsyncSession,
    ) -> SandboxSession | None:
        """Select one available sandbox row using row-level locking."""
        result = await session.execute(
            select(SandboxSession)
            .where(SandboxSession.status == SandboxStatus.AVAILABLE.value)
            .order_by(SandboxSession.last_used_at, SandboxSession.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        return result.scalar_one_or_none()

    async def _count_active_sandboxes(self, session: AsyncSession) -> int:
        """Count sandboxes still considered part of the active pool."""
        result = await session.execute(
            select(func.count())
            .select_from(SandboxSession)
            .where(
                SandboxSession.status.in_(
                    [
                        SandboxStatus.AVAILABLE.value,
                        SandboxStatus.LEASED.value,
                        SandboxStatus.RESETTING.value,
                    ]
                )
            )
        )
        return int(result.scalar_one() or 0)

    async def _acquire_pool_lock(self, session: AsyncSession) -> None:
        """Serialize pool resize decisions across workers."""
        await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": _POOL_LOCK_KEY})


pool_service = SandboxPoolService()
