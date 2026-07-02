"""AIPM-AAT JSON Schema — 双边互识数据格式.

AIPM Agent 输出的产品定义 → AAT 消费生成自动化测试。

与 AAT 现有 types 的映射关系（见 aat/packages/shared/src/index.ts）：
- Feature.criteria[]        → TestCase (name + steps)
- PageSpec                   → PageState (url + title + elements)
- UserFlow.steps[]           → TestStep[] (navigation sequence)
- ApiContract                → ApiEndpoint (method + path + parameters)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ═══════════════════════════════════════════════
# Versioning
# ═══════════════════════════════════════════════

SCHEMA_VERSION = "0.1.0"


# ═══════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════

class FeaturePriority(str, Enum):
    P0 = "p0"  # Must have
    P1 = "p1"  # Should have
    P2 = "p2"  # Nice to have
    P3 = "p3"  # Future


class CriteriaType(str, Enum):
    """Acceptance criteria type, maps to AAT test categories."""
    FUNCTIONAL = "functional"   # → AAT: happy-path
    EDGE_CASE = "edge_case"     # → AAT: boundary
    ERROR = "error"             # → AAT: error
    UI = "ui"                   # → AAT: assertion type=visible
    INTEGRATION = "integration" # → AAT: integration chain


class StepAction(str, Enum):
    """User flow step action, maps to AAT TestStep.action."""
    NAVIGATE = "navigate"
    CLICK = "click"
    FILL = "fill"
    SELECT = "select"
    WAIT = "wait"
    ASSERT = "assert"


class AssertionType(str, Enum):
    """Assertion type, maps to AAT Assertion.type."""
    VISIBLE = "visible"
    TEXT = "text"
    URL = "url"
    VALUE = "value"


# ═══════════════════════════════════════════════
# Core Schemas
# ═══════════════════════════════════════════════

class AcceptanceCriteria(BaseModel):
    """单个验收标准。AAT 将每条变为一个 TestCase + TestStep。

    示例：
    {
        "description": "用户输入邮箱和密码后点击登录",
        "criteria_type": "functional",
        "given": "用户在登录页",
        "when": "输入正确的邮箱 test@example.com 和密码",
        "then": "跳转到首页，看到用户名",
        "priority": "p0",
        "tags": ["login", "auth"]
    }
    """
    description: str = Field(..., description="验收标准描述，作为 AAT TestCase.name")
    criteria_type: CriteriaType = Field(
        default=CriteriaType.FUNCTIONAL,
        description="类型，映射到 AAT TestCase.category"
    )
    given: str = Field(default="", description="前置条件")
    when: str = Field(default="", description="操作步骤")
    then: str = Field(default="", description="预期结果")
    priority: FeaturePriority = Field(default=FeaturePriority.P1)
    tags: list[str] = Field(default_factory=list)


class Feature(BaseModel):
    """产品功能定义。AAT 映射为 TestSuite。

    示例：
    {
        "id": "feat-001",
        "name": "用户登录",
        "description": "用户通过邮箱和密码登录系统",
        "criteria": [...],
        "depends_on": ["feat-auth-infra"],
        "priority": "p0"
    }
    """
    id: str = Field(..., description="功能唯一标识")
    name: str = Field(..., description="功能名称")
    description: str = Field(default="", description="功能描述")
    criteria: list[AcceptanceCriteria] = Field(
        default_factory=list,
        description="验收标准列表 → AAT TestCase[]"
    )
    depends_on: list[str] = Field(
        default_factory=list,
        description="前置依赖的功能 ID 列表"
    )
    priority: FeaturePriority = Field(default=FeaturePriority.P1)
    tags: list[str] = Field(default_factory=list)


class PageElement(BaseModel):
    """页面元素定义。AAT 映射为 PageElement（字段完全兼容）。

    AAT 的 PageElement 已有字段：selector, tag, text, type,
    role, href, inputType, placeholder, ariaLabel, id, name, className
    """
    selector: str = Field(default="", description="CSS 选择器")
    tag: str = Field(default="div", description="HTML 标签")
    element_type: str = Field(
        default="",
        alias="type",
        description="元素类型: button|link|input|select|textarea"
    )
    text: str = Field(default="", description="可见文本")
    role: Optional[str] = Field(default=None, description="ARIA role")
    placeholder: Optional[str] = Field(default=None, description="placeholder 属性")
    aria_label: Optional[str] = Field(default=None, alias="ariaLabel")
    input_type: str = Field(default="", alias="inputType", description="input type 属性")

    model_config = {"populate_by_name": True}


class PageSpec(BaseModel):
    """页面/组件规格定义。AAT 映射为 PageState。

    示例：
    {
        "route": "/login",
        "title": "登录页",
        "elements": [
            {"tag": "input", "type": "input", "inputType": "email",
             "placeholder": "请输入邮箱", "role": "textbox"},
            {"tag": "input", "type": "input", "inputType": "password",
             "placeholder": "请输入密码", "role": "textbox"},
            {"tag": "button", "type": "button", "text": "登录", "role": "button"}
        ],
        "states": ["default", "error", "loading"]
    }
    """
    route: str = Field(..., description="页面路由/URL pattern")
    title: str = Field(default="", description="页面标题")
    description: str = Field(default="", description="页面功能说明")
    elements: list[PageElement] = Field(
        default_factory=list,
        description="页面交互元素列表 → AAT PageState.elements"
    )
    states: list[str] = Field(
        default_factory=list,
        description="页面状态列表 (default/error/loading/empty)"
    )


class FlowStep(BaseModel):
    """用户流程步骤。AAT 映射为 TestStep。

    示例：
    {
        "action": "fill",
        "target": "[placeholder='请输入邮箱']",
        "value": "test@example.com",
        "description": "输入邮箱"
    }
    """
    action: StepAction = Field(..., description="操作类型")
    target: str = Field(default="", description="目标选择器/URL")
    value: str = Field(default="", description="填充值或预期值")
    description: str = Field(default="", description="步骤说明")
    assertion: Optional[AssertionSpec] = Field(
        default=None,
        description="断言（仅 action=assert 时有效）"
    )
    fallback_selectors: list[str] = Field(
        default_factory=list,
        alias="fallbackSelectors",
        description="备选选择器 → AAT TestStep.fallbackSelectors"
    )

    model_config = {"populate_by_name": True}


class AssertionSpec(BaseModel):
    """断言规格。AAT 映射为 Assertion。"""
    assertion_type: AssertionType = Field(..., alias="type")
    expected: str = Field(..., description="期望值")
    selector: str = Field(default="", description="断言目标选择器")

    model_config = {"populate_by_name": True}


class UserFlow(BaseModel):
    """用户流程定义。AAT 映射为 TestSuite 中的导航测试序列。

    示例：
    {
        "id": "flow-001",
        "name": "用户登录流程",
        "description": "从首页进入登录，输入凭据，登录成功",
        "steps": [
            {"action": "navigate", "target": "/", "description": "打开首页"},
            {"action": "click", "target": "text=登录", "description": "点击登录按钮"},
            {"action": "fill", "target": "[placeholder='邮箱']", "value": "test@example.com"},
            {"action": "fill", "target": "[placeholder='密码']", "value": "123456"},
            {"action": "click", "target": "text=登录", "description": "提交登录"},
            {"action": "assert", "assertion": {"type": "url", "expected": "/dashboard"}}
        ]
    }
    """
    id: str = Field(..., description="流程唯一标识")
    name: str = Field(..., description="流程名称")
    description: str = Field(default="", description="流程描述")
    steps: list[FlowStep] = Field(
        default_factory=list,
        description="步骤列表 → AAT TestStep[]"
    )
    start_page: str = Field(default="/", description="起始页面")
    feature_id: str = Field(default="", description="关联的功能 ID")


class ApiField(BaseModel):
    """API 参数字段。"""
    name: str = Field(..., description="字段名")
    field_type: str = Field(default="string", alias="type", description="字段类型")
    required: bool = Field(default=False)
    description: str = Field(default="")
    example: Optional[str] = Field(default=None)
    enum_values: list[str] = Field(default_factory=list)

    @field_validator("example", mode="before")
    @classmethod
    def coerce_example(cls, v):
        if v is None:
            return None
        return str(v)

    model_config = {"populate_by_name": True}


class ApiContract(BaseModel):
    """API 契约定义。AAT 直接映射为 ApiEndpoint。

    示例：
    {
        "method": "POST",
        "path": "/api/auth/login",
        "summary": "用户登录",
        "request_body": {
            "fields": [
                {"name": "email", "type": "string", "required": true, "example": "test@example.com"},
                {"name": "password", "type": "string", "required": true}
            ]
        },
        "responses": {
            "200": {"description": "登录成功，返回 token"},
            "401": {"description": "认证失败"}
        }
    }
    """
    method: str = Field(..., description="HTTP method")
    path: str = Field(..., description="API path")
    summary: str = Field(default="", description="简述 → AAT ApiEndpoint.summary")
    description: str = Field(default="", description="详细描述")
    query_params: list[ApiField] = Field(
        default_factory=list, alias="queryParams"
    )
    path_params: list[ApiField] = Field(
        default_factory=list, alias="pathParams"
    )
    request_body: Optional[RequestBody] = Field(
        default=None, alias="requestBody"
    )
    responses: dict[str, ResponseSpec] = Field(default_factory=dict)
    auth_required: bool = Field(default=False)
    tags: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class RequestBody(BaseModel):
    """请求体定义。"""
    content_type: str = Field(default="application/json", alias="contentType")
    fields: list[ApiField] = Field(default_factory=list)
    example: Optional[dict] = Field(default=None)

    model_config = {"populate_by_name": True}


class ResponseSpec(BaseModel):
    """API 响应规格。"""
    description: str = Field(default="")
    body_example: Optional[dict] = Field(default=None, alias="bodyExample")

    model_config = {"populate_by_name": True}


class BusinessRule(BaseModel):
    """业务规则定义。AAT 可以用于生成边界测试和验证规则。

    示例：
    {
        "id": "rule-001",
        "name": "密码长度限制",
        "description": "密码必须 8-64 字符",
        "rule_type": "validation",
        "condition": "password.length < 8",
        "expected_behavior": "显示错误提示'密码至少8位'"
    }
    """
    id: str = Field(..., description="规则唯一标识")
    name: str = Field(..., description="规则名称")
    description: str = Field(default="", description="规则描述")
    rule_type: str = Field(
        default="validation",
        description="类型: validation|authorization|rate_limit|data_integrity"
    )
    condition: str = Field(default="", description="触发条件")
    expected_behavior: str = Field(default="", description="预期行为")
    related_features: list[str] = Field(
        default_factory=list,
        description="关联的功能 ID 列表"
    )


# ═══════════════════════════════════════════════
# Top-level Container
# ═══════════════════════════════════════════════

class AATProductSpec(BaseModel):
    """AAT 产品规格 — AIPM Agent 输出的顶层容器。

    这是 AAT 消费的统一入口。AAT 读取此 JSON 后：
    1. features → TestSuite[TestCase]  (功能测试)
    2. pages → PageState[]              (UI 元素探索已由 AIPM 预定义)
    3. flows → TestStep[]              (用户旅程测试)
    4. api_contracts → ApiEndpoint[]    (API 测试)
    5. business_rules → boundary/validation tests
    """
    schema_version: str = Field(
        default=SCHEMA_VERSION,
        description="Schema 版本"
    )
    project: ProjectMeta = Field(..., description="项目元数据")
    features: list[Feature] = Field(
        default_factory=list,
        description="功能定义 → AAT TestSuite"
    )
    pages: list[PageSpec] = Field(
        default_factory=list,
        description="页面/组件定义 → AAT PageState"
    )
    flows: list[UserFlow] = Field(
        default_factory=list,
        description="用户流程 → AAT navigation TestSteps"
    )
    api_contracts: list[ApiContract] = Field(
        default_factory=list,
        alias="apiContracts",
        description="API 契约 → AAT ApiEndpoint"
    )
    business_rules: list[BusinessRule] = Field(
        default_factory=list,
        alias="businessRules",
        description="业务规则 → AAT validation/boundary tests"
    )
    generated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="生成时间 ISO 8601"
    )

    model_config = {"populate_by_name": True}

    def estimate_test_count(self) -> int:
        """估算 AAT 会生成多少测试用例。"""
        count = 0
        # Each acceptance criteria = ~1 test case
        for feat in self.features:
            count += len(feat.criteria)
        # Each user flow = ~1-3 test cases (flow itself + error + edge)
        count += len(self.flows) * 2
        # Each API contract = ~3-5 test cases (happy + boundary + error)
        count += len(self.api_contracts) * 3
        # Each business rule = ~1-2 test cases
        count += len(self.business_rules) * 2
        return count


class ProjectMeta(BaseModel):
    """项目元数据。"""
    id: str = Field(..., description="AIPM project ID")
    name: str = Field(..., description="产品名称")
    description: str = Field(default="", description="产品简述")
    target_url: str = Field(
        default="",
        description="目标 URL → AAT ExploreConfig.url"
    )
    auth_required: bool = Field(default=False, description="是否需要认证")
    auth_config: Optional[AuthConfig] = Field(
        default=None,
        alias="authConfig",
        description="认证配置"
    )
    stage: str = Field(default="prototype", description="当前管线阶段")

    model_config = {"populate_by_name": True}


class AuthConfig(BaseModel):
    """认证配置 → AAT ExploreConfig.cookies / loginSteps。"""
    cookies: Optional[str] = Field(default=None, description="Cookie 字符串 key=val; key2=val2")
    login_url: Optional[str] = Field(default=None, alias="loginUrl")
    login_steps: list[dict] = Field(
        default_factory=list,
        alias="loginSteps",
        description="登录步骤: {action: fill|click, target: selector, value: text}"
    )

    model_config = {"populate_by_name": True}
