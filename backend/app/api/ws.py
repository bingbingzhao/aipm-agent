"""Conversation WebSocket endpoint.

Real-time chat for the inquiry engine (Stage ①).
User confirms when ready → advances to Stage ②.
"""

from __future__ import annotations

from typing import Optional, Tuple
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.db import async_session
from app.models.project import (
    Project, Conversation, RequirementSlot, ProjectStage,
    ThinkingReport,
)
from app.services.inquiry_engine import InquiryEngine
from app.services.stage_pipeline import (
    advance_to_thinking,
    get_engine,
    set_engine,
    remove_engine,
)

router = APIRouter()


def _sync_slots(project_id: str, requirement_card: dict):
    """Convert requirement_card dict to RequirementSlot rows for bulk upsert."""
    slots = []
    for key, data in requirement_card.items():
        slots.append(RequirementSlot(
            project_id=project_id,
            key=key,
            label=data.get("label", key),
            value=data.get("value", ""),
            state=data.get("state", "empty"),
        ))
    return slots


async def _get_or_create_engine(
    project_id: str,
    db,
) -> Tuple[InquiryEngine, Optional[Project]]:
    """Get existing engine or create from project + history."""
    cached = get_engine(project_id)
    if cached:
        return cached, None

    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise ValueError("Project not found")

    if project.stage != ProjectStage.IDEA:
        return None, project

    engine = InquiryEngine()

    # Restore slot states from normalized RequirementSlot rows
    slots_result = await db.execute(
        select(RequirementSlot)
        .where(RequirementSlot.project_id == project_id)
    )
    for slot in slots_result.scalars():
        from app.core.slots import SlotState
        try:
            state = SlotState(slot.state)
            engine.slot_manager.update_slot(slot.key, slot.value, state)
        except ValueError:
            pass

    # Load conversation history
    history_result = await db.execute(
        select(Conversation)
        .where(Conversation.project_id == project_id)
        .order_by(Conversation.created_at.asc())
    )
    has_history = False
    for msg in history_result.scalars():
        engine.conversation_history.append({
            "role": msg.role,
            "content": msg.content,
        })
        has_history = True

    # If no history yet, seed with project description as initial idea
    if not has_history and project.description:
        engine.initial_idea = project.description
        engine.conversation_history.append({
            "role": "user",
            "content": f"我想做一个产品：{project.description}",
        })

    set_engine(project_id, engine)
    return engine, project


@router.websocket("/ws/{project_id}")
async def websocket_chat(websocket: WebSocket, project_id: str):
    await websocket.accept()

    try:
        async with async_session() as db:
            try:
                engine, project = await _get_or_create_engine(project_id, db)
            except ValueError:
                await websocket.send_json({
                    "type": "error",
                    "content": "Project not found"
                })
                await websocket.close()
                return

            # If project is past Stage ①, send current state and close
            if engine is None and project is not None:
                # Load thinking report
                think_result = await db.execute(
                    select(ThinkingReport)
                    .where(ThinkingReport.project_id == project_id)
                    .order_by(ThinkingReport.version.desc())
                    .limit(1)
                )
                think = think_result.scalar_one_or_none()

                await websocket.send_json({
                    "type": "stage_state",
                    "stage": project.stage,
                    "thinking_report": think.content if think else None,
                })
                await websocket.close()
                return

            # First-time visit: seed conversation with initial idea if present
            if len(engine.conversation_history) <= 1:
                idea_text = engine.initial_idea[:100] if engine.initial_idea else ""

                if idea_text:
                    # Save initial idea as first user message in DB
                    first_msg = Conversation(
                        project_id=project_id,
                        role="user",
                        content=f"我想做一个产品：{idea_text}",
                    )
                    db.add(first_msg)
                    await db.commit()

                    # Show it to the user
                    await websocket.send_json({
                        "type": "message",
                        "role": "user",
                        "content": f"我想做一个产品：{idea_text}",
                        "stage": ProjectStage.IDEA,
                        "stage_complete": False,
                    })

                    welcome = f"{idea_text}——这个方向挺有意思的！先聊聊你具体想做成什么样的？"
                else:
                    welcome = "嗨！说说你想做什么产品？我可以帮你理清思路。"

                await websocket.send_json({
                    "type": "message",
                    "role": "assistant",
                    "content": welcome,
                    "stage": ProjectStage.IDEA,
                    "stage_complete": False,
                })

            while True:
                data = await websocket.receive_json()
                user_message = data.get("message", "")

                if not user_message:
                    continue

                # Save user message
                db.add(Conversation(
                    project_id=project_id,
                    role="user",
                    content=user_message,
                ))

                # Process with inquiry engine
                result = await engine.chat(user_message)

                # Save assistant message
                db.add(Conversation(
                    project_id=project_id,
                    role="assistant",
                    content=result["reply"],
                ))

                # Persist requirement slots to normalized table
                if result.get("requirement_card"):
                    # Delete old slots and insert new ones
                    await db.execute(
                        RequirementSlot.__table__.delete().where(
                            RequirementSlot.project_id == project_id
                        )
                    )
                    for slot in _sync_slots(project_id, result["requirement_card"]):
                        db.add(slot)

                await db.commit()

                response = {
                    "type": "message",
                    "role": "assistant",
                    "content": result["reply"],
                    "stage": ProjectStage.IDEA,
                    "stage_complete": result["stage_complete"],
                    "requirement_card": result.get("requirement_card"),
                    "next_slot": result.get("next_slot"),
                }

                # Stage ① ready → tell user they can confirm (or keep chatting)
                if result["stage_complete"] and result.get("requirement_card"):
                    response["stage_ready"] = True
                    response["stage_ready_hint"] = (
                        "需求信息差不多了！你可以点「完成需求梳理」生成产品方案，"
                        "也可以继续补充更多细节。"
                    )
                    await websocket.send_json(response)
                    continue

                await websocket.send_json(response)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"WebSocket error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except Exception:
            pass
    finally:
        remove_engine(project_id)
