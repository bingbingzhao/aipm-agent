"""Inquiry Engine — Stage ① 想法捕获.

Core: Multi-turn guided conversation to fill the requirement card.
Uses slot system + LLM-driven saturation evaluation.
"""

from __future__ import annotations

from app.core.llm import llm_chat
from app.core.slots import REQUIREMENT_SLOTS, SlotManager, SlotState
from app.core.slot_evaluator import SlotEvaluator

INQUIRY_SYSTEM_PROMPT = """你是一个专业的产品经理 AI 助手，你的任务是通过对话帮助用户清晰定义他们的产品想法。

核心原则：
1. **主动引导**：你是对话的主导者，每次回复后必须主动追问一个关键问题
2. **逐个深入**：每次只追一个问题，不要一次抛多个
3. **自然过渡**：追问要结合对话上下文自然引出，不要生硬切换话题
4. **避免重复**：已经充分讨论的维度不要回头再问
5. **保持对话感**：你不是在填表，你是在和用户聊天，但要专业且有深度
6. **短回复**：每次回复控制在 80-150 字，问题清晰即可

你需要收集的关键信息：
- 产品类型：SaaS/B2B/消费者工具/内容平台？
- 核心用户：谁会使用？典型特征？
- 核心问题：解决什么痛点？现有方案哪里不好？
- 现有解决方案：用户现在怎么解决的？竞品有哪些？
- 差异化价值：你的方案有什么不同？
- 商业模式：如何盈利？

每次对话开始时，先确认产品的初步想法，然后选择最关键、用户还没说清楚的维度开始追问。
"""


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
        lines = ["[内部状态] 当前需求维度收集进度："]
        for key, slot in self.slot_manager.slots.items():
            state_emoji = {
                SlotState.EMPTY: "⬜",
                SlotState.PARTIAL: "🟡",
                SlotState.SATURATED: "🟢",
            }
            lines.append(
                f"  {state_emoji.get(slot.state, '❓')} {slot.label} "
                f"({slot.state.value}): {slot.value or '尚未收集'}"
            )
        lines.append("注意：🟢 表示信息已经充分，不要再追问。🟡 和 ⬜ 表示还需要收集。")
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
            await self.evaluator.evaluate(
                self.conversation_history,
                self.slot_manager,
            )

        saturated = self.slot_manager.saturated

        return {
            "reply": reply,
            "stage_complete": saturated,
            "requirement_card": self.slot_manager.requirement_card if saturated else None,
            "next_slot": (
                self.slot_manager.get_next_to_ask().label
                if not saturated else None
            ),
        }
