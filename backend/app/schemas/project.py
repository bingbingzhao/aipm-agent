"""Project Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(default="")


class ProjectResponse(BaseModel):
    id: str
    title: str
    description: str
    stage: str
    status: str
    requirement_card: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    stage: Optional[str] = None


class RequirementSlotResponse(BaseModel):
    key: str
    label: str
    value: str
    state: str
    priority: str

    model_config = {"from_attributes": True}


class ConversationCreate(BaseModel):
    content: str = Field(..., min_length=1)


class ConversationResponse(BaseModel):
    id: str
    project_id: str
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    reply: str
    stage_changed: bool = False
    new_stage: Optional[str] = None
    requirement_card: Optional[dict] = None
