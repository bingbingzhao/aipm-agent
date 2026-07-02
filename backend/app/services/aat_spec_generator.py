"""AAT Spec Generator — LLM-driven extraction in multiple passes.

Takes AIPM pipeline outputs and generates a complete AATProductSpec
with features, pages, flows, API contracts, and business rules.

Uses separate LLM calls for each section to avoid token limits.
"""

from __future__ import annotations

from app.core.llm import llm_chat

# ─── Individual section prompts ───

FEATURES_PROMPT = """基于产品分析文档，提取功能列表和验收标准。

输出严格 JSON（不要 markdown）：

{
  "features": [
    {
      "id": "feat-001",
      "name": "功能名",
      "description": "描述",
      "priority": "p0|p1|p2",
      "depends_on": [],
      "tags": [],
      "criteria": [
        {"description": "验收标准", "criteria_type": "functional|edge_case|error|ui", "given": "前置", "when": "操作", "then": "预期", "priority": "p0|p1", "tags": []}
      ]
    }
  ]
}

每个功能至少 2 条 criteria。criteria_type 多样化。"""

PAGES_PROMPT = """基于路由规划和功能架构，提取页面定义和交互元素。

输出严格 JSON：

{
  "pages": [
    {
      "route": "/path",
      "title": "页面标题",
      "description": "描述",
      "states": ["default", "loading", "error"],
      "elements": [
        {"selector": ".btn", "tag": "button", "type": "button", "text": "文本", "role": "button", "inputType": "", "placeholder": ""}
      ]
    }
  ]
}

每个页面至少 3 个元素，选择器要像真实 CSS（.class, [data-testid], text=文本）。"""

FLOWS_PROMPT = """基于产品功能，提取核心用户流程。

输出严格 JSON：

{
  "flows": [
    {
      "id": "flow-001",
      "name": "流程名称",
      "description": "描述",
      "start_page": "/",
      "feature_id": "feat-001",
      "steps": [
        {"action": "navigate|click|fill|select|wait|assert", "target": "选择器", "value": "值", "description": "说明"}
      ]
    }
  ]
}

提取 2-3 个核心流程，每个 4-8 步。选择器要可执行（.class, [data-testid], text=文本）。"""

API_PROMPT = """基于数据实体和功能描述，推断 RESTful API 契约。

输出严格 JSON：

{
  "api_contracts": [
    {
      "method": "GET|POST|PUT|DELETE",
      "path": "/api/resource",
      "summary": "简述",
      "description": "描述",
      "auth_required": false,
      "tags": [],
      "query_params": [],
      "path_params": [],
      "responses": {"200": {"description": "成功"}, "400": {"description": "错误"}}
    }
  ]
}

每个数据实体至少 GET+POST。每个业务操作推断合理 API。"""

RULES_PROMPT = """基于 PRD 和业务逻辑，提取业务规则。

输出严格 JSON：

{
  "business_rules": [
    {
      "id": "rule-001",
      "name": "规则名",
      "description": "描述",
      "rule_type": "validation|authorization|rate_limit|data_integrity",
      "condition": "条件",
      "expected_behavior": "预期行为",
      "related_features": ["feat-001"]
    }
  ]
}

提取 3-6 条关键规则。"""


def _parse_llm_json(result: str) -> dict:
    """Parse LLM JSON output, handling truncation and markdown fences."""
    import json, re
    import logging
    logger = logging.getLogger(__name__)
    
    clean = result.strip()
    clean = re.sub(r'^```(?:json)?\s*\n?', '', clean)
    clean = re.sub(r'\n?```\s*$', '', clean)
    clean = clean.strip()
    
    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        # Try regex extraction
        m = re.search(r'\{[\s\S]*\}', clean)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
        # Graceful: try to salvage truncated JSON by closing arrays/objects
        salvaged = _salvage_truncated_json(clean)
        if salvaged:
            return salvaged
        logger.warning(f"JSON parse failed: {e}")
        return {}


