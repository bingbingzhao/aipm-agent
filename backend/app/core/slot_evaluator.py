"""LLM-based Slot Saturation Evaluator V2.

Adds confidence scoring and smarter evaluation logic:
- Each slot evaluation now includes a confidence score (0.0-1.0)
- stage_ready requires NOT just saturated, but high confidence
- Evaluator tracks evaluation history to avoid flip-flopping
"""

from __future__ import annotations

from typing import Optional

from app.core.llm import llm_chat
from app.core.slots import SlotManager, SlotState

EVAL_SYSTEM_PROMPT = """你是产品需求分析专家。判断需求维度的收集进度。

## 判断标准

- **saturated**（信息足够支撑设计决策）：
  - product_type：明确了品类归属 + 至少一个核心功能方向。只要用户描述了产品做什么（如"帮骑手优化路线"/"AI生成周报"），即视为 saturated。不需要用户明确说出"这是一个XX工具"这种标签。
  - target_user：明确了具体人群 + 至少一个使用场景/触发时刻
  - core_problem：描述了具体痛点 + 有一定严重程度（定量或定性）
  - existing_solutions：提到了至少一个当前替代方案及其局限
- **partial**：方向对但缺乏具体细节（如"做给程序员的"但没说哪种程序员、什么场景）
- **empty**：完全没讨论

## 可减少追问的信号
- 用户反复回答同一角度但给不出更多细节 → 已有信息即为最佳
- 用户明显回避或不想展开某个话题 → 标注为 saturated 并记录"信息有限"
- unique_value / monetization 只要提过一嘴即可 saturated
- technical_constraints / regulatory_concerns 无特殊提到则直接 saturated

## 置信度评分
对每个维度的饱和判断，加上一个 0.0-1.0 的置信度：
- 1.0 = 用户明确给出完整答案
- 0.7-0.9 = 信息够用但可以问更深
- 0.4-0.6 = 信息方向对但模糊
- 0.0-0.3 = 几乎没有有效信息

## 维度
1. product_type 2. target_user 3. core_problem 4. existing_solutions
5. unique_value 6. monetization 7. technical_constraints 8. regulatory_concerns

## 输出 JSON
{
    "product_type": {"state": "saturated|partial|empty", "confidence": 0.9, "summary": "30字总结"},
    "target_user": {"state": "...", "confidence": 0.8, "summary": "..."},
    "core_problem": {"state": "...", "confidence": 0.7, "summary": "..."},
    "existing_solutions": {"state": "...", "confidence": 0.5, "summary": "..."},
    "unique_value": {"state": "...", "confidence": 0.5, "summary": "..."},
    "monetization": {"state": "...", "confidence": 0.5, "summary": "..."},
    "technical_constraints": {"state": "...", "confidence": 1.0, "summary": "..."},
    "regulatory_concerns": {"state": "...", "confidence": 1.0, "summary": "..."},
    "overall_ready": true/false,
    "ready_confidence": 0.85
}

**overall_ready = 前4个维度都是 saturated 且平均置信度 ≥ 0.7**
**ready_confidence = 前4个维度置信度的平均值**
只输出 JSON，不要其他文字。"""


class SlotEvaluator:
    """Evaluates slot saturation using LLM analysis of conversation content."""

    def __init__(self):
        self._evaluation_count: int = 0
        self._eval_interval: int = 1  # Every turn — confidence scoring prevents premature saturation
        # Track history to avoid flip-flopping
        self._eval_history: list[dict] = []

    def should_evaluate(self) -> bool:
        """Check if it's time to run evaluation.

        V2: Evaluate every 2 turns to reduce LLM calls and avoid noisy flip-flops.
        """
        self._evaluation_count += 1
        return self._evaluation_count % self._eval_interval == 0

    async def evaluate(
        self,
        conversation_history: list[dict],
        slot_manager: SlotManager,
    ) -> dict:
        """Run LLM evaluation of current slot saturation."""
        history_text = self._format_history(conversation_history)
        current_state_text = self._format_current_state(slot_manager)

        messages = [
            {"role": "system", "content": EVAL_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"当前各维度状态：\n{current_state_text}\n\n"
                    f"对话历史（最近6轮）：\n{history_text}\n\n"
                    f"请评估各维度饱和度并输出 JSON。"
                )
            },
        ]

        try:
            result = await llm_chat(messages, temperature=0.1)
            evaluation = self._parse_json(result)
            self._apply_evaluation(evaluation, slot_manager)

            # Track for history
            self._eval_history.append(evaluation)
            if len(self._eval_history) > 10:
                self._eval_history = self._eval_history[-10:]

            import logging
            logger = logging.getLogger(__name__)
            saturated = sum(
                1 for d in evaluation.values()
                if isinstance(d, dict) and d.get("state") == "saturated"
            )
            confidence = evaluation.get("ready_confidence", 0.0)
            logger.info(
                f"Evaluator: {saturated}/8 saturated, "
                f"overall_ready={evaluation.get('overall_ready')}, "
                f"ready_confidence={confidence:.2f}"
            )

            # Attach confidence to evaluation for caller
            evaluation["_confidence"] = confidence
            return evaluation
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Evaluator failed: {e}, keeping previous states")
            return {}

    def _format_history(self, history: list[dict]) -> str:
        """Format conversation history for evaluation.

        V2: Focus on the last 6 messages for more precise evaluation.
        """
        lines = []
        for msg in history[-12:]:
            role = "用户" if msg["role"] == "user" else "助手"
            content = msg["content"][:300]
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
            lines.append(
                f"- {state_emoji.get(slot.state, '❓')} {slot.label}: "
                f"{slot.value[:80] if slot.value else '(空)'}"
            )
        return "\n".join(lines)

    def _parse_json(self, text: str) -> dict:
        """Extract JSON from LLM response. Handles markdown code blocks."""
        import json
        import re

        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            return json.loads(json_match.group())
        raise ValueError("No JSON found in response")

    def _apply_evaluation(self, evaluation: dict, slot_manager: SlotManager):
        """Apply LLM evaluation results to the slot manager.

        V2: Uses confidence scores to avoid premature saturation.
        Only marks a slot as SATURATED if confidence ≥ 0.6.
        """
        state_map = {
            "empty": SlotState.EMPTY,
            "partial": SlotState.PARTIAL,
            "saturated": SlotState.SATURATED,
        }

        for key, data in evaluation.items():
            if key in ("overall_ready", "ready_confidence", "_confidence"):
                continue
            if key in slot_manager.slots and isinstance(data, dict):
                state_str = data.get("state", "empty")
                confidence = data.get("confidence", 0.5)
                summary = data.get("summary", "")

                # Don't downgrade saturated → partial if previously saturated
                # (avoid flip-flopping)
                current_slot = slot_manager.slots[key]
                new_state = state_map.get(state_str, SlotState.EMPTY)

                if current_slot.state == SlotState.SATURATED and new_state != SlotState.SATURATED:
                    # Only downgrade if confidence is very low (< 0.3)
                    if confidence >= 0.3:
                        continue  # Keep saturated

                # Don't mark as saturated if confidence is too low
                if new_state == SlotState.SATURATED and confidence < 0.6:
                    new_state = SlotState.PARTIAL

                slot_manager.update_slot(key, summary, new_state)

    @property
    def eval_interval(self) -> int:
        return self._eval_interval

    @eval_interval.setter
    def eval_interval(self, value: int):
        self._eval_interval = max(1, value)
