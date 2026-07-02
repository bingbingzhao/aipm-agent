# AIPM-AAT JSON Schema v0.1.0

## 设计原则

**单向数据流**：AIPM Agent 输出 → AAT 消费。不双向依赖，不代码耦合。

## AIPM → AAT 映射表

| AIPM 领域对象 | → | AAT 类型 | 用途 |
|---------------|-----|----------|------|
| `Feature.criteria[]` | → | `TestCase[]` | 验收标准 → 功能测试用例 |
| `PageSpec` | → | `PageState` | 页面定义 → UI 元素探索基准 |
| `PageElement` | → | `PageElement` | 字段完全兼容 AAT shared types |
| `UserFlow.steps[]` | → | `TestStep[]` | 用户流程 → 导航测试序列 |
| `ApiContract` | → | `ApiEndpoint` | API 定义 → API 测试生成 |
| `BusinessRule` | → | boundary/error TestCase | 业务规则 → 边界/验证测试 |

## 示例流程

```
AIPM 生成 AATProductSpec JSON
        ↓
AAT 读取 features[] → 生成 TestSuite
AAT 读取 pages[] → 跳过 Explorer（已有元素定义）
AAT 读取 flows[] → 生成导航 TestSteps
AAT 读取 api_contracts[] → 启动 API 管线
AAT 读取 business_rules[] → 生成 validation tests
        ↓
AAT 执行全部测试 → TestReport
        ↓
回到 AIPM: 测试结果反馈 → PRD 迭代
```

## 字段兼容性

`PageElement` 字段与 AAT `packages/shared/src/index.ts` 中 `PageElement` 接口完全对齐：

```
selector     → selector    ✅
tag          → tag         ✅
type         → type        ✅
text         → text        ✅
role         → role        ✅
placeholder  → placeholder ✅
ariaLabel    → ariaLabel   ✅
inputType    → inputType   ✅
```

## 估算

一个典型的中型项目（5 个 Feature + 3 个 UserFlow + 2 个 ApiContract + 3 个 BusinessRule）：

- `estimate_test_count()` ≈ 5×3 + 3×2 + 2×3 + 3×2 = **33 个测试用例**

## 版本

- v0.1.0 — 初始版本，覆盖 Feature/Page/Flow/API/Rule 五大领域
