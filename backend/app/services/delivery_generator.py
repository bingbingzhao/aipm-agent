"""Delivery Generator — Stage ⑥ 交付。

Takes the PRD + structure and generates development-ready:
- Epic breakdown (feature groups mapped to sprints)
- User stories with story points
- Task list with estimates
- Sprint planning suggestions
"""

from __future__ import annotations

from app.core.llm import llm_chat

DELIVERY_SYSTEM_PROMPT = """你是一个资深技术项目经理。基于产品 PRD 和架构方案，生成可交付的开发任务包。

## 输出格式

严格按以下 JSON 格式输出（只输出 JSON）：

```json
{
  "epics": [
    {
      "id": "epic-xxx",
      "name": "Epic 名称",
      "description": "Epic 描述",
      "stories": [
        {
          "id": "story-xxx",
          "name": "Story 名称",
          "as_a": "用户角色",
          "i_want": "想要的功能",
          "so_that": "达成的目标",
          "acceptance_criteria": ["验收标准1", "验收标准2"],
          "story_points": 3,
          "priority": "p0|p1|p2",
          "dependencies": ["依赖的 story id"],
          "tasks": [
            {"name": "任务名", "estimate_hours": 4, "role": "frontend|backend|fullstack|design"}
          ]
        }
      ]
    }
  ],
  "sprints": [
    {
      "name": "Sprint 1",
      "goal": "Sprint 目标",
      "story_ids": ["story-xxx"],
      "duration_weeks": 2,
      "total_points": 21
    }
  ],
  "total_estimate": {
    "weeks": 8,
    "team_size": 3,
    "total_story_points": 84
  },
  "tech_stack": {
    "frontend": ["Vue 3", "Element Plus"],
    "backend": ["FastAPI", "Python"],
    "database": ["PostgreSQL"],
    "devops": ["Docker"]
  },
  "risks": [
    {"risk": "风险描述", "impact": "high|medium|low", "mitigation": "缓解措施"}
  ],
  "summary": "交付计划概述（2-3句话）"
}
```

## 估算指南
- 1 story point ≈ 半天工作量
- Epic 大小：3-8 stories
- Sprint: 2 周，21-34 points
- 前端:后端比例 ≈ 40:60
- P0 stories 必须在 Sprint 1-2 完成
"""


class DeliveryGenerator:
    """Generates development epics, stories, and sprint plans from PRD."""

    async def generate(self, prd_document: str, structure: dict) -> dict:
        """Generate delivery plan from PRD and structure."""
        # Extract key info from structure
        features_text = ""
        if structure and not structure.get("parse_error"):
            features = structure.get("feature_tree", [])
            if features:
                features_text = "功能列表:\n" + _format_features(features)

        # Use first 2500 chars of PRD for context
        prd_brief = prd_document[:2500]

        prompt = f"""## PRD 文档
{prd_brief}

{features_text}

请基于以上信息，生成开发交付计划。输出 JSON 格式。"""

        messages = [
            {"role": "system", "content": DELIVERY_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        result = await llm_chat(messages, temperature=0.3, max_tokens=4096)

        import json
        import re

        # Strip markdown code fences
        result = result.strip()
        if result.startswith("```"):
            result = re.sub(r'^```(?:json)?\s*', '', result)
            result = re.sub(r'```\s*$', '', result)
            result = result.strip()

        json_match = re.search(r'\{[\s\S]*\}', result)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # If first attempt fails, try again with strict format instruction
        messages.append({
            "role": "user",
            "content": "请严格只输出 JSON，不要用 markdown 代码块包裹。直接以 { 开头输出。"
        })
        result2 = await llm_chat(messages, temperature=0.1, max_tokens=4096)
        result2 = result2.strip()
        if result2.startswith("```"):
            result2 = re.sub(r'^```(?:json)?\s*', '', result2)
            result2 = re.sub(r'```\s*$', '', result2)
            result2 = result2.strip()
        json_match2 = re.search(r'\{[\s\S]*\}', result2)
        if json_match2:
            try:
                return json.loads(json_match2.group())
            except json.JSONDecodeError:
                pass

        return {"raw": result, "parse_error": True}


def _format_features(features: list[dict], indent: int = 0) -> str:
    lines = []
    prefix = "  " * indent
    for f in features:
        lines.append(f"{prefix}- {f.get('name', '')} [{f.get('priority', '')}]")
        for child in f.get("children", []):
            lines.append(f"{prefix}  - {child.get('name', '')}")
    return "\n".join(lines)
