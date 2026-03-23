"""Tasks API endpoints."""
import re
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.config import settings
from app.database import get_db
from app.models.conversation import Conversation
from app.models.project import Project
from app.models.rag_collection import RagCollection
from app.models.task import QueueStatus, Task, TaskRun, TaskStatus
from app.models.user_model_config import UserModelConfig
from app.schemas.model_catalog import ModelCatalogResponse
from app.schemas.model_settings import (
    ModelProviderSettings,
    ModelSettingsPayload,
    ModelSettingsResponse,
    ProviderId,
)
from app.schemas.role_catalog import RoleCatalogItem
from app.schemas.skill_catalog import SkillCatalogItem
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse, TaskRunResponse
from app.schemas.task_queue import TaskKanbanResponse
from app.security.auth import CurrentUser, get_current_user
from app.services.queue_service import queue_service

router = APIRouter(prefix="/api/tasks", tags=["tasks"])
logger = structlog.get_logger(__name__)
_MARKDOWN_EXTENSIONS = {".md", ".markdown"}
_ICON_KIND_BY_CATEGORY = {
    "engineering": "terminal",
    "design": "file",
    "testing": "file",
    "product": "file",
    "project-management": "file",
    "support": "file",
    "academic": "file",
    "marketing": "browser",
    "sales": "browser",
    "paid-media": "browser",
    "specialized": "python",
    "spatial-computing": "python",
    "game-development": "python",
}
_SKILL_ICON_KIND_BY_CATEGORY = {
    "commands": "terminal",
    "reference": "file",
}
_MODEL_PROVIDER_IDS: tuple[ProviderId, ...] = ("openai", "anthropic", "relay")


def _slugify(raw: str, fallback: str = "item") -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    return normalized or fallback


