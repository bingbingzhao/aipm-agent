"""Stage Pipeline Orchestrator — 串联 ①→②→③→④ 管线。

Manages automatic transitions between stages:
- Stage ① (idea) complete → auto Stage ② (thinking) → auto Stage ③ (structure)
- Stage ③ (structure) complete → user triggers Stage ④ (prototype)

Stores all outputs in Project.stage_outputs JSON field.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_session
from app.models.project import Project, ProjectStage
from app.services.inquiry_engine import InquiryEngine
from app.services.product_thinking import ProductThinking
from app.services.product_structure import ProductStructureGenerator
from app.services.prototype import PrototypeGenerator
from app.services.prototype_validator import PrototypeValidator
from app.services.prd_generator import PRDGenerator
from app.services.delivery_generator import DeliveryGenerator

_engines: dict[str, InquiryEngine] = {}
_thinking = ProductThinking()
_structure = ProductStructureGenerator()
_proto_gen = PrototypeGenerator()
_proto_val = PrototypeValidator()
_prd_gen = PRDGenerator()
_delivery_gen = DeliveryGenerator()


def get_engine(project_id: str) -> Optional[InquiryEngine]:
    return _engines.get(project_id)


def set_engine(project_id: str, engine: InquiryEngine):
    _engines[project_id] = engine


def remove_engine(project_id: str):
    _engines.pop(project_id, None)


async def get_project(project_id: str) -> Optional[Project]:
    async with async_session() as db:
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        return result.scalar_one_or_none()


async def save_stage_output(
    project_id: str,
    stage: str,
    output: dict,
):
    """Save a stage's output to the project."""
    async with async_session() as db:
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            return

        outputs = dict(project.stage_outputs or {})
        outputs[stage] = output

        project.stage_outputs = outputs
        await db.commit()


async def advance_to_thinking(
    project_id: str,
    requirement_card: dict,
) -> dict:
    """Stage ① complete → auto-generate Stage ② + auto-chain to Stage ③.

    Called when the inquiry engine's requirement card is saturated.
    """
    # Save requirement card
    await save_stage_output(project_id, "idea", {
        "requirement_card": requirement_card,
    })

    # Update stage
    async with async_session() as db:
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            return {"error": "Project not found"}

        project.stage = ProjectStage.THINKING
        project.requirement_card = requirement_card
        await db.commit()

    # Generate thinking report
    report = await _thinking.analyze(requirement_card)
    await save_stage_output(project_id, "thinking", {"report": report})

    # Auto-advance to structure
    structure_result = await advance_to_structure(project_id, report, requirement_card)

    return {
        "new_stage": structure_result.get("new_stage", ProjectStage.STRUCTURE),
        "thinking_report": report,
        "structure": structure_result.get("structure"),
    }


async def advance_to_structure(
    project_id: str,
    thinking_report: str,
    requirement_card: dict,
) -> dict:
    """Stage ② complete → auto-generate Stage ③ product structure."""
    # Update stage
    async with async_session() as db:
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            return {"error": "Project not found"}

        project.stage = ProjectStage.STRUCTURE
        await db.commit()

    # Generate structure
    structure = await _structure.generate(thinking_report, requirement_card)
    await save_stage_output(project_id, "structure", {"data": structure})

    return {
        "new_stage": ProjectStage.STRUCTURE,
        "structure": structure,
    }


async def advance_to_prototype(
    project_id: str,
) -> dict:
    """Stage ③ complete → generate Stage ④ prototype."""
    async with async_session() as db:
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            return {"error": "Project not found"}

        outputs = dict(project.stage_outputs or {})
        thinking_data = outputs.get("thinking", {})
        structure_data = outputs.get("structure", {})
        thinking_report = thinking_data.get("report", "")
        structure_info = structure_data.get("data", {})
        requirement_card = project.requirement_card or {}

    if not thinking_report:
        return {"error": "No thinking report found."}

    description = _build_prototype_prompt(
        thinking_report, requirement_card, structure_info
    )

    html = await _proto_gen.generate(description)
    validation = _proto_val.validate(html)

    await save_stage_output(project_id, "prototype", {
        "html": html,
        "validation": validation.to_dict(),
    })

    async with async_session() as db:
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if project:
            project.stage = ProjectStage.PROTOTYPE
            await db.commit()

    return {
        "new_stage": ProjectStage.PROTOTYPE,
        "prototype_html": html,
        "validation": validation.to_dict(),
    }


