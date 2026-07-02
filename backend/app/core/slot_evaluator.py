"""LLM-based Slot Saturation Evaluator.

Evaluates how well each requirement slot has been filled based on
the actual conversation content, replacing the naive round-count heuristic.
"""

from __future__ import annotations

from typing import Optional

from app.core.llm import llm_chat
from app.core.slots import SlotManager, SlotState

EVAL_SYSTEM_PROMPT = """你是一个产品需求分析专家。你的任务是快速判断对话中每个需求维度的信息是否已经"够用"。

## 判断标准

- **saturated（已饱和）**：用户给出了具体可操作的答案，足够支撑下一步的产品设计。
  例如："SaaS工具"、"技术团队10-50人"、"站会效率低"、"竞品Standuply贵" 都算 saturated
- **partial（不完整）**：用户提了但含糊（如"做给所有人用"），需要追问
- **empty（未提及）**：完全没讨论到

## 需要判断的维度

1. product_type（产品类型）
2. target_user（核心用户）
3. core_problem（核心问题）
4. existing_solutions（现有方案/竞品）
5. unique_value（差异化价值）
6. monetization（商业模式）
7. technical_constraints（技术约束）
8. regulatory_concerns（合规要求）

## 输出 JSON

```json
{
  "product_type": {"state": "saturated|partial|empty", "summary": "15字总结"},
  ...
  "overall_ready": true/false
}
```

**overall_ready=true 只需前4个维度都是 saturated**（产品类型+用户+问题+现有方案）。

注意：判断标准要务实。用户说"SaaS工具"就算 saturated。不要因为没提技术栈就说 partial。
只输出 JSON。"""


class SlotEvaluator:
    """Evaluates slot saturation using LLM analysis of conversation content."""

    def __init__(self):
        self._evaluation_count: int = 0
        # Only evaluate every N turns to control cost
        self._eval_interval: int = 2  # evaluate every 2 turns

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
