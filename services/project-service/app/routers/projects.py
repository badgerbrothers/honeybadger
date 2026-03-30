"""Projects API endpoints."""
from math import ceil
from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.database import get_db
from app.models.artifact import Artifact
from app.models.project import Project, ProjectNode, NodeType
from app.models.project_upload_session import ProjectUploadSession, ProjectUploadSessionStatus
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectNodeResponse,
    ProjectFileUploadResponse,
    ProjectMultipartUploadCreateRequest,
    ProjectMultipartUploadCreateResponse,
    ProjectMultipartUploadPartUrl,
    ProjectMultipartUploadCompleteRequest,
)
from app.schemas.artifact import ArtifactResponse
from app.security.auth import CurrentUser, get_current_user
from app.config import settings
from app.services.rag_client import rag_client
from app.services.storage import storage_service

logger = structlog.get_logger()
router = APIRouter(prefix="/api/projects", tags=["projects"])

MAX_FILE_SIZE = 10 * 1024 * 1024 * 1024  # 10GB
ALLOWED_EXTENSIONS = {'.txt', '.md', '.markdown', '.pdf', '.json', '.csv'}


def _format_limit(limit_bytes: int) -> str:
    gib = 1024 * 1024 * 1024
    mib = 1024 * 1024
    kib = 1024
    if limit_bytes >= gib:
        return f"{limit_bytes // gib}GB"
    if limit_bytes >= mib:
        return f"{limit_bytes // mib}MB"
    if limit_bytes >= kib:
        return f"{limit_bytes // kib}KB"
    return f"{limit_bytes}B"


async def _get_owned_project_or_404(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession,
) -> Project:
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_user_id == user.id,
        )
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _validate_project_upload(file_name: str, file_size: int) -> None:
    file_ext = Path(file_name).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Supported: {', '.join(ALLOWED_EXTENSIONS)}",
        )
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {_format_limit(MAX_FILE_SIZE)}",
        )


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    result = await db.execute(select(Project).where(Project.owner_user_id == user.id))
    projects = result.scalars().all()
    return projects


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    project: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    db_project = Project(**project.model_dump(), owner_user_id=user.id)
    db.add(db_project)
    await db.commit()
    await db.refresh(db_project)
    return db_project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    project = await _get_owned_project_or_404(project_id=project_id, user=user, db=db)
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: uuid.UUID,
    project_update: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    project = await _get_owned_project_or_404(project_id=project_id, user=user, db=db)
    for key, value in project_update.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    project = await _get_owned_project_or_404(project_id=project_id, user=user, db=db)
    await db.delete(project)
    await db.commit()


