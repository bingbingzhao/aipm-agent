"""Stage Pipeline Orchestrator — 串联 ①→②→③→④→⑤→⑥ 管线.

Each stage transitions manually (user confirms), storing outputs in
normalized relational tables instead of a single JSON blob.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_session
from app.models.project import (
    Project, ProjectStage, RequirementSlot,
    ThinkingReport, ProductStructure,
    Prototype, PRD, DeliveryPlan,
    DeliveryEpic, DeliveryStory, DeliveryTask, DeliverySprint,
)
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


def _build_requirement_card_from_slots(slots: list[RequirementSlot]) -> dict:
    """Convert normalized slots to dict format for AI prompts."""
    return {
        s.key: {"label": s.label, "value": s.value, "state": s.state}
        for s in slots
    }


async def advance_to_thinking(
    project_id: str,
    requirement_card: dict,
) -> dict:
    """Stage ① → ②: Generate thinking report from requirement card."""
    # Save requirement slots to DB
    async with async_session() as db:
        # Delete old slots
        await db.execute(
            RequirementSlot.__table__.delete().where(
                RequirementSlot.project_id == project_id
            )
        )
        for key, data in requirement_card.items():
            db.add(RequirementSlot(
                project_id=project_id,
                key=key,
                label=data.get("label", key),
                value=data.get("value", ""),
                state=data.get("state", "empty"),
            ))

        # Update project stage
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            return {"error": "Project not found"}

        project.stage = ProjectStage.THINKING
        await db.commit()

    # Generate thinking report
    report = await _thinking.analyze(requirement_card)

    # Save thinking report
    async with async_session() as db:
        db.add(ThinkingReport(
            project_id=project_id,
            content=report,
            version=1,
        ))
        await db.commit()

    return {
        "new_stage": ProjectStage.THINKING,
        "thinking_report": report,
    }


async def advance_to_structure(
    project_id: str,
    thinking_report: str,
    requirement_card: dict,
) -> dict:
    """Stage ② → ③: Generate product structure from thinking report."""
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

    # Save structure
    async with async_session() as db:
        db.add(ProductStructure(
            project_id=project_id,
            data=structure,
            version=1,
        ))
        await db.commit()

    return {
        "new_stage": ProjectStage.STRUCTURE,
        "structure": structure,
    }


async def advance_to_prototype(project_id: str) -> dict:
    """Stage ③ → ④: Generate prototype HTML."""
    async with async_session() as db:
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            return {"error": "Project not found"}

        # Load previous stage data
        think_result = await db.execute(
            select(ThinkingReport)
            .where(ThinkingReport.project_id == project_id)
            .order_by(ThinkingReport.version.desc())
            .limit(1)
        )
        think = think_result.scalar_one_or_none()

        struct_result = await db.execute(
            select(ProductStructure)
            .where(ProductStructure.project_id == project_id)
            .order_by(ProductStructure.version.desc())
            .limit(1)
        )
        struct = struct_result.scalar_one_or_none()

        slots_result = await db.execute(
            select(RequirementSlot)
            .where(RequirementSlot.project_id == project_id)
        )
        slots = slots_result.scalars().all()

    thinking_report = think.content if think else ""
    structure_data = struct.data if struct else {}
    requirement_card = _build_requirement_card_from_slots(slots)

    description = _build_prototype_prompt(
        thinking_report, requirement_card, structure_data
    )

    html = await _proto_gen.generate(description)
    validation = _proto_val.validate(html)

    # Save prototype
    async with async_session() as db:
        db.add(Prototype(
            project_id=project_id,
            html=html,
            validation_score=validation.score if hasattr(validation, 'score') else None,
            validation_detail=validation.to_dict(),
            version=1,
        ))

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


async def iterate_prototype(project_id: str, feedback: str) -> dict:
    """Iterate on an existing prototype based on user feedback."""
    async with async_session() as db:
        proto_result = await db.execute(
            select(Prototype)
            .where(Prototype.project_id == project_id)
            .order_by(Prototype.version.desc())
            .limit(1)
        )
        proto = proto_result.scalar_one_or_none()
        if not proto:
            return {"error": "No prototype found. Generate one first."}

        current_html = proto.html

    html = await _proto_gen.iterate(current_html, feedback)
    validation = _proto_val.validate(html)

    async with async_session() as db:
        db.add(Prototype(
            project_id=project_id,
            html=html,
            validation_score=validation.score if hasattr(validation, 'score') else None,
            validation_detail=validation.to_dict(),
            feedback=feedback,
            version=proto.version + 1,
        ))
        await db.commit()

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


async def advance_to_prd(project_id: str) -> dict:
    """Stage ④ → ⑤: Generate PRD."""
    async with async_session() as db:
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            return {"error": "Project not found"}

        # Load context
        think_result = await db.execute(
            select(ThinkingReport)
            .where(ThinkingReport.project_id == project_id)
            .order_by(ThinkingReport.version.desc())
            .limit(1)
        )
        think = think_result.scalar_one_or_none()

        struct_result = await db.execute(
            select(ProductStructure)
            .where(ProductStructure.project_id == project_id)
            .order_by(ProductStructure.version.desc())
            .limit(1)
        )
        struct = struct_result.scalar_one_or_none()

        proto_result = await db.execute(
            select(Prototype)
            .where(Prototype.project_id == project_id)
            .order_by(Prototype.version.desc())
            .limit(1)
        )
        proto = proto_result.scalar_one_or_none()

        slots_result = await db.execute(
            select(RequirementSlot)
            .where(RequirementSlot.project_id == project_id)
        )
        slots = slots_result.scalars().all()

    requirement_card = _build_requirement_card_from_slots(slots)
    prd = await _prd_gen.generate(
        project_name=project.title,
        requirement_card=requirement_card,
        thinking_report=think.content if think else "",
        structure=struct.data if struct else {},
        prototype_html=proto.html if proto else "",
    )

    async with async_session() as db:
        db.add(PRD(project_id=project_id, content=prd, version=1))
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


async def advance_to_delivery(project_id: str) -> dict:
    """Stage ⑤ → ⑥: Generate delivery plan."""
    async with async_session() as db:
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            return {"error": "Project not found"}

        prd_result = await db.execute(
            select(PRD)
            .where(PRD.project_id == project_id)
            .order_by(PRD.version.desc())
            .limit(1)
        )
        prd = prd_result.scalar_one_or_none()

        struct_result = await db.execute(
            select(ProductStructure)
            .where(ProductStructure.project_id == project_id)
            .order_by(ProductStructure.version.desc())
            .limit(1)
        )
        struct = struct_result.scalar_one_or_none()

    if not prd:
        return {"error": "No PRD found. Complete Stage ⑤ first."}

    delivery = await _delivery_gen.generate(
        prd.content,
        struct.data if struct else {},
    )

    # Save delivery plan with nested epics/stories/tasks/sprints
    async with async_session() as db:
        plan = DeliveryPlan(
            project_id=project_id,
            total_weeks=delivery.get("total_estimate", {}).get("weeks"),
            team_size=delivery.get("total_estimate", {}).get("team_size"),
            total_story_points=delivery.get("total_estimate", {}).get("total_story_points"),
        )
        db.add(plan)
        await db.flush()  # Get plan ID

        # Epics with stories and tasks
        for epic_data in delivery.get("epics", []):
            epic = DeliveryEpic(
                delivery_plan_id=plan.id,
                name=epic_data.get("name", ""),
                description=epic_data.get("description", ""),
                order_index=epic_data.get("order", 0),
            )
            db.add(epic)
            await db.flush()

            for story_data in epic_data.get("stories", []):
                story = DeliveryStory(
                    epic_id=epic.id,
                    name=story_data.get("name", ""),
                    as_a=story_data.get("as_a", ""),
                    i_want=story_data.get("i_want", ""),
                    so_that=story_data.get("so_that", ""),
                    story_points=story_data.get("story_points", 1),
                    order_index=story_data.get("order", 0),
                )
                db.add(story)
                await db.flush()

                for task_data in story_data.get("tasks", []):
                    db.add(DeliveryTask(
                        story_id=story.id,
                        name=task_data.get("name", ""),
                        role=task_data.get("role", "fullstack"),
                        estimate_hours=task_data.get("estimate_hours", 0),
                    ))

        # Sprints
        for sprint_data in delivery.get("sprints", []):
            db.add(DeliverySprint(
                delivery_plan_id=plan.id,
                name=sprint_data.get("name", ""),
                goal=sprint_data.get("goal", ""),
                duration_weeks=sprint_data.get("duration_weeks", 2),
                total_points=sprint_data.get("total_points", 0),
            ))

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
