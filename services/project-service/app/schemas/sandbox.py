"""SandboxSession schemas."""
from pydantic import BaseModel, ConfigDict
from datetime import datetime
import uuid

class SandboxSessionResponse(BaseModel):
    """Schema for sandbox session API responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    task_run_id: uuid.UUID
    container_id: str
    image: str
    cpu_limit: int | None
    memory_limit: int | None
    terminated_at: datetime | None
    created_at: datetime
    updated_at: datetime
