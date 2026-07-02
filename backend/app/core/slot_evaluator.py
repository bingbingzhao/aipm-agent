"""LLM-based Slot Saturation Evaluator.

Evaluates how well each requirement slot has been filled based on
the actual conversation content, replacing the naive round-count heuristic.
"""

from __future__ import annotations

from typing import Optional

from app.core.llm import llm_chat
from app.core.slots import SlotManager, SlotState

EVAL_SYSTEM_PROMPT = """你是产品需求分析专家。快速判断需求维度的收集进度。

## 判断标准（宽松，够用即饱和）

- **saturated**：信息足够支撑产品设计。阈值极低：
  - product_type：只要提到品类（SaaS/工具/App）→ saturated
  - target_user：只要提到目标人群（程序员/企业/学生）→ saturated  
  - core_problem：只要描述了痛点（效率低/太贵/不好用）→ saturated
  - existing_solutions：哪怕说"没有好方案"也→ saturated
  - unique_value/monetization：只要提过一嘴→ saturated
  - technical_constraints/regulatory：无特殊要求→ saturated（直接标，不用等用户提）
- **partial**：只有极含糊时（"做给所有人"），且前4个关键维度不要给 partial
- **empty**：完全没讨论，且仅用于后4个维度

## 维度

1. product_type 2. target_user 3. core_problem 4. existing_solutions
5. unique_value 6. monetization 7. technical_constraints 8. regulatory_concerns

## 输出 JSON

{"product_type":{"state":"saturated|partial|empty","summary":"20字总结"},..."overall_ready":true/false}

**overall_ready = 前4个维度都是 saturated**
**第7、8维度（技术约束/合规）无特殊要求时直接标 saturated**
只输出 JSON，不要其他文字。"""


class SlotEvaluator:
    """Evaluates slot saturation using LLM analysis of conversation content."""

    def __init__(self):
        self._evaluation_count: int = 0
        # Evaluate every turn after first exchange for faster completion
        self._eval_interval: int = 1

    def should_evaluate(self) -> bool:
        """Check if it's time to run evaluation."""
        self._evaluation_count += 1
        return self._evaluation_count % self._eval_interval == 0

    async def evaluate(
        self,
        conversation_history: list[dict],
        slot_manager: SlotManager,
    ) -> dict:
        """Run LLM evaluation of current slot saturation.

        Returns the updated slot states and whether the card is ready.
        """
        # Build the evaluation message
        history_text = self._format_history(conversation_history)
        current_state_text = self._format_current_state(slot_manager)

        messages = [
            {"role": "system", "content": EVAL_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"当前各维度状态：\n{current_state_text}\n\n对话历史：\n{history_text}\n\n请评估各维度饱和度并输出 JSON。"
            },
        ]

        try:
            result = await llm_chat(messages, temperature=0.2)
            evaluation = self._parse_json(result)
            self._apply_evaluation(evaluation, slot_manager)
            
            import logging
            logger = logging.getLogger(__name__)
            saturated = sum(1 for d in evaluation.values() if isinstance(d, dict) and d.get("state") == "saturated")
            logger.info(f"Evaluator: {saturated}/8 slots saturated, overall_ready={evaluation.get('overall_ready')}")
            
            return evaluation
        except Exception:
            # Fallback: keep current states unchanged
            return {}

    def _format_history(self, history: list[dict]) -> str:
        lines = []
        for msg in history[-16:]:  # Last 16 messages for context
            role = "用户" if msg["role"] == "user" else "助手"
            content = msg["content"][:500]  # More content per message
            lines.append(f"[{role}] {content}")
        return "\n".join(lines)

    def _format_current_state(self, slot_manager: SlotManager) -> str:
        lines = []
        for key, slot in slot_manager.slots.items():
            state_emoji = {
                SlotState.EMPTY: "⬜",
                SlotState.PARTIAL: "🟡",
                SlotState.SATURATED: "🟢",
            }
            lines.append(f"- {state_emoji.get(slot.state, '❓')} {slot.label}: {slot.value or '(空)'}")
        return "\n".join(lines)

    def _parse_json(self, text: str) -> dict:
        """Extract JSON from LLM response. Handles markdown code blocks."""
        import json
        import re

        # Try to find JSON block
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            return json.loads(json_match.group())
        raise ValueError("No JSON found in response")

    def _apply_evaluation(self, evaluation: dict, slot_manager: SlotManager):
        """Apply LLM evaluation results to the slot manager."""
        state_map = {
            "empty": SlotState.EMPTY,
            "partial": SlotState.PARTIAL,
            "saturated": SlotState.SATURATED,
        }

        for key, data in evaluation.items():
            if key == "overall_ready":
                continue
            if key in slot_manager.slots and isinstance(data, dict):
                state_str = data.get("state", "empty")
                summary = data.get("summary", "")
                new_state = state_map.get(state_str, SlotState.EMPTY)
                slot_manager.update_slot(key, summary, new_state)

    @property
    def eval_interval(self) -> int:
        return self._eval_interval

    @eval_interval.setter
    def eval_interval(self, value: int):
        self._eval_interval = max(1, value)
