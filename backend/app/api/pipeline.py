"""Stage Pipeline API — manual stage advancement endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.core.db import async_session
from app.models.project import (
    Project, ProjectStage, RequirementSlot,
    ThinkingReport, ProductStructure,
    Prototype, PRD, DeliveryPlan,
    DeliveryEpic, DeliveryStory, DeliveryTask, DeliverySprint,
)
from app.services.stage_pipeline import (
    advance_to_thinking,
    advance_to_structure,
    advance_to_prototype,
    advance_to_prd,
    advance_to_delivery,
    iterate_prototype,
    get_project,
)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.post("/advance/{project_id}")
async def advance_stage(project_id: str) -> dict:
    """Advance project to the next stage."""
    project = await get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.stage == ProjectStage.IDEA:
        async with async_session() as db:
            slots_result = await db.execute(
                select(RequirementSlot)
                .where(RequirementSlot.project_id == project_id)
            )
            slots = slots_result.scalars().all()
            if not slots:
                raise HTTPException(status_code=400, detail="需求卡片为空，请先完成对话。")

            requirement_card = {}
            for s in slots:
                requirement_card[s.key] = {
                    "label": s.label,
                    "value": s.value,
                    "state": s.state,
                }

        result = await advance_to_thinking(project_id, requirement_card)
        return {"status": "ok", "project_id": project_id, **result}

    if project.stage == ProjectStage.THINKING:
        async with async_session() as db:
            think_result = await db.execute(
                select(ThinkingReport)
                .where(ThinkingReport.project_id == project_id)
                .order_by(ThinkingReport.version.desc())
                .limit(1)
            )
            think = think_result.scalar_one_or_none()

            slots_result = await db.execute(
                select(RequirementSlot)
                .where(RequirementSlot.project_id == project_id)
            )
            slots = slots_result.scalars().all()

        if not think:
            raise HTTPException(status_code=400, detail="暂无思路分析报告。")

        requirement_card = {}
        for s in slots:
            requirement_card[s.key] = {
                "label": s.label, "value": s.value, "state": s.state,
            }

        result = await advance_to_structure(
            project_id, think.content, requirement_card
        )
        return {"status": "ok", "project_id": project_id, "thinking_report": think.content, **result}

    if project.stage == ProjectStage.STRUCTURE:
        result = await advance_to_prototype(project_id)
        return {"status": "ok", "project_id": project_id, **result}

    if project.stage == ProjectStage.PROTOTYPE:
        result = await advance_to_prd(project_id)
        return {"status": "ok", "project_id": project_id, **result}

    if project.stage == ProjectStage.PRD:
        result = await advance_to_delivery(project_id)
        return {"status": "ok", "project_id": project_id, **result}

    raise HTTPException(
        status_code=400,
        detail=f"Cannot advance from stage '{project.stage}'"
    )


@router.post("/iterate/{project_id}")
async def iterate_prototype_endpoint(
    project_id: str,
    feedback: str = "",
) -> dict:
    """Iterate on the current prototype based on feedback."""
    if not feedback:
        raise HTTPException(status_code=400, detail="Feedback is required")

    result = await iterate_prototype(project_id, feedback)
    return {"status": "ok", "project_id": project_id, **result}


@router.get("/state/{project_id}")
async def get_pipeline_state(project_id: str) -> dict:
    """Get the full pipeline state for a project."""
    project = await get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    async with async_session() as db:
        # Slots → requirement_card dict
        slots_result = await db.execute(
            select(RequirementSlot)
            .where(RequirementSlot.project_id == project_id)
        )
        requirement_card = {
            s.key: {"label": s.label, "value": s.value, "state": s.state}
            for s in slots_result.scalars()
        } or None

        # Thinking report
        think_result = await db.execute(
            select(ThinkingReport)
            .where(ThinkingReport.project_id == project_id)
            .order_by(ThinkingReport.version.desc())
            .limit(1)
        )
        think = think_result.scalar_one_or_none()

        # Structure
        struct_result = await db.execute(
            select(ProductStructure)
            .where(ProductStructure.project_id == project_id)
            .order_by(ProductStructure.version.desc())
            .limit(1)
        )
        struct = struct_result.scalar_one_or_none()

        # Prototype
        proto_result = await db.execute(
            select(Prototype)
            .where(Prototype.project_id == project_id)
            .order_by(Prototype.version.desc())
            .limit(1)
        )
        proto = proto_result.scalar_one_or_none()

        # PRD
        prd_result = await db.execute(
            select(PRD)
            .where(PRD.project_id == project_id)
            .order_by(PRD.version.desc())
            .limit(1)
        )
        prd = prd_result.scalar_one_or_none()

        # Delivery plan (with nested data as dict for API compat)
        plan_result = await db.execute(
            select(DeliveryPlan)
            .where(DeliveryPlan.project_id == project_id)
            .order_by(DeliveryPlan.created_at.desc())
            .limit(1)
        )
        plan = plan_result.scalar_one_or_none()

        delivery_data = None
        if plan:
            epics_result = await db.execute(
                select(DeliveryEpic)
                .where(DeliveryEpic.delivery_plan_id == plan.id)
                .order_by(DeliveryEpic.order_index)
            )
            epics_data = []
            for epic in epics_result.scalars():
                stories_result = await db.execute(
                    select(DeliveryStory)
                    .where(DeliveryStory.epic_id == epic.id)
                    .order_by(DeliveryStory.order_index)
                )
                stories_data = []
                for story in stories_result.scalars():
                    tasks_result = await db.execute(
                        select(DeliveryTask)
                        .where(DeliveryTask.story_id == story.id)
                    )
                    stories_data.append({
                        "id": story.id, "name": story.name,
                        "as_a": story.as_a, "i_want": story.i_want,
                        "so_that": story.so_that, "story_points": story.story_points,
                        "tasks": [
                            {"name": t.name, "role": t.role, "estimate_hours": t.estimate_hours}
                            for t in tasks_result.scalars()
                        ],
                    })
                epics_data.append({
                    "id": epic.id, "name": epic.name,
                    "description": epic.description,
                    "stories": stories_data,
                })

            sprints_result = await db.execute(
                select(DeliverySprint)
                .where(DeliverySprint.delivery_plan_id == plan.id)
                .order_by(DeliverySprint.order_index)
            )
            sprints_data = [
                {"name": s.name, "goal": s.goal,
                 "duration_weeks": s.duration_weeks, "total_points": s.total_points}
                for s in sprints_result.scalars()
            ]

            delivery_data = {
                "epics": epics_data,
                "sprints": sprints_data,
                "total_estimate": {
                    "weeks": plan.total_weeks,
                    "team_size": plan.team_size,
                    "total_story_points": plan.total_story_points,
                },
            }

    return {
        "project_id": project.id,
        "title": project.title,
        "stage": project.stage,
        "requirement_card": requirement_card,
        "thinking_report": think.content if think else None,
        "structure": struct.data if struct else None,
        "prototype_html": proto.html if proto else None,
        "validation": proto.validation_detail if proto else None,
        "prd_document": prd.content if prd else None,
        "delivery": delivery_data,
    }
