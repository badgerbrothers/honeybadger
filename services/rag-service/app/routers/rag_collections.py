"""Global RAG collection CRUD and file upload APIs."""
from __future__ import annotations

import uuid
from pathlib import Path
from math import ceil

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import settings
from app.models.rag_collection import RagCollection
from app.models.rag_collection_file import RagCollectionFile, RagFileStatus
from app.models.rag_upload_session import RagUploadSession, RagUploadSessionStatus
from app.schemas.rag_collection import (
    RagCollectionCreate,
    RagCollectionResponse,
    RagCollectionUpdate,
)
from app.schemas.rag_file import RagFilePreviewResponse, RagFileResponse, RagFileUploadResponse
from app.schemas.rag_multipart_upload import (
    RagMultipartUploadCompleteRequest,
    RagMultipartUploadCreateRequest,
    RagMultipartUploadCreateResponse,
    RagMultipartUploadPartUrl,
)
from app.security.auth import CurrentUser, get_current_user
from app.services.index_job_service import index_job_service
from app.services.storage import storage_service

router = APIRouter(prefix="/api/rags", tags=["rag_collections"])
logger = structlog.get_logger(__name__)

ALLOWED_EXTENSIONS = {".txt", ".md", ".markdown", ".pdf", ".json", ".csv"}
TEXT_PREVIEW_EXTENSIONS = {".txt", ".md", ".markdown", ".json", ".csv"}
DEFAULT_PREVIEW_BYTES = 1024 * 1024


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


def _max_upload_size_for_extension(file_ext: str) -> int:
    if file_ext == ".pdf":
        return settings.rag_pdf_upload_max_bytes
    return settings.rag_upload_max_bytes


def _validate_upload_name_and_size(file_name: str, file_size: int) -> tuple[str, int]:
    file_ext = Path(file_name).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    max_file_size = _max_upload_size_for_extension(file_ext)
    if file_size > max_file_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {_format_limit(max_file_size)}",
        )
    return file_ext, max_file_size


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


