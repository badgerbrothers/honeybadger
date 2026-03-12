"""RAG API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db
from app.models.document_chunk import DocumentChunk

router = APIRouter(prefix="/api/projects", tags=["rag"])


class IndexRequest(BaseModel):
    file_path: str
    content: str


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    threshold: float = 0.7


@router.post("/{project_id}/documents/index")
async def index_document(
    project_id: str,
    request: IndexRequest,
    db: AsyncSession = Depends(get_db)
):
    """Index a document for RAG retrieval."""
    # TODO: Integrate with worker indexer
    return {"message": "Indexing not yet implemented", "project_id": project_id}


@router.post("/{project_id}/search")
async def search_chunks(
    project_id: str,
    request: SearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """Search for similar document chunks."""
    # TODO: Integrate with worker retriever
    return {"chunks": [], "query": request.query}


@router.get("/{project_id}/chunks")
async def list_chunks(project_id: str, db: AsyncSession = Depends(get_db)):
    """List all indexed chunks for a project."""
    result = await db.execute(
        select(DocumentChunk).where(DocumentChunk.project_id == project_id)
    )
    chunks = result.scalars().all()
    return [
        {
            "id": c.id,
            "file_path": c.file_path,
            "chunk_index": c.chunk_index,
            "token_count": c.token_count,
        }
        for c in chunks
    ]


@router.delete("/{project_id}/chunks/{chunk_id}", status_code=204)
async def delete_chunk(
    project_id: str, chunk_id: int, db: AsyncSession = Depends(get_db)
):
    """Delete a document chunk."""
    result = await db.execute(
        select(DocumentChunk).where(
            DocumentChunk.id == chunk_id,
            DocumentChunk.project_id == project_id
        )
    )
    chunk = result.scalar_one_or_none()
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")
    await db.delete(chunk)
    await db.commit()
