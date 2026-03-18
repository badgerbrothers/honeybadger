"""Projects API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import structlog
from pathlib import Path
from app.database import get_db
from app.models.artifact import Artifact
from app.models.project import Project, ProjectNode, NodeType
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectNodeResponse, ProjectFileUploadResponse
from app.schemas.artifact import ArtifactResponse
from app.services.rag_service import rag_service
from app.services.storage import storage_service

logger = structlog.get_logger()
router = APIRouter(prefix="/api/projects", tags=["projects"])

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'.txt', '.md', '.markdown', '.pdf', '.json', '.csv'}

@router.get("/", response_model=list[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project))
    projects = result.scalars().all()
    return projects

@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(project: ProjectCreate, db: AsyncSession = Depends(get_db)):
    db_project = Project(**project.model_dump())
    db.add(db_project)
    await db.commit()
    await db.refresh(db_project)
    return db_project

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: uuid.UUID, project_update: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    for key, value in project_update.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    await db.commit()
    await db.refresh(project)
    return project

@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(project)
    await db.commit()

@router.post("/{project_id}/files/upload", response_model=ProjectFileUploadResponse, status_code=201)
async def upload_project_file(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload file to project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Supported: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
        )

    file_id = uuid.uuid4()
    object_name = f"projects/{project_id}/files/{file_id}/{file.filename}"

    try:
        node = ProjectNode(
            id=file_id,
            project_id=project_id,
            name=file.filename,
            path=object_name,
            node_type=NodeType.FILE,
            size=len(content)
        )
        db.add(node)
        await db.flush()

        await storage_service.upload_file(
            object_name,
            content,
            file.content_type or "application/octet-stream"
        )

        await db.commit()
        await db.refresh(node)
        await rag_service.schedule_indexing(
            project_id=project_id,
            project_node_id=node.id,
            storage_path=node.path,
            file_name=node.name,
            db=db,
        )

        return {
            "id": node.id,
            "project_id": node.project_id,
            "name": node.name,
            "path": node.path,
            "size": node.size,
            "mime_type": file.content_type,
            "created_at": node.created_at
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"File upload failed: {e}", project_id=str(project_id), filename=file.filename)
        raise HTTPException(status_code=503, detail="File storage service unavailable")

@router.get("/{project_id}/files", response_model=list[ProjectNodeResponse])
async def list_project_files(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """List all files in a project."""
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
    db: AsyncSession = Depends(get_db)
):
    """Delete a project file."""
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
async def list_project_artifacts(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """List artifacts for a project."""
    result = await db.execute(
        select(Artifact).where(Artifact.project_id == project_id).order_by(Artifact.created_at.desc())
    )
    return result.scalars().all()
