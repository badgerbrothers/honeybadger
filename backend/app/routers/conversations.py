"""Conversations API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from app.database import get_db
from app.models.conversation import Conversation, Message
from app.schemas.conversation import ConversationCreate, ConversationUpdate, ConversationResponse, MessageCreate, MessageResponse

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

@router.get("/", response_model=list[ConversationResponse])
async def list_conversations(project_id: uuid.UUID | None = Query(None), db: AsyncSession = Depends(get_db)):
    query = select(Conversation)
    if project_id:
        query = query.where(Conversation.project_id == project_id)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=ConversationResponse, status_code=201)
async def create_conversation(conversation: ConversationCreate, db: AsyncSession = Depends(get_db)):
    db_conversation = Conversation(**conversation.model_dump())
    db.add(db_conversation)
    await db.commit()
    await db.refresh(db_conversation)
    return db_conversation

@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation

@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(conversation_id: uuid.UUID, conversation_update: ConversationUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    for key, value in conversation_update.model_dump(exclude_unset=True).items():
        setattr(conversation, key, value)
    await db.commit()
    await db.refresh(conversation)
    return conversation

@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.delete(conversation)
    await db.commit()

@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def list_messages(conversation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")
    result = await db.execute(select(Message).where(Message.conversation_id == conversation_id))
    return result.scalars().all()

@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=201)
async def create_message(conversation_id: uuid.UUID, message: MessageCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")
    db_message = Message(conversation_id=conversation_id, **message.model_dump())
    db.add(db_message)
    await db.commit()
    await db.refresh(db_message)
    return db_message
