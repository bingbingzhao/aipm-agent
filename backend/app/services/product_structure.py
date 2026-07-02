"""Product Structure — Stage ③ 产品结构.

Analyzes the thinking report and requirement card to generate:
- Information architecture (site/module hierarchy)
- Feature tree (functional breakdown with priorities)
- Page routing plan
- Data model sketch
"""

from __future__ import annotations

from app.core.llm import llm_chat

STRUCTURE_SYSTEM_PROMPT = """你是一个资深信息架构师。基于产品思路分析，输出结构化的产品架构方案。

## 输出格式

按以下 JSON 格式输出（只输出 JSON，不要其他内容）：

```json
{
  "information_architecture": {
    "modules": [
      {
        "name": "模块名",
        "description": "简述",
        "pages": ["页面路由1", "页面路由2"],
        "priority": "p0|p1|p2"
      }
    ],
    "navigation": {
      "primary": ["主导航项1", "主导航项2"],
      "secondary": ["辅助导航项1"]
    }
  },
  "feature_tree": [
    {
      "id": "feat-xxx",
      "name": "功能名",
      "description": "功能说明",
      "priority": "p0|p1|p2",
      "children": [
        {"id": "sub-xxx", "name": "子功能", "description": "说明"}
      ]
    }
  ],
  "route_plan": [
    {
      "route": "/path",
      "title": "页面标题",
      "description": "页面功能",
      "components": ["组件1", "组件2"],
      "auth_required": false
    }
  ],
  "data_entities": [
    {
      "name": "实体名",
      "fields": [
        {"name": "字段名", "type": "字段类型", "description": "说明", "required": true}
      ],
      "relationships": ["关联实体"]
    }
  ],
  "summary": "架构概述（2-3句话）"
}
```

## 要点

- modules 按用户视角划分，不是按技术模块划分
- feature_tree 要有层级，不超过3层
- route_plan 覆盖所有页面路由
- data_entities 列出核心数据模型
- 所有 priority 用 p0/p1/p2
"""


class ProductStructureGenerator:
    """Generates product structure from thinking report."""

    async def generate(self, thinking_report: str, requirement_card: dict) -> dict:
        """Generate product structure from thinking report and requirement card."""
        # Build summary from requirement card
        card_summary = "\n".join(
            f"- {v.get('label', k)}: {v.get('value', '')}"
            for k, v in requirement_card.items()
            if v.get("state") == "saturated"
        )

        # Truncate thinking report to key parts (first 1000 chars)
        report_brief = thinking_report[:1000]

        prompt = f"""## 产品需求
{card_summary}

## 产品思路分析
{report_brief}

请基于以上信息，生成完整的产品架构方案。输出 JSON 格式。"""

        messages = [
            {"role": "system", "content": STRUCTURE_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        result = await llm_chat(messages, temperature=0.3)

        # Parse JSON from response
        import json
        import re

        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Fallback: return raw text
        return {"raw": result, "parse_error": True}
