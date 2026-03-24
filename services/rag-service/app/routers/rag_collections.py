"""Global RAG collection CRUD and file upload APIs."""
from __future__ import annotations

import uuid
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.rag_collection import RagCollection
from app.models.rag_collection_file import RagCollectionFile, RagFileStatus
from app.schemas.rag_collection import (
    RagCollectionCreate,
    RagCollectionResponse,
    RagCollectionUpdate,
)
from app.schemas.rag_file import RagFileResponse, RagFileUploadResponse
from app.security.auth import CurrentUser, get_current_user
from app.services.index_job_service import index_job_service
from app.services.storage import storage_service

router = APIRouter(prefix="/api/rags", tags=["rag_collections"])
logger = structlog.get_logger(__name__)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {".txt", ".md", ".markdown", ".pdf", ".json", ".csv"}


async def _get_owned_rag_or_404(
    rag_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession,
) -> RagCollection:
    result = await db.execute(
        select(RagCollection).where(
            RagCollection.id == rag_id,
            RagCollection.owner_user_id == user.id,
        )
    )
    rag = result.scalar_one_or_none()
    if rag is None:
        raise HTTPException(status_code=404, detail="RAG collection not found")
    return rag


@router.get("/", response_model=list[RagCollectionResponse])
async def list_rag_collections(
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    result = await db.execute(
        select(RagCollection)
        .where(RagCollection.owner_user_id == user.id)
        .order_by(RagCollection.updated_at.desc())
    )
    return result.scalars().all()


@router.post("/", response_model=RagCollectionResponse, status_code=201)
async def create_rag_collection(
    payload: RagCollectionCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    rag = RagCollection(**payload.model_dump(), owner_user_id=user.id)
    db.add(rag)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="RAG collection name already exists")
    await db.refresh(rag)
    return rag


@router.get("/{rag_id}", response_model=RagCollectionResponse)
async def get_rag_collection(
    rag_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    rag = await _get_owned_rag_or_404(rag_id=rag_id, user=user, db=db)
    return rag


@router.patch("/{rag_id}", response_model=RagCollectionResponse)
async def update_rag_collection(
    rag_id: uuid.UUID,
    payload: RagCollectionUpdate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    rag = await _get_owned_rag_or_404(rag_id=rag_id, user=user, db=db)

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(rag, key, value)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="RAG collection name already exists")
    await db.refresh(rag)
    return rag


@router.delete("/{rag_id}", status_code=204)
async def delete_rag_collection(
    rag_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    rag = await _get_owned_rag_or_404(rag_id=rag_id, user=user, db=db)
    await db.delete(rag)
    await db.commit()
    return None


@router.get("/{rag_id}/files", response_model=list[RagFileResponse])
async def list_rag_files(
    rag_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    await _get_owned_rag_or_404(rag_id=rag_id, user=user, db=db)
    result = await db.execute(
        select(RagCollectionFile)
        .where(RagCollectionFile.rag_collection_id == rag_id)
        .order_by(RagCollectionFile.created_at.desc())
    )
    return result.scalars().all()


@router.post("/{rag_id}/files/upload", response_model=RagFileUploadResponse, status_code=201)
async def upload_rag_file(
    rag_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    await _get_owned_rag_or_404(rag_id=rag_id, user=user, db=db)

    file_name = file.filename or "uploaded-file"
    file_ext = Path(file_name).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    file_id = uuid.uuid4()
    object_name = f"rags/{rag_id}/files/{file_id}/{file_name}"

    rag_file = RagCollectionFile(
        id=file_id,
        rag_collection_id=rag_id,
        storage_path=object_name,
        file_name=file_name,
        file_size=len(content),
        mime_type=file.content_type,
        status=RagFileStatus.PENDING,
    )
    db.add(rag_file)

    try:
        await storage_service.upload_file(
            object_name=object_name,
            data=content,
            content_type=file.content_type or "application/octet-stream",
        )
        await db.commit()
        await db.refresh(rag_file)

        index_job = await index_job_service.schedule_indexing(
            db=db,
            rag_collection_id=rag_id,
            storage_path=object_name,
            file_name=file_name,
        )
        return RagFileUploadResponse(
            **RagFileResponse.model_validate(rag_file).model_dump(),
            index_job_id=index_job.id,
        )
    except Exception as exc:
        await db.rollback()
        try:
            file_result = await db.execute(
                select(RagCollectionFile).where(RagCollectionFile.id == file_id)
            )
            existing_file = file_result.scalar_one_or_none()
            if existing_file is not None:
                existing_file.status = RagFileStatus.FAILED
                existing_file.error_message = str(exc)
                await db.commit()
        except Exception:
            await db.rollback()
        logger.error(
            "rag_file_upload_failed",
            rag_collection_id=str(rag_id),
            file_name=file_name,
            error=str(exc),
            exc_info=True,
        )
        raise HTTPException(status_code=503, detail="RAG file upload failed") from exc
