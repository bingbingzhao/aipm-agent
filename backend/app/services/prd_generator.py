"""PRD Generator — Stage ⑤ PRD 文档生成。

Assembles all previous stage outputs into a comprehensive PRD document.
Input: thinking report + structure + prototype HTML + requirement card
Output: Structured PRD markdown
"""

from __future__ import annotations

from app.core.llm import llm_chat

PRD_SYSTEM_PROMPT = """你是一个资深产品经理。基于以下所有产品资料，生成一份完整的、可直接交付给开发团队的产品需求文档（PRD）。

## 输出格式

严格按以下 Markdown 结构输出：

# {产品名称} — 产品需求文档

## 1. 概述
- 产品简介（一句话）
- 产品愿景
- 目标用户
- 核心价值主张

## 2. 产品思路
（整合 thinking report 的核心内容）
- 市场分析
- 竞品对比
- 可行性评估

## 3. 功能需求
（基于 feature_tree 和 modules 详细展开）
对每个 P0/P1 功能：
- 功能名称
- 用户故事（As a... I want... So that...）
- 验收标准（When... Then...）
- 优先级

## 4. 页面与路由
（基于 route_plan）
列出所有页面及其核心功能说明

## 5. 数据模型
（基于 data_entities）
列出核心数据实体及其字段定义

## 6. 非功能性需求
- 性能要求
- 安全要求
- 兼容性
- 可访问性

## 7. 技术约束与依赖
- 技术栈建议
- 第三方依赖
- 集成点

## 8. 成功指标
- 可量化的 KPI（至少 3 个）
- 验收标准

## 9. 里程碑与时间线
- Phase 1（MVP）：核心功能 + 时间估算
- Phase 2：增强功能
- Phase 3：优化迭代

## 要点

- 语言专业、具体、可执行
- 用户故事遵循标准格式
- 验收标准要具体到操作步骤和预期结果
- 所有观点基于提供的资料，不凭空编造
"""


class PRDGenerator:
    """Generates a comprehensive PRD from all stage outputs."""

    async def generate(
        self,
        project_name: str,
        requirement_card: dict,
        thinking_report: str,
        structure: dict,
        prototype_html: str = "",
    ) -> str:
        """Generate a complete PRD document.

        Args:
            project_name: Project/product name
            requirement_card: Stage ① requirement card
            thinking_report: Stage ② thinking report
            structure: Stage ③ structure (JSON)
            prototype_html: Stage ④ prototype HTML (optional, for context)
        """
        # Build context from all stages
        card_text = "\n".join(
            f"- {v.get('label', k)}: {v.get('value', '')}"
            for k, v in requirement_card.items()
            if v.get("state") == "saturated"
        )

        # Structure context
        structure_text = ""
        if structure and not structure.get("parse_error"):
            # Modules
            modules = structure.get("information_architecture", {}).get("modules", [])
            if modules:
                structure_text += "\n### 功能模块\n"
                for m in modules:
                    structure_text += f"- **{m.get('name', '')}** [{m.get('priority', '')}]: {m.get('description', '')}\n"

            # Features
            features = structure.get("feature_tree", [])
            if features:
                structure_text += "\n### 功能树\n"
                structure_text += _format_feature_tree(features)

            # Routes
            routes = structure.get("route_plan", [])
            if routes:
                structure_text += "\n### 页面路由\n"
                for r in routes:
                    structure_text += f"- `{r.get('route', '/')}` — {r.get('title', '')}: {r.get('description', '')}\n"

            # Data entities
            entities = structure.get("data_entities", [])
            if entities:
                structure_text += "\n### 数据模型\n"
                for e in entities:
                    fields = ", ".join(
                        f"{f.get('name', '')}:{f.get('type', 'string')}"
                        for f in e.get("fields", [])
                    )
                    structure_text += f"- **{e.get('name', '')}**: {fields}\n"

        # Prototype context (brief)
        proto_context = ""
        if prototype_html:
            proto_context = (
                f"\n### 原型已生成\n"
                f"HTML 长度: {len(prototype_html)} 字符\n"
                f"（原型内容已在 Stage ④ 交付，PRD 中引用即可）"
            )

        # Build prompt
        prompt = f"""请为产品「{project_name}」生成完整 PRD。

## 需求卡片
{card_text}

## 产品思路
{thinking_report[:2000]}

## 产品架构
{structure_text}
{proto_context}

请按照输出格式生成完整 PRD。"""

        messages = [
            {"role": "system", "content": PRD_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        return await llm_chat(messages, temperature=0.3, max_tokens=4096)


def _format_feature_tree(features: list[dict], indent: int = 0) -> str:
    """Recursively format feature tree."""
    lines = []
    prefix = "  " * indent
    for f in features:
        name = f.get("name", "")
        desc = f.get("description", "")
        priority = f.get("priority", "")
        line = f"{prefix}- **{name}** [{priority}]"
        if desc:
            line += f": {desc}"
        lines.append(line)
        children = f.get("children", [])
        if children:
            lines.append(_format_feature_tree(children, indent + 1))
    return "\n".join(lines)
