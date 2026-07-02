"""Project CRUD API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.project import Project
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project).order_by(Project.updated_at.desc())
    )
    return result.scalars().all()


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    project = Project(title=data.title, description=data.description)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
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
    return project


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


@router.post("/{project_id}/regress", response_model=ProjectResponse)
async def regress_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
):
    """回退项目到上一阶段，清除当前阶段数据。"""
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    current_idx = STAGE_ORDER.index(project.stage) if project.stage in STAGE_ORDER else 0
    if current_idx == 0:
        raise HTTPException(status_code=400, detail="已在最初阶段，无法回退")

    prev_stage = STAGE_ORDER[current_idx - 1]

    # Clear stage outputs for current and later stages
    outputs = project.stage_outputs or {}
    for stage in STAGE_ORDER[current_idx:]:
        outputs.pop(stage, None)
    project.stage_outputs = outputs if outputs else None

    # If going back to idea, clear conversations and requirement card too
    if prev_stage == "idea":
        project.requirement_card = None
        from sqlalchemy import delete
        from app.models.project import Conversation
        await db.execute(
            delete(Conversation).where(Conversation.project_id == project_id)
        )

    project.stage = prev_stage
    await db.commit()
    await db.refresh(project)
    return project
