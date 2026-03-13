"""Worker main loop - autonomous task execution engine."""
import asyncio
import signal
import sys
import uuid
import logging
from datetime import datetime, timezone
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from config import settings
from orchestrator.agent import Agent
from sandbox.manager import SandboxManager
from models.factory import create_model_provider
from tools import get_all_tools
from skills.registry import get_skill

# Database setup
engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,
    pool_pre_ping=True,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Logging setup
logger = structlog.get_logger(__name__)

def configure_logging():
    """Configure structlog for worker process."""
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )

# Graceful shutdown
shutdown_event = asyncio.Event()

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info("shutdown_signal_received", signal=signum)
    shutdown_event.set()

def setup_signal_handlers():
    """Setup SIGTERM and SIGINT handlers."""
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

async def get_next_pending_task(session: AsyncSession):
    """Fetch and claim next PENDING TaskRun."""
    from backend.app.models.task import TaskRun, TaskStatus

    # Query for PENDING tasks
    result = await session.execute(
        select(TaskRun)
        .where(TaskRun.status == TaskStatus.PENDING)
        .order_by(TaskRun.created_at)
        .limit(1)
    )
    task_run = result.scalar_one_or_none()

    if task_run:
        # Claim task by updating status
        task_run.status = TaskStatus.RUNNING
        task_run.started_at = datetime.now(timezone.utc)
        await session.commit()
        logger.info("task_claimed", task_run_id=str(task_run.id))

    return task_run

async def execute_task_run(task_run_id: uuid.UUID, session: AsyncSession):
    """Execute a single TaskRun with sandbox and agent."""
    from backend.app.models.task import Task, TaskRun, TaskStatus
    from backend.app.models.sandbox import SandboxSession

    task_logger = structlog.get_logger().bind(task_run_id=str(task_run_id))
    task_logger.info("task_execution_started")

    sandbox = None
    sandbox_session = None

    try:
        # Load TaskRun and Task
        result = await session.execute(
            select(TaskRun).where(TaskRun.id == task_run_id)
        )
        task_run = result.scalar_one()

        result = await session.execute(
            select(Task).where(Task.id == task_run.task_id)
        )
        task = result.scalar_one()

        # Create sandbox
        sandbox = SandboxManager(
            task_run_id=task_run_id,
            image=settings.sandbox_image,
            mem_limit=settings.sandbox_memory_limit,
            cpu_quota=settings.sandbox_cpu_quota
        )

        container_id = await sandbox.create()
        task_logger.info("sandbox_created", container_id=container_id)

        # Persist SandboxSession
        sandbox_session = SandboxSession(
            task_run_id=task_run_id,
            container_id=container_id,
            image=settings.sandbox_image,
            cpu_limit=settings.sandbox_cpu_quota,
            memory_limit=int(settings.sandbox_memory_limit.removesuffix('m').removesuffix('g'))
        )
        session.add(sandbox_session)
        await session.commit()

        # Initialize model
        model_provider = create_model_provider(
            provider=settings.model_provider,
            model=task.model or settings.default_main_model,
            config={}
        )

        # Load skill if specified
        skill = None
        if task.skill:
            skill = get_skill(task.skill)
            if skill:
                task_logger.info("skill_loaded", skill=task.skill)
            else:
                task_logger.warning("skill_not_found", skill=task.skill)

        # Initialize tools
        tools = get_all_tools(sandbox)

        # Create and run agent
        agent = Agent(
            task_run_id=task_run_id,
            model=model_provider,
            tools=tools,
            max_iterations=20,
            skill=skill
        )

        result = await agent.run(
            goal=task.goal,
            system_prompt=skill.system_prompt if skill else None
        )

        # Update TaskRun with success
        task_run.status = TaskStatus.COMPLETED
        task_run.completed_at = datetime.now(timezone.utc)
        await session.commit()

        task_logger.info("task_execution_completed", result_length=len(result))

        # Cleanup sandbox
        await sandbox.destroy()
        sandbox_session.terminated_at = datetime.now(timezone.utc)
        await session.commit()

    except Exception as e:
        task_logger.error("task_execution_failed", error=str(e), exc_info=True)

        # Update TaskRun with failure if it was loaded
        if 'task_run' in locals():
            task_run.status = TaskStatus.FAILED
            task_run.completed_at = datetime.now(timezone.utc)
            task_run.error_message = str(e)
            await session.commit()

        # Cleanup sandbox if created
        try:
            if sandbox:
                await sandbox.destroy()
            if sandbox_session:
                sandbox_session.terminated_at = datetime.now(timezone.utc)
                await session.commit()
        except Exception as cleanup_error:
            task_logger.error("sandbox_cleanup_failed", error=str(cleanup_error))

async def worker_loop():
    """Main worker loop - poll for tasks and execute."""
    logger.info("worker_started")

    while not shutdown_event.is_set():
        try:
            async with async_session_maker() as session:
                task_run = await get_next_pending_task(session)

                if task_run:
                    await execute_task_run(task_run.id, session)
                else:
                    # No tasks available, wait before polling again
                    await asyncio.sleep(settings.worker_poll_interval or 5)

        except Exception as e:
            logger.error("worker_loop_error", error=str(e), exc_info=True)
            await asyncio.sleep(5)  # Back off on error

    logger.info("worker_stopped")

async def main():
    """Main entry point."""
    configure_logging()
    setup_signal_handlers()

    logger.info("worker_initializing")

    try:
        await worker_loop()
    except KeyboardInterrupt:
        logger.info("worker_interrupted")
    finally:
        await engine.dispose()
        logger.info("worker_shutdown_complete")

if __name__ == "__main__":
    asyncio.run(main())
