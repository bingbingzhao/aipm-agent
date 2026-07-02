"""AAT Spec Generator — 将 AIPM 项目数据组装为 AAT 可消费的产品规格。

在管线 Stage ④ (原型生成后) 和 Stage ⑤ (PRD) 时调用，
输出 AATProductSpec JSON 供 AAT 消费。
"""

from __future__ import annotations

from app.schemas.aat_schema import (
    AATProductSpec,
    ProjectMeta,
    Feature,
    AcceptanceCriteria,
    PageSpec,
    UserFlow,
    FlowStep,
    ApiContract,
    BusinessRule,
    CriteriaType,
    FeaturePriority,
    StepAction,
)


def generate_aat_spec(
    project_id: str,
    project_name: str,
    project_description: str,
    target_url: str = "",
    features: list[dict] | None = None,
    pages: list[dict] | None = None,
    flows: list[dict] | None = None,
    api_contracts: list[dict] | None = None,
    business_rules: list[dict] | None = None,
) -> AATProductSpec:
    """Generate an AAT-compatible product spec from AIPM project data."""
    return AATProductSpec(
        project=ProjectMeta(
            id=project_id,
            name=project_name,
            description=project_description,
            target_url=target_url,
        ),
        features=features or [],
        pages=pages or [],
        flows=flows or [],
        api_contracts=api_contracts or [],
        business_rules=business_rules or [],
    )


def export_json_schema() -> dict:
    """Export the AATProductSpec as a JSON Schema for documentation."""
    return AATProductSpec.model_json_schema()
