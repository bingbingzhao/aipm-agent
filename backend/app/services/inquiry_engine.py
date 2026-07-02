"""Inquiry Engine — Stage ① 想法捕获.

Core: Multi-turn guided conversation to fill the requirement card.
Uses slot system + LLM-driven saturation evaluation.
"""

from __future__ import annotations

from app.core.llm import llm_chat
from app.core.slots import REQUIREMENT_SLOTS, SlotManager, SlotState
from app.core.slot_evaluator import SlotEvaluator

INQUIRY_SYSTEM_PROMPT = """你是一个产品顾问，用聊天的语气帮人理清产品想法。

对话风格：
- 像朋友聊天，不套模板
- 回复短而自然，一到三句话
- 用"你"不用"用户"，用"我们"不用"该产品"
- 禁止说"明白了"、"了解了"、"很好的问题"这类话术开头
- 直接追问，不铺垫
- 偶尔给一句实在的反馈（不要太狗腿，不需要每句都夸）

你需要了解的（按优先级）：
1. 这是什么类型的产品？
2. 谁会用它？
3. 它要解决什么问题？
4. 现在大家怎么解决的？
5-6. 差异化、怎么赚钱（次要，碰得到就问）

首次对话：简单打个招呼，确认想法，然后自然问一个关键问题。
不要问"还有什么需要补充的吗"这种开放式问题——要有指向性。"""


class InquiryEngine:
    """Manages the inquiry conversation for Stage ①.

    Architecture:
    - Main LLM call: generates the conversational reply + decides next question
    - Evaluator LLM call (every N turns): analyzes saturation of each slot
    """

    def __init__(self, initial_idea: str = ""):
        self.slot_manager = SlotManager()
        self.evaluator = SlotEvaluator()
        self.initial_idea = initial_idea
        self.conversation_history: list[dict] = []
        if initial_idea:
            self.conversation_history.append({
                "role": "user",
                "content": f"我想做一个产品：{initial_idea}"
            })

    def build_messages(self) -> list[dict]:
        """Build full message list for LLM chat call, including slot context."""
        messages = [{"role": "system", "content": INQUIRY_SYSTEM_PROMPT}]

        # Inject current slot saturation context
        slot_context = self._build_slot_context()
        if slot_context:
            messages.append({
                "role": "system",
                "content": slot_context,
            })

        messages.extend(self.conversation_history)

        # Add explicit next-slot guidance
        next_slot = self.slot_manager.get_next_to_ask()
        if next_slot:
            hint = self._next_question_hint(next_slot)
            messages.append({
                "role": "system",
                "content": hint,
            })

        return messages

    def _build_slot_context(self) -> str:
        """Build a context message describing current slot states."""
        lines = ["[需求收集进度]"]
        for key, slot in self.slot_manager.slots.items():
            state_emoji = {
                SlotState.EMPTY: "⬜",
                SlotState.PARTIAL: "🟡",
                SlotState.SATURATED: "🟢",
            }
            lines.append(f"  {state_emoji.get(slot.state, '❓')} {slot.label}: {slot.value or '(空)'}")
        lines.append("🟢=已充分 (勿追问) | 🟡⬜=需收集")
        return "\n".join(lines)

    def _next_question_hint(self, slot) -> str:
        """Generate a natural hint for the next question to ask."""
        if slot.state == SlotState.EMPTY:
            return f"[指引] 请自然引入关于「{slot.label}」的问题。用户还没有提供这方面信息。"
        elif slot.state == SlotState.PARTIAL:
            return f"[指引] 请深入追问「{slot.label}」，用户只给了不完整的回答。当前信息：{slot.value}"
        return ""

    async def chat(self, user_message: str) -> dict:
        """Process a user message and return the AI response."""
        self.conversation_history.append({"role": "user", "content": user_message})

        # Build messages and generate response
        messages = self.build_messages()
        reply = await llm_chat(messages, temperature=0.8)

        self.conversation_history.append({"role": "assistant", "content": reply})

        # Run LLM-based slot evaluation every N turns
        if self.evaluator.should_evaluate():
            self.slot_manager.auto_saturate_conditionals()
            await self.evaluator.evaluate(
                self.conversation_history,
                self.slot_manager,
            )

        saturated = self.slot_manager.saturated

        return {
            "reply": reply,
            "stage_complete": saturated,
            "requirement_card": self.slot_manager.requirement_card,
            "next_slot": (
                self.slot_manager.get_next_to_ask().label
                if not saturated else None
            ),
        }
