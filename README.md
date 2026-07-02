# AIPM Agent — AI 产品经理 Agent

> 从一句话想法到完整产品方案，6 阶段全流程 AI 辅助

## 快速开始

```bash
# 后端
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 填入 DEEPSEEK_API_KEY
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 前端
cd frontend
npm install
npm run dev
```

打开 <http://localhost:5173>

## 核心管线（6 阶段全实现 ✅）

```
① 想法捕获 → ② 产品思路 → ③ 产品结构 → ④ 原型 → ⑤ PRD → ⑥ 交付
```

| # | 阶段 | AI 核心能力 | 状态 |
|:--:|------|------|:--:|
| ① | 想法捕获 | 追问引擎：2 轮对话完成需求卡片，WebSocket 实时交互 | ✅ |
| ② | 产品思路 | 自动生成 3-5K 字分析报告（市场/用户/竞品/可行性） | ✅ |
| ③ | 产品结构 | 自动生成 JSON（功能模块 + 路由 + 数据实体） | ✅ |
| ④ | 原型 | 点击生成交互 HTML，自动质量校验（4 类检查，评分 0-100） | ✅ |
| ⑤ | PRD | 点击生成 9 章完整 PRD 文档 | ✅ |
| ⑥ | 交付 | Epic/Story 分解 + Sprint 规划 | ✅ |

## 追问引擎（核心壁垒）🆕

**2 轮对话完成需求卡片：**

```
用户："做个AI周报工具"
AI："给谁用？"
用户："程序员和PM"
AI："他们的痛点是什么？"
用户："每周写周报烦，AI自动生成省时间"
AI："现在怎么解决的？"
用户："Notion手动，竞品太贵"
→ ✅ 需求卡片完成 → 自动进入 ②③ 阶段
```

- 8 维度槽位系统，LLM 实时饱和度评估
- 条件槽位（技术约束/合规）自动饱和，无触发词即跳过
- 每轮评估，不再等待

## 与 AAT 集成

```
AIPM Pipeline ①②③④⑤⑥
    ↓ 5-pass LLM extraction
AATProductSpec (56KB JSON)
    ↓ GET /api/aat/spec/{project_id}
AAT CLI: aat aipm <spec.json>
    ↓
38 TestCases → 203-line Playwright script
```

**用法：**
```bash
# 从 AIPM API 拉取
aat aipm --url http://localhost:8000 --project-id <id>

# 从本地 JSON
aat aipm ../aipm-agent/samples/aat-spec-bot.json
```

## 技术栈

| 层 | 选型 |
|------|------|
| 后端 | Python 3.12+ / FastAPI / WebSocket / LangChain / SQLAlchemy |
| 前端 | Vue 3 / Element Plus / Pinia / TailwindCSS |
| 数据库 | SQLite（开发）/ PostgreSQL（生产） |
| AI | DeepSeek V4-Pro + LangChain |
| 数据校验 | Pydantic（同时定义 AAT JSON Schema） |

## 项目规模

- 60+ 文件 | ~3,000 行 Python | ~1,600 行 Vue/TS
- 8 个 API 端点 + WebSocket + 7 个 LLM 服务
- 6 阶段全管线端到端验证通过

## 部署

```bash
docker compose up
```

| 环境 | 前端 | 后端 | 数据库 |
|------|------|------|--------|
| 开发 | Vite Dev Server (5173) | FastAPI (8000) | SQLite |
| 线上 | Vercel | Railway | PostgreSQL |

## 路线图

- [x] MVP 6 阶段管线
- [x] AIPM-AAT 双边集成
- [x] 追问引擎 3x 提速
- [ ] 浏览器端 UI 完整验证
- [ ] Docker 一键部署验证
- [ ] AAT Spec 生成速度优化（200s → 30s）

---

*创建：2026-07-02 | 状态：MVP 完成，待生产化打磨*