async def iterate_prototype(
    project_id: str,
    feedback: str,
) -> dict:
    """Iterate on an existing prototype based on user feedback."""
    async with async_session() as db:
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            return {"error": "Project not found"}

        outputs = dict(project.stage_outputs or {})
        proto_data = outputs.get("prototype", {})
        current_html = proto_data.get("html", "")

    if not current_html:
        return {"error": "No prototype found. Generate one first."}

    html = await _proto_gen.iterate(current_html, feedback)
    validation = _proto_val.validate(html)

    await save_stage_output(project_id, "prototype", {
        "html": html,
        "validation": validation.to_dict(),
    })

    return {
        "prototype_html": html,
        "validation": validation.to_dict(),
    }


def _build_prototype_prompt(
    thinking_report: str,
    requirement_card: dict,
    structure_info: dict,
) -> str:
    """Build a prompt for prototype generation using all available context."""
    card_summary = "\n".join(
        f"- {v.get('label', k)}: {v.get('value', '')}"
        for k, v in requirement_card.items()
        if v.get("state") == "saturated"
    )

    report_summary = thinking_report[:800]

    # Extract structure info
    structure_text = ""
    if structure_info and not structure_info.get("parse_error"):
        routes = structure_info.get("route_plan", [])
        if routes:
            pages_desc = "\n".join(
                f"  - {r.get('route', '/')}: {r.get('title', '')} — {r.get('description', '')}"
                for r in routes[:8]
            )
            structure_text = f"\n## 页面路由规划\n{pages_desc}"

        modules = structure_info.get("information_architecture", {}).get("modules", [])
        if modules:
            mod_desc = "\n".join(
                f"  - {m.get('name', '')}: {', '.join(m.get('pages', []))}"
                for m in modules[:5]
            )
            structure_text += f"\n\n## 功能模块\n{mod_desc}"

    prompt = f"""基于以下产品分析，生成一个完整的交互原型页面。

## 产品需求
{card_summary}

## 产品思路分析
{report_summary}"""

    if structure_text:
        prompt += f"\n{structure_text}"

    prompt += "\n\n请生成一个包含核心功能展示的 HTML 原型页面，要求设计现代、交互完整，覆盖主要页面路由。"

    return prompt


async def advance_to_prd(
    project_id: str,
) -> dict:
    """Stage ④ complete → generate Stage ⑤ PRD."""
    async with async_session() as db:
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            return {"error": "Project not found"}

        outputs = dict(project.stage_outputs or {})
        thinking_data = outputs.get("thinking", {})
        structure_data = outputs.get("structure", {})
        proto_data = outputs.get("prototype", {})
        requirement_card = project.requirement_card or {}

    thinking_report = thinking_data.get("report", "")
    structure = structure_data.get("data", {})
    proto_html = proto_data.get("html", "")

    if not thinking_report and not structure:
        return {"error": "No previous stage data found. Complete earlier stages first."}

    # Generate PRD
    prd = await _prd_gen.generate(
        project_name=project.title,
        requirement_card=requirement_card,
        thinking_report=thinking_report,
        structure=structure,
        prototype_html=proto_html,
    )

    # Save
    await save_stage_output(project_id, "prd", {"document": prd})

    async with async_session() as db:
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if project:
            project.stage = ProjectStage.PRD
            await db.commit()

    return {
        "new_stage": ProjectStage.PRD,
        "prd_document": prd,
    }


async def advance_to_delivery(
    project_id: str,
) -> dict:
    """Stage ⑤ complete → generate Stage ⑥ delivery plan."""
    async with async_session() as db:
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            return {"error": "Project not found"}

        outputs = dict(project.stage_outputs or {})
        prd_data = outputs.get("prd", {})
        structure_data = outputs.get("structure", {})

    prd_doc = prd_data.get("document", "")
    structure = structure_data.get("data", {})

    if not prd_doc:
        return {"error": "No PRD found. Complete Stage ⑤ first."}

    delivery = await _delivery_gen.generate(prd_doc, structure)

    await save_stage_output(project_id, "delivery", {"data": delivery})

    async with async_session() as db:
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if project:
            project.stage = ProjectStage.DELIVERY
            await db.commit()

    return {
        "new_stage": ProjectStage.DELIVERY,
        "delivery": delivery,
    }
