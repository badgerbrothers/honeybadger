"""Worker main loop - autonomous task execution engine."""
import asyncio
import logging
from pathlib import Path
import signal
import uuid
from datetime import datetime, UTC
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

try:
    from db_models import (
        DocumentIndexJob,
        DocumentIndexStatus,
        Task,
        TaskRun,
        TaskStatus,
    )
except ModuleNotFoundError:  # pragma: no cover - package-import fallback
    from worker.db_models import (
        DocumentIndexJob,
        DocumentIndexStatus,
        Task,
        TaskRun,
        TaskStatus,
    )
try:
    from config import settings
    from orchestrator.agent import Agent
    from models.factory import create_model_provider
    from services.backend_client import BackendClient
    from services.storage_client import storage_client
    from sandbox.pool_service import pool_service
    from tools import get_all_tools
    from skills.registry import get_skill
except ModuleNotFoundError:  # pragma: no cover - package-import fallback
    from worker.config import settings
    from worker.orchestrator.agent import Agent
    from worker.models.factory import create_model_provider
    from worker.services.backend_client import BackendClient
    from worker.services.storage_client import storage_client
    from worker.sandbox.pool_service import pool_service
    from worker.tools import get_all_tools
    from worker.skills.registry import get_skill

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


def utcnow() -> datetime:
    """Return naive UTC datetime to match current DB column definitions."""
    return datetime.now(UTC).replace(tzinfo=None)


def append_run_log(task_run, event_type: str, **payload) -> None:
    """Append a structured event to TaskRun.logs."""
    logs = list(task_run.logs or [])
    logs.append({
        "type": event_type,
        "timestamp": utcnow().isoformat(),
        **payload,
    })
    task_run.logs = logs


def classify_run_failure(exc: Exception) -> tuple[str, bool]:
    """Classify a run failure into a coarse category and retry hint."""
    try:
        from models.exceptions import ConfigurationError, InvalidRequestError, RateLimitError
        from orchestrator.exceptions import ModelError as OrchestratorModelError, ToolExecutionError
        from sandbox.exceptions import SandboxCreationError, SandboxError
        from tools.exceptions import ToolError
    except ModuleNotFoundError:  # pragma: no cover - package-import fallback
        from worker.models.exceptions import ConfigurationError, InvalidRequestError, RateLimitError
        from worker.orchestrator.exceptions import (
            ModelError as OrchestratorModelError,
            ToolExecutionError,
        )
        from worker.sandbox.exceptions import SandboxCreationError, SandboxError
        from worker.tools.exceptions import ToolError

    if isinstance(exc, RateLimitError):
        return "model_api", True
    if isinstance(exc, (ConfigurationError, InvalidRequestError, ValueError)):
        return "validation", False
    if isinstance(exc, OrchestratorModelError):
        return "model_api", True
    if isinstance(exc, ToolExecutionError):
        return "tool", False
    if isinstance(exc, ToolError):
        return "tool", False
    if isinstance(exc, SandboxCreationError):
        return "sandbox", True
    if isinstance(exc, SandboxError):
        return "sandbox", False
    if isinstance(exc, TimeoutError):
        return "internal", True
    return "internal", False


def build_run_failure_event(exc: Exception, *, failed_step: str) -> dict:
    """Build a structured run_failed event payload."""
    error_category, retryable_hint = classify_run_failure(exc)
    error_message = str(exc)
    return {
        "error": error_message,
        "error_message": error_message,
        "error_category": error_category,
        "retryable_hint": retryable_hint,
        "failed_step": failed_step,
    }


def classify_index_job_failure(exc: Exception, *, failed_step: str) -> tuple[str, str]:
    """Classify an index-job failure into an error code and normalized step."""
    try:
        from models.exceptions import ModelError as WorkerModelError, RateLimitError
        from rag.parsers.exceptions import FileReadError, ParseError, UnsupportedFormatError
    except ModuleNotFoundError:  # pragma: no cover - package-import fallback
        from worker.models.exceptions import ModelError as WorkerModelError, RateLimitError
        from worker.rag.parsers.exceptions import FileReadError, ParseError, UnsupportedFormatError

    if isinstance(exc, UnsupportedFormatError):
        return "unsupported_format", "parse"
    if isinstance(exc, FileReadError):
        return "file_read_failed", "parse"
    if isinstance(exc, ParseError):
        return "document_parse_failed", "parse"
    if isinstance(exc, RateLimitError):
        return "embedding_rate_limited", "embedding"
    if isinstance(exc, WorkerModelError):
        return "embedding_request_failed", "embedding"
    if failed_step == "validate_configuration":
        return "openai_api_key_missing", failed_step
    if failed_step == "download_file":
        return "storage_download_failed", failed_step
    if failed_step == "index_document":
        return "document_index_failed", failed_step
    return "document_index_failed", failed_step


