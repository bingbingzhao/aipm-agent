"""Project CRUD API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.models.project import (
    Project, ProjectStage, RequirementSlot,
    Conversation, ThinkingReport, ProductStructure,
    Prototype, PRD, DeliveryPlan,
)
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    RequirementSlotResponse,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _build_requirement_card(slots: list[RequirementSlot]) -> dict | None:
    """Convert requirement slots to the legacy card dict format."""
    if not slots:
        return None
    return {
        s.key: {"label": s.label, "value": s.value, "state": s.state}
        for s in slots
    }


def _project_to_response(p, include_card=True) -> dict:
    """Convert Project ORM to response dict with optional card."""
    card = None
    if include_card:
        try:
            # Lazy-load slots if available
            card = _build_requirement_card(p.slots)
        except Exception:
            pass  # Slots not loaded yet (e.g. just created)
    return {
        "id": p.id,
        "title": p.title,
        "description": p.description,
        "stage": p.stage,
        "status": p.status,
        "requirement_card": card,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }


@router.get("/")
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.slots))
        .order_by(Project.updated_at.desc())
    )
    return [_project_to_response(p) for p in result.scalars().all()]


@router.post("/", status_code=201)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    project = Project(title=data.title, description=data.description)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return _project_to_response(project)


@router.get("/{project_id}")
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.slots))
        .where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return _project_to_response(project)


@router.patch("/{project_id}")
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)

    await db.commit()
    await db.refresh(project)
    return _project_to_response(project, include_card=False)


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await db.delete(project)
    await db.commit()


STAGE_ORDER = ["idea", "thinking", "structure", "prototype", "prd", "delivery"]


@router.post("/{project_id}/regress")
async def regress_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """回退项目到上一阶段，保留对话历史和需求卡片。"""
    result = await db.execute(
        select(Project)
        .options(selectinload(Project.slots))
        .where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    current_idx = STAGE_ORDER.index(project.stage) if project.stage in STAGE_ORDER else 0
    if current_idx == 0:
        raise HTTPException(status_code=400, detail="已在最初阶段，无法回退")

    prev_stage = STAGE_ORDER[current_idx - 1]
    project.stage = prev_stage

    # NOTES: requirement_card (slots) and conversations are preserved
    # Stage-specific data (thinking report, structure, prototype, etc.)
    # are kept in their tables as version history.

    await db.commit()
    await db.refresh(project)
    return _project_to_response(project)


# ═══ Requirement Slots API ═══

@router.get("/{project_id}/slots", response_model=list[RequirementSlotResponse])
async def get_project_slots(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RequirementSlot)
        .where(RequirementSlot.project_id == project_id)
        .order_by(RequirementSlot.key)
    )
    return result.scalars().all()