def _markdown_title(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        trimmed = line.strip()
        if not trimmed:
            continue
        if trimmed.startswith("#"):
            title = re.sub(r"^#+\s*", "", trimmed).strip()
            return title or fallback
    return fallback


def _markdown_summary(markdown: str, default_text: str) -> str:
    for line in markdown.splitlines():
        trimmed = line.strip()
        if not trimmed:
            continue
        if trimmed.startswith("#") or trimmed.startswith(">") or trimmed.startswith("-"):
            continue
        return f"{trimmed[:80]}..." if len(trimmed) > 80 else trimmed
    return default_text


def _skill_tools_from_markdown(markdown: str) -> list[str]:
    lower = markdown.lower()
    tools: list[str] = []

    def add(tool: str) -> None:
        if tool not in tools:
            tools.append(tool)

    if "web browser" in lower or "browser" in lower or "网络浏览器" in lower:
        add("browser")
    if "shell" in lower or "terminal" in lower or "终端" in lower:
        add("shell")
    if "python" in lower:
        add("python")
    if "file i/o" in lower or "fileio" in lower or "文件" in lower:
        add("fileio")

    if not tools:
        tools.append("fileio")
    return tools


def _build_role_catalog(roles_dir: Path) -> list[RoleCatalogItem]:
    if not roles_dir.exists():
        logger.warning("roles_dir_missing", roles_dir=str(roles_dir))
        return []

    role_files = sorted(
        path
        for path in roles_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in _MARKDOWN_EXTENSIONS
    )

    roles: list[RoleCatalogItem] = []
    for role_file in role_files:
        rel_path = role_file.relative_to(roles_dir).as_posix()
        rel_stem = str(Path(rel_path).with_suffix(""))
        category = Path(rel_path).parts[0] if len(Path(rel_path).parts) > 1 else "general"
        fallback_name = role_file.stem.replace("_", " ").replace("-", " ").strip().title() or "Role"

        try:
            markdown = role_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            markdown = role_file.read_text(encoding="utf-8", errors="ignore")

        roles.append(
            RoleCatalogItem(
                id=_slugify(rel_stem, fallback="role"),
                name=_markdown_title(markdown, fallback_name),
                summary=_markdown_summary(markdown, default_text="Role markdown document"),
                iconKind=_ICON_KIND_BY_CATEGORY.get(category, "file"),
                markdown=markdown,
                category=category,
                path=rel_path,
            )
        )
    return roles


def _build_skill_catalog(skills_dir: Path) -> list[SkillCatalogItem]:
    if not skills_dir.exists():
        logger.warning("skills_dir_missing", skills_dir=str(skills_dir))
        return []

    skill_files = sorted(
        path
        for path in skills_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in _MARKDOWN_EXTENSIONS
    )

    skills: list[SkillCatalogItem] = []
    for skill_file in skill_files:
        rel_path = skill_file.relative_to(skills_dir).as_posix()
        rel_stem = str(Path(rel_path).with_suffix(""))
        category = Path(rel_path).parts[0] if len(Path(rel_path).parts) > 1 else "general"
        fallback_name = skill_file.stem.replace("_", " ").replace("-", " ").strip().title() or "Skill"

        try:
            markdown = skill_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            markdown = skill_file.read_text(encoding="utf-8", errors="ignore")

        skills.append(
            SkillCatalogItem(
                id=_slugify(rel_stem, fallback="skill"),
                name=_markdown_title(markdown, fallback_name),
                summary=_markdown_summary(markdown, default_text="Skill markdown document"),
                iconKind=_SKILL_ICON_KIND_BY_CATEGORY.get(category, "file"),
                tools=_skill_tools_from_markdown(markdown),
                markdown=markdown,
                category=category,
                path=rel_path,
            )
        )
    return skills


def _normalize_model(model: str) -> str:
    return model.strip().lower()


def _default_model_settings_payload() -> dict[str, Any]:
    return {
        "active_provider": "openai",
        "providers": {
            "openai": {
                "enabled": True,
                "api_key": "",
                "base_url": "https://api.openai.com/v1",
                "main_model": settings.default_main_model,
                "note": "Official OpenAI API",
            },
            "anthropic": {
                "enabled": False,
                "api_key": "",
                "base_url": "https://api.anthropic.com",
                "main_model": "claude-3-opus-20240229",
                "note": "Anthropic / A-site provider",
            },
            "relay": {
                "enabled": False,
                "api_key": "",
                "base_url": "https://your-relay.example.com/v1",
                "main_model": settings.default_main_model,
                "note": "OpenAI-compatible relay gateway",
            },
        },
    }


def _normalized_model_settings_payload(
    payload: dict[str, Any] | None = None,
) -> ModelSettingsPayload:
    defaults = _default_model_settings_payload()
    active_provider = defaults["active_provider"]
    if isinstance(payload, dict):
        active_provider = str(payload.get("active_provider") or active_provider)

    providers_input = payload.get("providers") if isinstance(payload, dict) else None
    merged_providers: dict[ProviderId, ModelProviderSettings] = {}
    for provider_id in _MODEL_PROVIDER_IDS:
        default_provider = defaults["providers"][provider_id]
        incoming_provider = (
            providers_input.get(provider_id)
            if isinstance(providers_input, dict)
            else None
        )
        if not isinstance(incoming_provider, dict):
            incoming_provider = {}

        merged_providers[provider_id] = ModelProviderSettings(
            enabled=bool(incoming_provider.get("enabled", default_provider["enabled"])),
            api_key=str(incoming_provider.get("api_key", default_provider["api_key"]) or ""),
            base_url=str(incoming_provider.get("base_url", default_provider["base_url"]) or ""),
            main_model=str(
                incoming_provider.get("main_model", default_provider["main_model"])
                or default_provider["main_model"]
            ),
            note=str(incoming_provider.get("note", default_provider["note"]) or ""),
        )

    merged_providers["openai"].base_url = defaults["providers"]["openai"]["base_url"]
    merged_providers["anthropic"].base_url = defaults["providers"]["anthropic"]["base_url"]

    if active_provider not in _MODEL_PROVIDER_IDS:
        active_provider = "openai"

    return ModelSettingsPayload(
        active_provider=active_provider,  # type: ignore[arg-type]
        providers=merged_providers,
    )


def _supported_model_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for model in settings.supported_models:
        lookup[_normalize_model(model)] = model
    return lookup


def _resolve_task_model(model: str | None) -> str:
    supported_models = _supported_model_lookup()
    default_key = _normalize_model(settings.default_main_model)

    if default_key not in supported_models:
        logger.error(
            "invalid_default_model_config",
            default_model=settings.default_main_model,
            supported_models=settings.supported_models,
        )
        raise HTTPException(status_code=500, detail="Task model configuration is invalid")

    if model is None or not model.strip():
        return supported_models[default_key]

    model_key = _normalize_model(model)
    if model_key not in supported_models:
        raise HTTPException(
            status_code=422,
            detail={
                "message": f"Unsupported model: {model}",
                "supported_models": list(supported_models.values()),
            },
        )
    return supported_models[model_key]


async def _get_owned_task_or_404(
    task_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession,
) -> Task:
    result = await db.execute(
        select(Task)
        .join(Project, Task.project_id == Project.id)
        .where(
            Task.id == task_id,
            Project.owner_user_id == user.id,
        )
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


async def _ensure_owned_project_and_conversation(
    task: TaskCreate,
    user: CurrentUser,
    db: AsyncSession,
) -> Project:
    project_result = await db.execute(
        select(Project).where(
            Project.id == task.project_id,
            Project.owner_user_id == user.id,
        )
    )
    project = project_result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    conversation_result = await db.execute(
        select(Conversation).where(
            Conversation.id == task.conversation_id,
            Conversation.project_id == task.project_id,
        )
    )
    if conversation_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if task.rag_collection_id is not None:
        rag_result = await db.execute(
            select(RagCollection).where(
                RagCollection.id == task.rag_collection_id,
                RagCollection.owner_user_id == user.id,
            )
        )
        if rag_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="RAG collection not found")
    return project


async def _get_user_model_config(
    user: CurrentUser,
    db: AsyncSession,
) -> UserModelConfig | None:
    result = await db.execute(
        select(UserModelConfig).where(UserModelConfig.owner_user_id == user.id)
    )
    return result.scalar_one_or_none()


@router.get("/", response_model=list[TaskResponse])
async def list_tasks(
    conversation_id: uuid.UUID | None = Query(None),
    project_id: uuid.UUID | None = Query(None),
    queue_status: QueueStatus | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    query = (
        select(Task)
        .join(Project, Task.project_id == Project.id)
        .where(Project.owner_user_id == user.id)
    )
    if conversation_id:
        query = query.where(Task.conversation_id == conversation_id)
    if project_id:
        query = query.where(Task.project_id == project_id)
    if queue_status:
        query = query.where(Task.queue_status == queue_status)
    query = query.order_by(Task.priority.desc(), Task.scheduled_at.asc(), Task.created_at.asc())
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(
    task: TaskCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    project = await _ensure_owned_project_and_conversation(task=task, user=user, db=db)
    task_data = task.model_dump()
    if "rag_collection_id" not in task.model_fields_set:
        task_data["rag_collection_id"] = project.active_rag_collection_id
    task_data["model"] = _resolve_task_model(task.model)
    db_task = Task(**task_data)
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task


@router.get("/models", response_model=ModelCatalogResponse)
async def get_model_catalog():
    """Return default and supported models for task creation."""
    default_model = _resolve_task_model(None)
    return ModelCatalogResponse(
        default_model=default_model,
        supported_models=list(_supported_model_lookup().values()),
    )


@router.get("/model-settings", response_model=ModelSettingsResponse)
async def get_model_settings(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Return persisted model/provider settings for the current user."""
    config = await _get_user_model_config(user=user, db=db)
    if config is None:
        payload = _normalized_model_settings_payload()
        return ModelSettingsResponse(**payload.model_dump(), updated_at=None)

    payload = _normalized_model_settings_payload(
        {
            "active_provider": config.active_provider,
            "providers": config.providers_payload,
        }
    )
    return ModelSettingsResponse(**payload.model_dump(), updated_at=config.updated_at)


@router.put("/model-settings", response_model=ModelSettingsResponse)
async def put_model_settings(
    request: ModelSettingsPayload,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Persist model/provider settings for the current user."""
    normalized = _normalized_model_settings_payload(request.model_dump())
    config = await _get_user_model_config(user=user, db=db)

    if config is None:
        config = UserModelConfig(
            owner_user_id=user.id,
            active_provider=normalized.active_provider,
            providers_payload=normalized.model_dump()["providers"],
        )
        db.add(config)
    else:
        config.active_provider = normalized.active_provider
        config.providers_payload = normalized.model_dump()["providers"]

    await db.commit()
    await db.refresh(config)
    return ModelSettingsResponse(**normalized.model_dump(), updated_at=config.updated_at)


@router.get("/roles", response_model=list[RoleCatalogItem])
async def list_roles(
    _user: CurrentUser = Depends(get_current_user),
):
    """Return role markdown docs discovered from shared/roles."""
    roles_dir = Path(settings.roles_dir)
    try:
        return _build_role_catalog(roles_dir)
    except Exception as exc:
        logger.error(
            "roles_catalog_load_failed",
            roles_dir=str(roles_dir),
            error=str(exc),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to load roles catalog") from exc


@router.get("/skills", response_model=list[SkillCatalogItem])
async def list_skills(
    _user: CurrentUser = Depends(get_current_user),
):
    """Return skill markdown docs discovered from shared/skills."""
    skills_dir = Path(settings.skills_dir)
    try:
        return _build_skill_catalog(skills_dir)
    except Exception as exc:
        logger.error(
            "skills_catalog_load_failed",
            skills_dir=str(skills_dir),
            error=str(exc),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to load skills catalog") from exc


@router.get("/kanban", response_model=TaskKanbanResponse)
async def get_kanban_board(
    project_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    query = (
        select(Task)
        .join(Project, Task.project_id == Project.id)
        .where(Project.owner_user_id == user.id)
    )
    if project_id:
        query = query.where(Task.project_id == project_id)
    query = query.order_by(Task.priority.desc(), Task.scheduled_at.asc(), Task.created_at.asc())

    result = await db.execute(query)
    tasks = result.scalars().all()

    kanban = TaskKanbanResponse()
    for task in tasks:
        if task.queue_status == QueueStatus.SCHEDULED:
            kanban.scheduled.append(task)
        elif task.queue_status == QueueStatus.QUEUED:
            kanban.queued.append(task)
        elif task.queue_status == QueueStatus.IN_PROGRESS:
            kanban.in_progress.append(task)
        elif task.queue_status == QueueStatus.DONE:
            kanban.done.append(task)
    return kanban

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    task = await _get_owned_task_or_404(task_id=task_id, user=user, db=db)
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID,
    task_update: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    task = await _get_owned_task_or_404(task_id=task_id, user=user, db=db)
    for key, value in task_update.model_dump(exclude_unset=True).items():
        setattr(task, key, value)
    await db.commit()
    await db.refresh(task)
    return task

@router.patch("/{task_id}/queue-status", response_model=TaskResponse)
async def update_task_queue_status(
    task_id: uuid.UUID,
    queue_status: QueueStatus = Query(...),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    task = await _get_owned_task_or_404(task_id=task_id, user=user, db=db)

    task.queue_status = queue_status
    publish_run_id: uuid.UUID | None = None

    if queue_status == QueueStatus.IN_PROGRESS and not task.current_run_id:
        db_run = TaskRun(task_id=task_id, status=TaskStatus.PENDING)
        db.add(db_run)
        await db.flush()
        task.current_run_id = db_run.id
        publish_run_id = db_run.id

    await db.commit()

    if publish_run_id is not None:
        try:
            await queue_service.publish_task_run(publish_run_id)
        except Exception as exc:
            logger.error(
                "task_queue_status_publish_failed",
                task_id=str(task_id),
                task_run_id=str(publish_run_id),
                error=str(exc),
                exc_info=True,
            )
            run_result = await db.execute(select(TaskRun).where(TaskRun.id == publish_run_id))
            db_run = run_result.scalar_one_or_none()
            if db_run:
                db_run.status = TaskStatus.FAILED
                db_run.error_message = "queue_publish_failed"
                task.current_run_id = None
                await db.commit()
            raise HTTPException(status_code=503, detail="Task run queue unavailable") from exc

    await db.refresh(task)
    logger.info("task_queue_status_updated", task_id=str(task_id), new_status=queue_status.value)
    return task

@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    task = await _get_owned_task_or_404(task_id=task_id, user=user, db=db)
    await db.delete(task)
    await db.commit()


@router.get("/{task_id}/runs", response_model=list[TaskRunResponse])
async def list_task_runs(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    await _get_owned_task_or_404(task_id=task_id, user=user, db=db)
    result = await db.execute(
        select(TaskRun).where(TaskRun.task_id == task_id).order_by(TaskRun.created_at.desc())
    )
    return result.scalars().all()


@router.post("/{task_id}/runs", response_model=TaskRunResponse, status_code=201)
async def create_task_run(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    task = await _get_owned_task_or_404(task_id=task_id, user=user, db=db)
    db_run = TaskRun(task_id=task_id, status=TaskStatus.PENDING)
    db.add(db_run)
    await db.flush()
    task.current_run_id = db_run.id
    await db.commit()
    await db.refresh(db_run)
    try:
        await queue_service.publish_task_run(db_run.id)
    except Exception as exc:
        logger.error(
            "task_run_publish_failed",
            task_id=str(task_id),
            task_run_id=str(db_run.id),
            error=str(exc),
            exc_info=True,
        )
        db_run.status = TaskStatus.FAILED
        db_run.error_message = "queue_publish_failed"
        task.current_run_id = None
        await db.commit()
        await db.refresh(db_run)
        raise HTTPException(status_code=503, detail="Task run queue unavailable") from exc
    return db_run


@router.post("/{task_id}/retry", response_model=TaskRunResponse, status_code=201)
async def retry_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Create a new run for an existing task."""
    return await create_task_run(task_id=task_id, db=db, user=user)