def build_system_prompt(skill_prompt: str | None, rag_context: str | None = None) -> str | None:
    """Merge skill prompt and optional retrieved context into a single system prompt."""
    parts = [part for part in [skill_prompt, rag_context] if part]
    if not parts:
        return None
    return "\n\n".join(parts)


async def get_next_pending_task(session: AsyncSession):
    """Fetch and claim next PENDING TaskRun."""

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
        task_run.started_at = utcnow()
        append_run_log(task_run, "run_started", status=TaskStatus.RUNNING.value)
        await session.commit()
        logger.info("task_claimed", task_run_id=str(task_run.id))

    return task_run


async def claim_task_run_by_id(session: AsyncSession, task_run_id: uuid.UUID) -> TaskRun | None:
    """Claim a specific TaskRun when it is still pending."""
    result = await session.execute(
        select(TaskRun).where(TaskRun.id == task_run_id)
    )
    task_run = result.scalar_one_or_none()
    if task_run is None:
        raise ValueError(f"TaskRun not found: {task_run_id}")

    if task_run.status != TaskStatus.PENDING:
        logger.info(
            "task_run_not_claimed",
            task_run_id=str(task_run_id),
            status=task_run.status.value,
        )
        return None

    task_run.status = TaskStatus.RUNNING
    if task_run.started_at is None:
        task_run.started_at = utcnow()
    append_run_log(task_run, "run_started", status=TaskStatus.RUNNING.value)
    await session.commit()
    logger.info("task_claimed", task_run_id=str(task_run.id))
    return task_run


async def get_next_pending_index_job(session: AsyncSession):
    """Fetch and claim the next pending document indexing job."""
    result = await session.execute(
        select(DocumentIndexJob)
        .where(DocumentIndexJob.status == DocumentIndexStatus.PENDING)
        .order_by(DocumentIndexJob.created_at)
        .limit(1)
    )
    job = result.scalar_one_or_none()
    if job:
        job.status = DocumentIndexStatus.RUNNING
        job.started_at = utcnow()
        await session.commit()
        logger.info("document_index_job_claimed", job_id=str(job.id))
    return job


