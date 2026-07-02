"""Product Thinking — Stage ② 产品思路.

from __future__ import annotations

Analyzes the completed requirement card and generates:
- Product positioning
- User personas
- Core scenarios
- Competitive analysis
- Feasibility assessment
"""

from app.core.llm import llm_chat

THINKING_SYSTEM_PROMPT = """你是一个资深产品战略顾问。基于用户提供的需求卡片信息，输出一份结构化的产品思路分析。

请按以下结构输出：

## 产品定位
- 一句话定位
- 产品愿景
- 核心价值主张

## 用户画像
- 主要用户群体（2-3个）
- 每个群体的特征、痛点、目标

## 核心场景
- 主要使用场景（3-5个）
- 每个场景的用户旅程

## 竞品分析
- 直接竞品
- 间接竞品
- 差异化机会

## 可行性评估
- 技术可行性
- 市场可行性
- 风险提示
"""


class ProductThinking:
    """Generates product thinking analysis from requirement card."""

    async def analyze(self, requirement_card: dict) -> str:
        """Generate a full product thinking report."""
        card_text = "\n".join(
            f"- {v['label']}: {v['value']}"
            for v in requirement_card.values()
        )

        messages = [
            {"role": "system", "content": THINKING_SYSTEM_PROMPT},
            {"role": "user", "content": f"以下是需求卡片：\n\n{card_text}\n\n请输出产品思路分析。"}
        ]

        return await llm_chat(messages, temperature=0.7)
