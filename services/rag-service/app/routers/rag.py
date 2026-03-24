"""RAG API endpoints."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db
from app.models.project import Project
from app.security.auth import CurrentUser, get_current_user
from app.services.index_job_service import index_job_service
from app.services.search_service import search_service

router = APIRouter(prefix="/api/rag/projects", tags=["rag"])


class IndexRequest(BaseModel):
    node_id: uuid.UUID


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    threshold: float = 0.7


async def _ensure_owned_project_or_404(
    project_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession,
) -> None:
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.owner_user_id == user.id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Project not found")


@router.post("/{project_id}/documents/index")
async def index_document(
    project_id: uuid.UUID,
    request: IndexRequest,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Index a document for RAG retrieval."""
    await _ensure_owned_project_or_404(project_id=project_id, user=user, db=db)
    job = await index_job_service.requeue_node(project_id, request.node_id, db)
    if job is None:
        raise HTTPException(status_code=404, detail="Project file not found")
    return {
        "job_id": str(job.id),
        "status": job.status.value,
        "project_id": str(project_id),
        "node_id": str(request.node_id),
    }


@router.post("/{project_id}/search")
async def search_chunks(
    project_id: uuid.UUID,
    request: SearchRequest,
    use_hybrid: bool = Query(True, description="Enable vector + full-text hybrid search"),
    use_reranker: bool = Query(True, description="Enable cross-encoder reranking"),
    use_query_rewrite: bool = Query(False, description="Enable LLM query rewriting"),
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Search for similar document chunks."""
    await _ensure_owned_project_or_404(project_id=project_id, user=user, db=db)
    chunks = await search_service.search(
        project_id=project_id,
        query=request.query,
        top_k=request.top_k,
        threshold=request.threshold,
        db=db,
        use_hybrid=use_hybrid,
        use_reranker=use_reranker,
        use_query_rewrite=use_query_rewrite,
    )
    return {
        "chunks": chunks,
        "query": request.query,
        "options": {
            "use_hybrid": use_hybrid,
            "use_reranker": use_reranker,
            "use_query_rewrite": use_query_rewrite,
        },
    }


@router.get("/{project_id}/chunks")
async def list_chunks(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """List all indexed chunks for a project."""
    await _ensure_owned_project_or_404(project_id=project_id, user=user, db=db)
    return await search_service.list_chunks(project_id, db)


@router.delete("/{project_id}/chunks/{chunk_id}", status_code=204)
async def delete_chunk(
    project_id: uuid.UUID,
    chunk_id: int,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """Delete a document chunk."""
    await _ensure_owned_project_or_404(project_id=project_id, user=user, db=db)
    deleted = await search_service.delete_chunk(project_id, chunk_id, db)
    if not deleted:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return None
