"""Stage Pipeline API — manual stage advancement endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.stage_pipeline import (
    advance_to_thinking,
    advance_to_prototype,
    advance_to_prd,
    advance_to_delivery,
    iterate_prototype,
    get_project,
)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.post("/advance/{project_id}")
async def advance_stage(project_id: str) -> dict:
    """Advance project to the next stage.

    - Stage ① → ②: auto-triggered via WebSocket (see ws.py)
    - Stage ② → ④: call this endpoint
    """
    project = await get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    from app.models.project import ProjectStage

    if project.stage == ProjectStage.IDEA:
        if not project.requirement_card:
            raise HTTPException(
                status_code=400,
                detail="Stage ① not complete. Card is not saturated yet."
            )
        result = await advance_to_thinking(project_id, project.requirement_card)
        return {
            "status": "ok",
            "project_id": project_id,
            **result,
        }

    if project.stage == ProjectStage.THINKING:
        raise HTTPException(
            status_code=400,
            detail=f"Stage '{project.stage}' auto-advances. No manual action needed."
        )

    if project.stage == ProjectStage.STRUCTURE:
        result = await advance_to_prototype(project_id)
        return {
            "status": "ok",
            "project_id": project_id,
            **result,
        }

    if project.stage == ProjectStage.PROTOTYPE:
        result = await advance_to_prd(project_id)
        return {
            "status": "ok",
            "project_id": project_id,
            **result,
        }

    if project.stage == ProjectStage.PRD:
        result = await advance_to_delivery(project_id)
        return {
            "status": "ok",
            "project_id": project_id,
            **result,
        }

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
    return {
        "status": "ok",
        "project_id": project_id,
        **result,
    }


@router.get("/state/{project_id}")
async def get_pipeline_state(project_id: str) -> dict:
    """Get the full pipeline state for a project."""
    project = await get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    outputs = project.stage_outputs or {}

    return {
        "project_id": project.id,
        "title": project.title,
        "stage": project.stage,
        "requirement_card": project.requirement_card,
        "thinking_report": outputs.get("thinking", {}).get("report"),
        "structure": outputs.get("structure", {}).get("data"),
        "prototype_html": outputs.get("prototype", {}).get("html"),
        "validation": outputs.get("prototype", {}).get("validation"),
        "prd_document": outputs.get("prd", {}).get("document"),
        "delivery": outputs.get("delivery", {}).get("data"),
    }
