"""Conversation WebSocket endpoint.

from __future__ import annotations

Real-time chat for the inquiry engine (Stage ①).
Auto-transitions to Stage ② when requirement card is complete.
"""

from typing import Optional, Tuple
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.db import async_session
from app.models.project import Project, Conversation, ProjectStage
from app.services.inquiry_engine import InquiryEngine
from app.services.stage_pipeline import (
    advance_to_thinking,
    get_engine,
    set_engine,
    remove_engine,
)

router = APIRouter()


async def _get_or_create_engine(
    project_id: str,
    db,
) -> Tuple[InquiryEngine, Optional[Project]]:
    """Get existing engine or create from project + history.

    Returns (engine, project). If project is already past Stage ①,
    engine won't be created (returns None for engine, project).
    """
    cached = get_engine(project_id)
    if cached:
        return cached, None

    # Load project
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise ValueError("Project not found")

    # If already past idea stage, don't create new inquiry engine
    if project.stage != ProjectStage.IDEA:
        return None, project

    engine = InquiryEngine(initial_idea=project.description)

    # Restore slot states from existing requirement card
    if project.requirement_card:
        for key, data in project.requirement_card.items():
            from app.core.slots import SlotState
            state_str = data.get("state", "empty")
            try:
                state = SlotState(state_str)
                engine.slot_manager.update_slot(key, data.get("value", ""), state)
            except ValueError:
                pass

    # Load conversation history
    history_result = await db.execute(
        select(Conversation)
        .where(Conversation.project_id == project_id)
        .order_by(Conversation.created_at.asc())
    )
    for msg in history_result.scalars():
        engine.conversation_history.append({
            "role": msg.role,
            "content": msg.content,
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

            # If project is already past Stage ①, redirect
            if engine is None and project is not None:
                outputs = project.stage_outputs or {}
                thinking = outputs.get("thinking", {})
                proto = outputs.get("prototype", {})

                await websocket.send_json({
                    "type": "stage_state",
                    "stage": project.stage,
                    "thinking_report": thinking.get("report"),
                    "prototype_html": proto.get("html"),
                    "validation": proto.get("validation"),
                })
                await websocket.close()
                return

            # Send welcome if first message (only initial_idea in history, no DB msgs)
            if len(engine.conversation_history) <= 1:
                welcome = "你好！我是 AIPM Agent。请告诉我你的产品想法，我来帮你逐步梳理。"
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
                conv = Conversation(
                    project_id=project_id,
                    role="user",
                    content=user_message,
                )
                db.add(conv)

                # Process with inquiry engine
                result = await engine.chat(user_message)

                # Save assistant message
                conv_assistant = Conversation(
                    project_id=project_id,
                    role="assistant",
                    content=result["reply"],
                )
                db.add(conv_assistant)
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

                # Stage ① complete → auto advance to Stage ② + ③
                if result["stage_complete"] and result.get("requirement_card"):
                    pipeline_result = await advance_to_thinking(
                        project_id,
                        result["requirement_card"],
                    )
                    response["stage_transition"] = {
                        "from": ProjectStage.IDEA,
                        "to": pipeline_result.get("new_stage", ProjectStage.STRUCTURE),
                    }
                    response["thinking_report"] = pipeline_result.get("thinking_report")
                    response["structure"] = pipeline_result.get("structure")

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
