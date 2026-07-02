"""Conversation REST API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.project import Conversation
from app.schemas.project import ConversationResponse

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("/{project_id}", response_model=list[ConversationResponse])
async def get_conversation(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.project_id == project_id)
        .order_by(Conversation.created_at.asc())
    )
    return result.scalars().all()