async def claim_document_index_job_by_id(
    session: AsyncSession,
    job_id: uuid.UUID,
) -> DocumentIndexJob | None:
    """Claim a specific document index job when it is still pending."""
    result = await session.execute(
        select(DocumentIndexJob).where(DocumentIndexJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise ValueError(f"DocumentIndexJob not found: {job_id}")

    if job.status != DocumentIndexStatus.PENDING:
        logger.info(
            "document_index_job_not_claimed",
            job_id=str(job_id),
            status=job.status.value,
        )
        return None

    job.status = DocumentIndexStatus.RUNNING
    if job.started_at is None:
        job.started_at = utcnow()
    await session.commit()
    logger.info("document_index_job_claimed", job_id=str(job.id))
    return job


async def finalize_run_state(
    session: AsyncSession,
    task,
    task_run,
    status,
    *,
    error_message: str | None = None,
    result: str | None = None,
) -> None:
    """Write the terminal state for a run and clear Task.current_run_id if needed."""
    task_run.status = status
    task_run.completed_at = utcnow()
    task_run.error_message = error_message
    if task and task.current_run_id == task_run.id:
        task.current_run_id = None

    if status.value == "completed":
        append_run_log(task_run, "run_completed", result=result or "")
    elif status.value == "failed":
        append_run_log(task_run, "run_failed", error=error_message or "")
    elif status.value == "cancelled":
        append_run_log(task_run, "run_cancelled")

    await session.commit()


async def reload_task_execution_state(
    session: AsyncSession,
    task_run_id: uuid.UUID,
) -> tuple[TaskRun | None, Task | None]:
    """Reload run/task ORM instances after rollback invalidates previous ones."""
    run_result = await session.execute(
        select(TaskRun).where(TaskRun.id == task_run_id)
    )
    task_run = run_result.scalar_one_or_none()
    if task_run is None:
        return None, None

    task_result = await session.execute(
        select(Task).where(Task.id == task_run.task_id)
    )
    task = task_result.scalar_one_or_none()
    return task_run, task


async def retrieve_project_context(task, task_run, session: AsyncSession) -> str | None:
    """Retrieve RAG chunks relevant to the task goal and persist a summary."""
    if not settings.openai_api_key:
        return None
    rag_collection_id = getattr(task, "rag_collection_id", None)
    if not rag_collection_id:
        # RAG is optional. When no collection is selected, skip retrieval entirely.
        return None

    from rag.embeddings import EmbeddingService
    from rag.retriever import DocumentRetriever

    retriever = DocumentRetriever(
        EmbeddingService(
            settings.openai_api_key,
            settings.embedding_model,
            settings.embedding_dimension,
        ),
        session,
    )
    chunks = await retriever.retrieve(
        query=task.goal,
        project_id=None,
        rag_collection_id=str(rag_collection_id),
        top_k=5,
        threshold=0.55,
    )
    if not chunks:
        return None

    task_run.working_memory = {
        "rag_context": [
            {
                "id": chunk["id"],
                "file_path": chunk["file_path"],
                "chunk_index": chunk["chunk_index"],
                "similarity": chunk["similarity"],
            }
            for chunk in chunks
        ]
    }
    await session.commit()

    formatted_chunks = []
    for chunk in chunks:
        formatted_chunks.append(
            f"[{chunk['file_path']}#{chunk['chunk_index']}] {chunk['content']}"
        )
    return "Relevant project context:\n" + "\n\n".join(formatted_chunks)


async def emit_run_event(
    backend_client: BackendClient | None,
    task_run_id: uuid.UUID,
    event_type: str,
    **payload,
) -> None:
    """Report an execution event to the backend if configured."""
    if backend_client is None:
        return
    event = {
        "type": event_type,
        "timestamp": utcnow().isoformat(),
        **payload,
    }
    try:
        await backend_client.emit_run_event(str(task_run_id), event)
    except Exception as exc:
        logger.warning("run_event_emit_failed", task_run_id=str(task_run_id), error=str(exc))


async def upload_artifact_candidate(
    backend_client: BackendClient | None,
    task_run_id: uuid.UUID,
    project_id,
    metadata: dict | None,
) -> dict | None:
    """Upload a file-like artifact candidate and return backend metadata."""
    if backend_client is None or not metadata or project_id is None:
        return None

    artifact = metadata.get("artifact")
    if not artifact:
        return None

    path = artifact.get("path")
    if not path or not Path(path).exists():
        return None

    uploaded = await backend_client.upload_artifact(
        project_id=str(project_id),
        task_run_id=str(task_run_id),
        file_path=path,
        artifact_type=artifact.get("artifact_type", "file"),
    )
    return uploaded


async def execute_document_index_job(job_id: uuid.UUID, session: AsyncSession):
    """Execute a single document indexing job."""
    job_logger = structlog.get_logger().bind(document_index_job_id=str(job_id))
    result = await session.execute(select(DocumentIndexJob).where(DocumentIndexJob.id == job_id))
    job = result.scalar_one()

    local_path = None
    failed_step = "load_job"
    try:
        if job.status != DocumentIndexStatus.RUNNING:
            job_logger.info(
                "document_index_job_skipped",
                reason="job_not_running",
                status=job.status.value,
            )
            return

        failed_step = "validate_configuration"
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY not configured for RAG indexing")

        from rag.embeddings import EmbeddingService
        from rag.indexer import DocumentIndexer

        failed_step = "download_file"
        file_bytes = await storage_client.download_file(job.storage_path)
        workspace = Path("worker_tmp") / "rag"
        workspace.mkdir(parents=True, exist_ok=True)
        local_path = workspace / f"{job.id}_{job.file_name}"
        local_path.write_bytes(file_bytes)

        indexer = DocumentIndexer(
            EmbeddingService(
                settings.openai_api_key,
                settings.embedding_model,
                settings.embedding_dimension,
            ),
            session,
        )
        failed_step = "index_document"
        chunk_count = await indexer.index_document(
            project_id=job.project_id,
            rag_collection_id=getattr(job, "rag_collection_id", None),
            file_path=str(local_path),
        )

        job.status = DocumentIndexStatus.COMPLETED
        job.completed_at = utcnow()
        job.error_code = None
        job.error_message = None
        job.failed_step = None
        job.chunk_count = chunk_count
        await session.commit()
        job_logger.info("document_index_job_completed", chunk_count=chunk_count)
    except Exception as exc:
        error_code, normalized_step = classify_index_job_failure(exc, failed_step=failed_step)
        job.status = DocumentIndexStatus.FAILED
        job.completed_at = utcnow()
        job.error_code = error_code
        job.error_message = str(exc)
        job.failed_step = normalized_step
        await session.commit()
        job_logger.error(
            "document_index_job_failed",
            error=str(exc),
            error_code=error_code,
            failed_step=normalized_step,
            exc_info=True,
        )
    finally:
        if local_path and local_path.exists():
            local_path.unlink(missing_ok=True)


async def execute_task_run(task_run_id: uuid.UUID, session: AsyncSession):
    """Execute a single TaskRun with sandbox and agent."""
    try:
        from sandbox.manager import SandboxManager
    except ModuleNotFoundError:  # pragma: no cover - package-import fallback
        from worker.sandbox.manager import SandboxManager

    task_logger = structlog.get_logger().bind(task_run_id=str(task_run_id))
    task_logger.info("task_execution_started")

    sandbox = None
    sandbox_session = None
    pending_event_tasks: list[asyncio.Task] = []
    failed_step = "load_task_run"
    backend_client = (
        BackendClient(
            settings.backend_base_url,
            internal_service_token=settings.internal_service_token,
        )
        if settings.backend_base_url
        else None
    )

    def schedule_event(event_type: str, **payload) -> None:
        pending_event_tasks.append(
            asyncio.create_task(
                emit_run_event(
                    backend_client,
                    task_run_id,
                    event_type,
                    **payload,
                )
            )
        )

    try:
        # Load TaskRun and Task
        result = await session.execute(
            select(TaskRun).where(TaskRun.id == task_run_id)
        )
        task_run = result.scalar_one()

        failed_step = "load_task"
        result = await session.execute(
            select(Task).where(Task.id == task_run.task_id)
        )
        task = result.scalar_one()

        if task_run.status != TaskStatus.RUNNING:
            task_logger.info(
                "task_execution_skipped",
                reason="task_run_not_running",
                status=task_run.status.value,
            )
            return

        if task.current_run_id != task_run.id:
            task.current_run_id = task_run.id
            await session.commit()

        schedule_event("run_started", status=task_run.status.value)

        failed_step = "sandbox_lookup"
        existing_sandbox_session = await pool_service.get_leased_sandbox_for_task_run(
            session,
            task_run_id,
        )
        if existing_sandbox_session is not None:
            task_logger.warning(
                "task_execution_skipped",
                reason="sandbox_already_leased_for_task_run",
                container_id=existing_sandbox_session.container_id,
            )
            return

        failed_step = "sandbox_ensure_capacity"
        await pool_service.ensure_min_capacity(session)

        failed_step = "sandbox_lease"
        sandbox_session = await pool_service.lease_sandbox(session, task_run_id)
        sandbox = SandboxManager.from_session(sandbox_session)

        task_logger.info("sandbox_leased", container_id=sandbox_session.container_id)
        append_run_log(task_run, "sandbox_leased", container_id=sandbox_session.container_id)
        schedule_event(
            "step",
            message="sandbox_leased",
            container_id=sandbox_session.container_id,
        )

        # Initialize model
        failed_step = "model_initialize"
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
                append_run_log(task_run, "skill_loaded", skill=task.skill)
            else:
                task_logger.warning("skill_not_found", skill=task.skill)
                append_run_log(task_run, "skill_missing", skill=task.skill)

        # Initialize tools
        tools = get_all_tools(sandbox)

        failed_step = "context_retrieve"
        rag_context = await retrieve_project_context(task, task_run, session)

        def on_agent_event(event: dict) -> None:
            event_type = event.get("type", "step")
            payload = {key: value for key, value in event.items() if key != "type"}
            append_run_log(task_run, event_type, **payload)
            schedule_event(event_type, **payload)
            if event_type == "tool_result":
                metadata = payload.get("metadata")
                pending_event_tasks.append(
                    asyncio.create_task(
                        _upload_artifact_from_tool_result(
                            backend_client,
                            task_run,
                            task.project_id,
                            metadata,
                            schedule_event,
                        )
                    )
                )

        # Create and run agent
        failed_step = "agent_run"
        agent = Agent(
            task_run_id=task_run_id,
            model=model_provider,
            tools=tools,
            max_iterations=20,
            skill=skill,
            event_callback=on_agent_event,
        )

        result = await agent.run(
            goal=task.goal,
            system_prompt=build_system_prompt(skill.system_prompt if skill else None, rag_context)
        )

        await session.refresh(task_run)
        if task_run.status == TaskStatus.CANCELLED:
            await finalize_run_state(session, task, task_run, TaskStatus.CANCELLED)
            schedule_event("run_cancelled")
        else:
            await finalize_run_state(
                session,
                task,
                task_run,
                TaskStatus.COMPLETED,
                result=result,
            )
            schedule_event("run_completed", result=result)

        task_logger.info("task_execution_completed", result_length=len(result))

    except Exception as e:
        task_logger.error("task_execution_failed", error=str(e), exc_info=True)
        await session.rollback()

        try:
            reloaded_task_run, reloaded_task = await reload_task_execution_state(session, task_run_id)
            if reloaded_task_run is None:
                task_logger.error("task_failure_state_update_skipped", reason="task_run_not_found_after_rollback")
            elif reloaded_task_run.status == TaskStatus.CANCELLED and reloaded_task is not None:
                await finalize_run_state(session, reloaded_task, reloaded_task_run, TaskStatus.CANCELLED)
                schedule_event("run_cancelled")
            elif reloaded_task is not None:
                await finalize_run_state(
                    session,
                    reloaded_task,
                    reloaded_task_run,
                    TaskStatus.FAILED,
                    error_message=str(e),
                )
                schedule_event("run_failed", **build_run_failure_event(e, failed_step=failed_step))
            else:
                task_logger.error(
                    "task_failure_state_update_skipped",
                    reason="task_not_found_after_rollback",
                    task_run_id=str(task_run_id),
                )
        except Exception as state_error:
                task_logger.error("task_failure_state_update_failed", error=str(state_error), exc_info=True)
    finally:
        if sandbox and sandbox_session:
            failed_step = "sandbox_return"
            try:
                await pool_service.mark_resetting(session, sandbox_session)
                await pool_service.reset_sandbox(sandbox)
                await pool_service.health_check_sandbox(sandbox)
                await pool_service.return_sandbox(session, sandbox_session, healthy=True)
            except Exception as cleanup_error:
                task_logger.error("sandbox_return_failed", error=str(cleanup_error), exc_info=True)
                try:
                    await pool_service.recycle_sandbox(
                        session,
                        sandbox_session,
                        reason="return_failed",
                    )
                except Exception as recycle_error:
                    task_logger.error(
                        "sandbox_recycle_failed",
                        error=str(recycle_error),
                        exc_info=True,
                    )
            else:
                append_run_log(task_run, "sandbox_returned", container_id=sandbox_session.container_id)
                schedule_event(
                    "step",
                    message="sandbox_returned",
                    container_id=sandbox_session.container_id,
                )
        if pending_event_tasks:
            await asyncio.gather(*pending_event_tasks, return_exceptions=True)


async def _upload_artifact_from_tool_result(
    backend_client: BackendClient | None,
    task_run,
    project_id,
    metadata: dict | None,
    schedule_event,
) -> None:
    """Upload tool-generated files as artifacts and emit lifecycle events."""
    uploaded = await upload_artifact_candidate(
        backend_client=backend_client,
        task_run_id=task_run.id,
        project_id=project_id,
        metadata=metadata,
    )
    if uploaded:
        schedule_event(
            "artifact_created",
            artifact_id=uploaded["id"],
            name=uploaded["name"],
            artifact_type=uploaded["artifact_type"],
        )

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
                    index_job = await get_next_pending_index_job(session)
                    if index_job:
                        await execute_document_index_job(index_job.id, session)
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