@router.get("/{rag_id}/files/{file_id}/preview", response_model=RagFilePreviewResponse)
async def preview_rag_file(
    rag_id: uuid.UUID,
    file_id: uuid.UUID,
    max_bytes: int = DEFAULT_PREVIEW_BYTES,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    await _get_owned_rag_or_404(rag_id=rag_id, user=user, db=db)
    result = await db.execute(
        select(RagCollectionFile).where(
            RagCollectionFile.id == file_id,
            RagCollectionFile.rag_collection_id == rag_id,
        )
    )
    rag_file = result.scalar_one_or_none()
    if rag_file is None:
        raise HTTPException(status_code=404, detail="RAG file not found")

    file_ext = Path(rag_file.file_name).suffix.lower()
    if file_ext not in TEXT_PREVIEW_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Preview is only supported for text-like files")

    preview_bytes = max(1024, min(max_bytes, DEFAULT_PREVIEW_BYTES))
    payload = await storage_service.download_file_range(
        rag_file.storage_path,
        offset=0,
        length=preview_bytes,
    )
    return RagFilePreviewResponse(
        file_id=rag_file.id,
        file_name=rag_file.file_name,
        mime_type=rag_file.mime_type,
        content=payload.decode("utf-8", errors="replace"),
        truncated=rag_file.file_size > len(payload),
    )


@router.post(
    "/{rag_id}/files/multipart",
    response_model=RagMultipartUploadCreateResponse,
    status_code=201,
)
async def create_rag_file_multipart_upload(
    rag_id: uuid.UUID,
    payload: RagMultipartUploadCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    await _get_owned_rag_or_404(rag_id=rag_id, user=user, db=db)

    file_name = payload.file_name.strip() or "uploaded-file"
    file_size = payload.file_size
    _validate_upload_name_and_size(file_name, file_size)

    file_id = uuid.uuid4()
    object_name = f"rags/{rag_id}/files/{file_id}/{file_name}"
    part_size = settings.s3_multipart_part_size
    part_count = max(1, ceil(file_size / part_size))

    try:
        upload_id = await storage_service.create_multipart_upload(
            object_name=object_name,
            content_type=payload.mime_type or "application/octet-stream",
        )
        session = RagUploadSession(
            file_id=file_id,
            rag_collection_id=rag_id,
            owner_user_id=user.id,
            storage_path=object_name,
            file_name=file_name,
            file_size=file_size,
            mime_type=payload.mime_type,
            upload_id=upload_id,
            part_size=part_size,
            part_count=part_count,
            status=RagUploadSessionStatus.INITIATED,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        part_urls = []
        for part_number in range(1, part_count + 1):
            url = await storage_service.get_presigned_multipart_part_url(
                object_name=object_name,
                upload_id=upload_id,
                part_number=part_number,
                expires_seconds=settings.rag_multipart_url_expiry_seconds,
            )
            part_urls.append(RagMultipartUploadPartUrl(part_number=part_number, url=url))

        return RagMultipartUploadCreateResponse(
            upload_session_id=session.id,
            file_id=file_id,
            storage_path=object_name,
            upload_id=upload_id,
            part_size=part_size,
            part_count=part_count,
            expires_in_seconds=settings.rag_multipart_url_expiry_seconds,
            parts=part_urls,
        )
    except Exception as exc:
        await db.rollback()
        logger.error(
            "rag_multipart_upload_create_failed",
            rag_collection_id=str(rag_id),
            file_name=file_name,
            error=str(exc),
            exc_info=True,
        )
        raise HTTPException(status_code=503, detail="RAG multipart upload initialization failed") from exc


@router.post(
    "/{rag_id}/files/multipart/complete",
    response_model=RagFileUploadResponse,
    status_code=201,
)
async def complete_rag_file_multipart_upload(
    rag_id: uuid.UUID,
    payload: RagMultipartUploadCompleteRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    await _get_owned_rag_or_404(rag_id=rag_id, user=user, db=db)

    result = await db.execute(
        select(RagUploadSession).where(
            RagUploadSession.id == payload.upload_session_id,
            RagUploadSession.rag_collection_id == rag_id,
            RagUploadSession.owner_user_id == user.id,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Multipart upload session not found")
    if session.status == RagUploadSessionStatus.COMPLETED:
        existing_result = await db.execute(
            select(RagCollectionFile).where(RagCollectionFile.id == session.file_id)
        )
        existing_file = existing_result.scalar_one_or_none()
        if existing_file is None:
            raise HTTPException(status_code=409, detail="Multipart upload already finalized")
        return RagFileUploadResponse(
            **RagFileResponse.model_validate(existing_file).model_dump(),
            index_job_id=None,
        )
    if session.status != RagUploadSessionStatus.INITIATED:
        raise HTTPException(status_code=409, detail="Multipart upload session is not active")

    try:
        await storage_service.complete_multipart_upload(
            object_name=session.storage_path,
            upload_id=session.upload_id,
            parts=[(part.part_number, part.etag) for part in payload.parts],
        )
        stat = await storage_service.stat_file(session.storage_path)
        actual_size = int(getattr(stat, "size", session.file_size) or session.file_size)
        _validate_upload_name_and_size(session.file_name, actual_size)
        if actual_size != session.file_size:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file size does not match the initialized upload session",
            )

        rag_file = RagCollectionFile(
            id=session.file_id,
            rag_collection_id=rag_id,
            storage_path=session.storage_path,
            file_name=session.file_name,
            file_size=actual_size,
            mime_type=session.mime_type,
            status=RagFileStatus.PENDING,
        )
        db.add(rag_file)
        session.status = RagUploadSessionStatus.COMPLETED
        await db.commit()
        await db.refresh(rag_file)

        index_job = await index_job_service.schedule_indexing(
            db=db,
            rag_collection_id=rag_id,
            storage_path=session.storage_path,
            file_name=session.file_name,
        )
        return RagFileUploadResponse(
            **RagFileResponse.model_validate(rag_file).model_dump(),
            index_job_id=index_job.id,
        )
    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        try:
            session.status = RagUploadSessionStatus.FAILED
            await db.commit()
        except Exception:
            await db.rollback()
        logger.error(
            "rag_multipart_upload_complete_failed",
            rag_collection_id=str(rag_id),
            upload_session_id=str(payload.upload_session_id),
            error=str(exc),
            exc_info=True,
        )
        raise HTTPException(status_code=503, detail="RAG multipart upload finalization failed") from exc


@router.delete(
    "/{rag_id}/files/multipart/{upload_session_id}",
    status_code=204,
)
async def abort_rag_file_multipart_upload(
    rag_id: uuid.UUID,
    upload_session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    await _get_owned_rag_or_404(rag_id=rag_id, user=user, db=db)

    result = await db.execute(
        select(RagUploadSession).where(
            RagUploadSession.id == upload_session_id,
            RagUploadSession.rag_collection_id == rag_id,
            RagUploadSession.owner_user_id == user.id,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Multipart upload session not found")
    if session.status == RagUploadSessionStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="Multipart upload already completed")
    if session.status == RagUploadSessionStatus.ABORTED:
        return None

    try:
        await storage_service.abort_multipart_upload(
            object_name=session.storage_path,
            upload_id=session.upload_id,
        )
    except Exception:
        logger.warning(
            "rag_multipart_upload_abort_failed",
            rag_collection_id=str(rag_id),
            upload_session_id=str(upload_session_id),
            exc_info=True,
        )

    session.status = RagUploadSessionStatus.ABORTED
    await db.commit()
    return None