@router.post("/{project_id}/files/multipart", response_model=ProjectMultipartUploadCreateResponse, status_code=201)
async def create_project_file_multipart_upload(
    project_id: uuid.UUID,
    payload: ProjectMultipartUploadCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    await _get_owned_project_or_404(project_id=project_id, user=user, db=db)

    file_name = payload.file_name.strip() or "uploaded-file"
    _validate_project_upload(file_name, payload.file_size)

    file_id = uuid.uuid4()
    object_name = f"projects/{project_id}/files/{file_id}/{file_name}"
    part_size = settings.s3_multipart_part_size
    part_count = max(1, ceil(payload.file_size / part_size))

    try:
        upload_id = await storage_service.create_multipart_upload(
            object_name=object_name,
            content_type=payload.mime_type or "application/octet-stream",
        )
        session = ProjectUploadSession(
            file_id=file_id,
            project_id=project_id,
            owner_user_id=user.id,
            storage_path=object_name,
            file_name=file_name,
            file_size=payload.file_size,
            mime_type=payload.mime_type,
            upload_id=upload_id,
            part_size=part_size,
            part_count=part_count,
            status=ProjectUploadSessionStatus.INITIATED,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        parts = []
        for part_number in range(1, part_count + 1):
            url = await storage_service.get_presigned_multipart_part_url(
                object_name=object_name,
                upload_id=upload_id,
                part_number=part_number,
            )
            parts.append(ProjectMultipartUploadPartUrl(part_number=part_number, url=url))

        return ProjectMultipartUploadCreateResponse(
            upload_session_id=session.id,
            file_id=file_id,
            path=object_name,
            upload_id=upload_id,
            part_size=part_size,
            part_count=part_count,
            expires_in_seconds=settings.project_multipart_url_expiry_seconds,
            parts=parts,
        )
    except Exception as exc:
        await db.rollback()
        logger.error("project_multipart_upload_create_failed", project_id=str(project_id), error=str(exc), exc_info=True)
        raise HTTPException(status_code=503, detail="Project multipart upload initialization failed") from exc


@router.post("/{project_id}/files/multipart/complete", response_model=ProjectFileUploadResponse, status_code=201)
async def complete_project_file_multipart_upload(
    project_id: uuid.UUID,
    payload: ProjectMultipartUploadCompleteRequest,
    authorization: str = Header(..., alias="Authorization"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    project = await _get_owned_project_or_404(project_id=project_id, user=user, db=db)
    result = await db.execute(
        select(ProjectUploadSession).where(
            ProjectUploadSession.id == payload.upload_session_id,
            ProjectUploadSession.project_id == project_id,
            ProjectUploadSession.owner_user_id == user.id,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Project multipart upload session not found")
    if session.status == ProjectUploadSessionStatus.COMPLETED:
        existing_result = await db.execute(
            select(ProjectNode).where(
                ProjectNode.id == session.file_id,
                ProjectNode.project_id == project_id,
                ProjectNode.node_type == NodeType.FILE,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing is None:
            raise HTTPException(status_code=409, detail="Project multipart upload already finalized")
        return {
            "id": existing.id,
            "project_id": existing.project_id,
            "name": existing.name,
            "path": existing.path,
            "size": existing.size,
            "mime_type": session.mime_type,
            "created_at": existing.created_at,
        }
    if session.status != ProjectUploadSessionStatus.INITIATED:
        raise HTTPException(status_code=409, detail="Project multipart upload session is not active")

    try:
        await storage_service.complete_multipart_upload(
            object_name=session.storage_path,
            upload_id=session.upload_id,
            parts=[(part.part_number, part.etag) for part in payload.parts],
        )
        stat = await storage_service.stat_file(session.storage_path)
        actual_size = int(getattr(stat, "size", session.file_size) or session.file_size)
        _validate_project_upload(session.file_name, actual_size)
        if actual_size != session.file_size:
            raise HTTPException(status_code=400, detail="Uploaded file size does not match the initialized upload session")

        node = ProjectNode(
            id=session.file_id,
            project_id=project_id,
            name=session.file_name,
            path=session.storage_path,
            node_type=NodeType.FILE,
            size=actual_size,
        )
        db.add(node)
        session.status = ProjectUploadSessionStatus.COMPLETED
        await db.commit()
        await db.refresh(node)

        if project.active_rag_collection_id:
            await rag_client.schedule_indexing(
                project_id=project_id,
                node_id=node.id,
                authorization_header=authorization,
            )
        else:
            logger.info(
                "project_file_index_skipped_no_active_rag",
                project_id=str(project_id),
                node_id=str(node.id),
            )

        return {
            "id": node.id,
            "project_id": node.project_id,
            "name": node.name,
            "path": node.path,
            "size": node.size,
            "mime_type": session.mime_type,
            "created_at": node.created_at,
        }
    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        try:
            session.status = ProjectUploadSessionStatus.FAILED
            await db.commit()
        except Exception:
            await db.rollback()
        logger.error("project_multipart_upload_complete_failed", project_id=str(project_id), error=str(exc), exc_info=True)
        raise HTTPException(status_code=503, detail="Project multipart upload finalization failed") from exc


@router.delete("/{project_id}/files/multipart/{upload_session_id}", status_code=204)
async def abort_project_file_multipart_upload(
    project_id: uuid.UUID,
    upload_session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    await _get_owned_project_or_404(project_id=project_id, user=user, db=db)
    result = await db.execute(
        select(ProjectUploadSession).where(
            ProjectUploadSession.id == upload_session_id,
            ProjectUploadSession.project_id == project_id,
            ProjectUploadSession.owner_user_id == user.id,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Project multipart upload session not found")
    if session.status == ProjectUploadSessionStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="Project multipart upload already completed")
    if session.status == ProjectUploadSessionStatus.ABORTED:
        return None

    try:
        await storage_service.abort_multipart_upload(session.storage_path, session.upload_id)
    except Exception:
        logger.warning("project_multipart_upload_abort_failed", project_id=str(project_id), upload_session_id=str(upload_session_id), exc_info=True)

    session.status = ProjectUploadSessionStatus.ABORTED
    await db.commit()
    return None

@router.get("/{project_id}/files", response_model=list[ProjectNodeResponse])
async def list_project_files(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """List all files in a project."""
    await _get_owned_project_or_404(project_id=project_id, user=user, db=db)
    result = await db.execute(
        select(ProjectNode)
        .where(ProjectNode.project_id == project_id)
        .where(ProjectNode.node_type == NodeType.FILE)
        .order_by(ProjectNode.created_at.desc())
    )
    files = result.scalars().all()
    return files

@router.delete("/{project_id}/files/{file_id}", status_code=204)
async def delete_project_file(
    project_id: uuid.UUID,
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Delete a project file."""
    await _get_owned_project_or_404(project_id=project_id, user=user, db=db)
    result = await db.execute(
        select(ProjectNode)
        .where(ProjectNode.id == file_id)
        .where(ProjectNode.project_id == project_id)
        .where(ProjectNode.node_type == NodeType.FILE)
    )
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="File not found")

    storage_path = node.path

    await db.delete(node)
    await db.commit()

    try:
        await storage_service.delete_file(storage_path)
    except Exception as e:
        logger.warning(f"Failed to delete file from storage: {e}", path=storage_path)


@router.get("/{project_id}/artifacts", response_model=list[ArtifactResponse])
async def list_project_artifacts(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """List artifacts for a project."""
    await _get_owned_project_or_404(project_id=project_id, user=user, db=db)
    result = await db.execute(
        select(Artifact).where(Artifact.project_id == project_id).order_by(Artifact.created_at.desc())
    )
    return result.scalars().all()