def _salvage_truncated_json(text: str) -> dict | None:
    """Attempt to salvage truncated JSON by closing open structures."""
    import json, re
    
    # Find the last valid JSON structure before truncation
    # Try progressively shorter prefixes
    for end in range(len(text), max(len(text) - 200, 0), -1):
        truncated = text[:end]
        # Try to close open strings
        if truncated.rstrip().endswith('"'):
            # Might be mid-string, try removing the last quote
            pass
        # Try adding closing brackets
        for suffix in ["}", "]}", "}]}"]:
            attempt = truncated.rstrip().rstrip(',') + suffix
            try:
                result = json.loads(attempt)
                # Make sure we got at least some data
                if any(isinstance(v, list) and len(v) > 0 for v in result.values()):
                    return result
            except json.JSONDecodeError:
                continue
    
    return None


def _build_context(
    project_name: str,
    project_description: str,
    thinking_report: str,
    structure: dict,
    prd_document: str,
) -> str:
    """Build shared context for all LLM calls."""
    parts = [f"# {project_name}\n{project_description}"]

    if thinking_report:
        parts.append(f"\n## 产品思路\n{thinking_report[:1200]}")

    if structure and not structure.get("parse_error"):
        ft = structure.get("feature_tree", [])
        if ft:
            ft_text = "\n".join(
                f"- {f.get('name', '')} [{f.get('priority', '')}]"
                for f in ft[:10]
            )
            parts.append(f"\n## 功能架构\n{ft_text}")

        routes = structure.get("route_plan", [])
        if routes:
            rt_text = "\n".join(
                f"- {r.get('route', '/')}: {r.get('title', '')}"
                for r in routes[:15]
            )
            parts.append(f"\n## 路由规划\n{rt_text}")

        entities = structure.get("data_entities", [])
        if entities:
            ent_text = "\n".join(
                f"- {e.get('name', '')}: {', '.join(f.get('name','')+':'+f.get('type','string') for f in e.get('fields',[]))}"
                for e in entities[:8]
            )
            parts.append(f"\n## 数据实体\n{ent_text}")

    if prd_document:
        parts.append(f"\n## PRD 功能需求\n{prd_document[:1500]}")

    return "\n".join(parts)


class AATSpecGenerator:
    """Multi-pass LLM-driven AAT product spec extraction."""

    async def generate(
        self,
        project_name: str,
        project_description: str,
        thinking_report: str,
        structure: dict,
        prd_document: str,
        delivery: dict | None = None,
    ) -> dict:
        """Generate complete AATProductSpec from pipeline outputs."""
        context = _build_context(
            project_name, project_description,
            thinking_report, structure, prd_document,
        )

        kwargs = {"temperature": 0.3, "max_tokens": 4096}  # larger output for each section

        # 1. Features
        f_result = await llm_chat([
            {"role": "system", "content": FEATURES_PROMPT},
            {"role": "user", "content": context + "\n\n提取功能列表和验收标准。"},
        ], **kwargs)
        features_data = _parse_llm_json(f_result)

        # 2. Pages (context includes routes)
        p_result = await llm_chat([
            {"role": "system", "content": PAGES_PROMPT},
            {"role": "user", "content": context + "\n\n提取页面定义。"},
        ], **kwargs)
        pages_data = _parse_llm_json(p_result)

        # 3. Flows
        fl_result = await llm_chat([
            {"role": "system", "content": FLOWS_PROMPT},
            {"role": "user", "content": context + "\n\n提取核心用户流程。"},
        ], **kwargs)
        flows_data = _parse_llm_json(fl_result)

        # 4. API contracts
        a_result = await llm_chat([
            {"role": "system", "content": API_PROMPT},
            {"role": "user", "content": context + "\n\n推断 API 契约。"},
        ], **kwargs)
        api_data = _parse_llm_json(a_result)

        # 5. Business rules
        r_result = await llm_chat([
            {"role": "system", "content": RULES_PROMPT},
            {"role": "user", "content": context + "\n\n提取业务规则。"},
        ], **kwargs)
        rules_data = _parse_llm_json(r_result)

        # Merge
        return {
            "features": features_data.get("features", []),
            "pages": pages_data.get("pages", []),
            "flows": flows_data.get("flows", []),
            "api_contracts": api_data.get("api_contracts", []),
            "business_rules": rules_data.get("business_rules", []),
        }
