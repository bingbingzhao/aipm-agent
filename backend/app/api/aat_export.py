"""AAT Spec export API endpoint.

Exports AIPM project data as AATProductSpec JSON that AAT can consume.
Uses LLM-driven generation from pipeline stage outputs.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.project import Project
from app.schemas.aat_schema import AATProductSpec, ProjectMeta
from app.services.aat_spec_generator import AATSpecGenerator

router = APIRouter(prefix="/api/aat", tags=["aat"])

_spec_gen = AATSpecGenerator()


@router.get("/spec/{project_id}")
async def export_aat_spec(project_id: str, db: AsyncSession = Depends(get_db)):
    """Export a project as AAT-compatible product spec JSON.

    AAT can consume this directly for test generation.
    Generates features, pages, flows, API contracts, and business rules
    from pipeline stage outputs using LLM extraction.
    """
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    outputs = project.stage_outputs or {}

    # Extract stage data
    thinking_data = outputs.get("thinking", {})
    structure_data = outputs.get("structure", {})
    prd_data = outputs.get("prd", {})
    delivery_data = outputs.get("delivery", {})

    thinking_report = thinking_data.get("report", "")
    structure = structure_data.get("data", {})
    prd_document = prd_data.get("document", "")
    delivery = delivery_data.get("data", {})

    # If no pipeline data yet, return basic spec
    if not thinking_report and not structure and not prd_document:
        return AATProductSpec(
            project=ProjectMeta(
                id=project.id,
                name=project.title,
                description=project.description,
                stage=project.stage,
            ),
            features=[],
            pages=[],
            flows=[],
            api_contracts=[],
            business_rules=[],
        )

    # Generate full spec from pipeline data (5 LLM passes, non-blocking)
    spec_data = await _spec_gen.generate(
        project_name=project.title,
        project_description=project.description,
        thinking_report=thinking_report,
        structure=structure,
        prd_document=prd_document,
        delivery=delivery,
    )

    # Build response with whatever data we got (partial results OK)
    features = spec_data.get("features", [])
    pages = spec_data.get("pages", [])
    flows = spec_data.get("flows", [])
    api_contracts = spec_data.get("api_contracts", [])
    business_rules = spec_data.get("business_rules", [])

    return AATProductSpec(
        project=ProjectMeta(
            id=project.id,
            name=project.title,
            description=project.description,
            stage=project.stage,
        ),
        features=features,
        pages=pages,
        flows=flows,
        api_contracts=api_contracts,
        business_rules=business_rules,
    )


@router.get("/spec/{project_id}/estimate")
async def estimate_test_count(project_id: str, db: AsyncSession = Depends(get_db)):
    """Estimate how many test cases AAT would generate for this project."""
    spec = await export_aat_spec(project_id, db)
    return {
        "project_id": project_id,
        "features_count": len(spec.features),
        "criteria_count": sum(len(f.criteria) for f in spec.features),
        "flows_count": len(spec.flows),
        "api_count": len(spec.api_contracts),
        "rules_count": len(spec.business_rules),
        "estimated_test_count": spec.estimate_test_count(),
    }
