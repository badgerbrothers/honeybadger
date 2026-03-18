"""Memory API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from app.database import get_db
from app.models.memory import ConversationSummary, ProjectMemory
from app.models.conversation import Conversation, Message
from app.models.project import Project
from app.schemas.memory import (
    ConversationSummaryResponse,
    ProjectMemoryCreate,
    ProjectMemoryResponse,
    ProjectMemorySearch,
)
from app.services.memory_service import memory_service

router = APIRouter(prefix="/api", tags=["memory"])


@router.post("/conversations/{conversation_id}/summarize", response_model=ConversationSummaryResponse, status_code=201)
async def summarize_conversation(conversation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Generate and store conversation summary."""
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages_result = await db.execute(
        select(Message).where(Message.conversation_id == conversation_id)
    )
    messages = messages_result.scalars().all()

    try:
        summary_text = await memory_service.summarize_conversation(messages)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    summary = ConversationSummary(
        conversation_id=conversation_id,
        summary_text=summary_text,
        message_count=len(messages),
    )
    db.add(summary)
    await db.commit()
    await db.refresh(summary)
    return summary


@router.get("/conversations/{conversation_id}/summary", response_model=ConversationSummaryResponse)
async def get_conversation_summary(conversation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Retrieve latest conversation summary."""
    result = await db.execute(
        select(ConversationSummary)
        .where(ConversationSummary.conversation_id == conversation_id)
        .order_by(ConversationSummary.created_at.desc())
    )
    summary = result.scalars().first()
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    return summary


@router.post("/projects/{project_id}/memories", response_model=ProjectMemoryResponse, status_code=201)
async def create_project_memory(
    project_id: uuid.UUID, memory: ProjectMemoryCreate, db: AsyncSession = Depends(get_db)
):
    """Create new project memory with embedding."""
    # Verify project exists
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        embedding = await memory_service.generate_embedding(memory.content)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    db_memory = ProjectMemory(
        project_id=project_id,
        memory_type=memory.memory_type,
        content=memory.content,
        embedding=embedding,
        memory_metadata=memory.memory_metadata,
    )
    db.add(db_memory)
    await db.commit()
    await db.refresh(db_memory)
    return db_memory


@router.get("/projects/{project_id}/memories", response_model=list[ProjectMemoryResponse])
async def list_project_memories(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """List all memories for a project."""
    result = await db.execute(
        select(ProjectMemory).where(ProjectMemory.project_id == project_id)
    )
    return result.scalars().all()


@router.post("/projects/{project_id}/memories/search", response_model=list[ProjectMemoryResponse])
async def search_project_memories(
    project_id: uuid.UUID, search: ProjectMemorySearch, db: AsyncSession = Depends(get_db)
):
    """Semantic search over project memories."""
    memories = await memory_service.search_memories(
        project_id, search.query, search.limit, db
    )
    return memories
