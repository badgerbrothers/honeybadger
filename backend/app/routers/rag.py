"""RAG API endpoints."""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_db
from app.services.rag_service import rag_service

router = APIRouter(prefix="/api/projects", tags=["rag"])


class IndexRequest(BaseModel):
    node_id: uuid.UUID


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    threshold: float = 0.7


@router.post("/{project_id}/documents/index")
async def index_document(
    project_id: uuid.UUID,
    request: IndexRequest,
    db: AsyncSession = Depends(get_db)
):
    """Index a document for RAG retrieval."""
    job = await rag_service.requeue_node(project_id, request.node_id, db)
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
    db: AsyncSession = Depends(get_db)
):
    """Search for similar document chunks."""
    chunks = await rag_service.search(
        project_id=project_id,
        query=request.query,
        top_k=request.top_k,
        threshold=request.threshold,
        db=db,
    )
    return {"chunks": chunks, "query": request.query}


@router.get("/{project_id}/chunks")
async def list_chunks(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """List all indexed chunks for a project."""
    return await rag_service.list_chunks(project_id, db)


@router.delete("/{project_id}/chunks/{chunk_id}", status_code=204)
async def delete_chunk(
    project_id: uuid.UUID, chunk_id: int, db: AsyncSession = Depends(get_db)
):
    """Delete a document chunk."""
    deleted = await rag_service.delete_chunk(project_id, chunk_id, db)
    if not deleted:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return None
