"""Artifact API endpoints."""
from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import io
from urllib.parse import quote
from app.database import get_db
from app.models.artifact import Artifact, ArtifactType
from app.models.project import ProjectNode, NodeType
from app.schemas.artifact import ArtifactResponse
from app.services.storage import storage_service

router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])

# File upload limits
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


@router.get("/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(artifact_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get artifact metadata."""
    result = await db.execute(select(Artifact).where(Artifact.id == artifact_id))
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact


@router.post("/upload", response_model=ArtifactResponse, status_code=201)
async def upload_artifact(
    project_id: uuid.UUID,
    task_run_id: uuid.UUID,
    artifact_type: ArtifactType = Query(default=ArtifactType.FILE),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload artifact file."""
    artifact_id = uuid.uuid4()
    object_name = f"{project_id}/{task_run_id}/{artifact_id}/{file.filename}"

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB")

    await storage_service.upload_file(object_name, content, file.content_type or "application/octet-stream")

    artifact = Artifact(
        id=artifact_id,
        project_id=project_id,
        task_run_id=task_run_id,
        name=file.filename,
        artifact_type=artifact_type,
        storage_path=object_name,
        size=len(content),
        mime_type=file.content_type
    )
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)
    return artifact


@router.get("/{artifact_id}/download")
async def download_artifact(artifact_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Download artifact file."""
    result = await db.execute(select(Artifact).where(Artifact.id == artifact_id))
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    data = await storage_service.download_file(artifact.storage_path)
    return StreamingResponse(
        io.BytesIO(data),
        media_type=artifact.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{quote(artifact.name)}"'}
    )


@router.get("/list/project/{project_id}", response_model=list[ArtifactResponse])
async def list_project_artifacts(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """List artifacts for a project."""
    result = await db.execute(
        select(Artifact).where(Artifact.project_id == project_id).order_by(Artifact.created_at.desc())
    )
    return result.scalars().all()


@router.get("/list/run/{run_id}", response_model=list[ArtifactResponse])
async def list_run_artifacts(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """List artifacts produced by a run."""
    result = await db.execute(
        select(Artifact).where(Artifact.task_run_id == run_id).order_by(Artifact.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/{artifact_id}", status_code=204)
async def delete_artifact(artifact_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Delete artifact."""
    result = await db.execute(select(Artifact).where(Artifact.id == artifact_id))
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    # Delete database record first to maintain consistency
    storage_path = artifact.storage_path
    await db.delete(artifact)
    await db.commit()

    # Then delete from storage (if this fails, record is already gone)
    await storage_service.delete_file(storage_path)


@router.post("/{artifact_id}/save-to-project")
async def save_artifact_to_project(artifact_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Persist an artifact as a project file node."""
    result = await db.execute(select(Artifact).where(Artifact.id == artifact_id))
    artifact = result.scalar_one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    node_id = uuid.uuid4()
    source_name = PurePosixPath(artifact.storage_path).name
    target_object_name = f"projects/{artifact.project_id}/saved-artifacts/{node_id}/{source_name}"
    await storage_service.copy_file(artifact.storage_path, target_object_name)

    node = ProjectNode(
        id=node_id,
        project_id=artifact.project_id,
        name=artifact.name,
        path=target_object_name,
        node_type=NodeType.FILE,
        size=artifact.size,
    )
    db.add(node)
    await db.commit()
    await db.refresh(node)

    return {
        "id": str(node.id),
        "project_id": str(node.project_id),
        "name": node.name,
        "path": node.path,
        "size": node.size,
    }
