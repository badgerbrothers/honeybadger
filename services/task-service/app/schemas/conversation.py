"""Conversation and Message schemas."""
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
import uuid
from app.models.conversation import MessageRole

class ConversationCreate(BaseModel):
    """Schema for creating a conversation."""
    project_id: uuid.UUID
    title: str | None = Field(None, max_length=255)

class ConversationUpdate(BaseModel):
    """Schema for updating a conversation."""
    title: str | None = Field(None, max_length=255)

class ConversationResponse(BaseModel):
    """Schema for conversation API responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime

class MessageCreate(BaseModel):
    """Schema for creating a message."""
    role: MessageRole
    content: str = Field(..., min_length=1)

class MessageResponse(BaseModel):
    """Schema for message API responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: MessageRole
    content: str
    created_at: datetime
