# AIPM Agent — 行进追踪

> 任何方向性决策必须实时写入此文件，不等会话结束。

## 决策日志

| 日期 | 决策 | 详情 |
|------|------|------|
| 2026-07-02 | 项目立项 | AIPM Agent = 独立项目，与 AAT 通过 JSON Schema 内在互识，代码库独立 |
| 2026-07-02 | 优先级调整 | AIPM Agent 设为优先项目，MVP 完成后联合 AAT 做双边测试 |
| 2026-07-02 | 项目骨架 | 后端 FastAPI + 前端 Vue 3 全栈可运行 |
| 2026-07-02 | 追问引擎 LLM 升级 | 轮数启发式 → SlotEvaluator（每 2 轮评估 8 维度） |
| 2026-07-02 | AIPM-AAT Schema v0.1.0 | 5 领域映射（Feature/Page/Flow/API/Rule）+ 导出 |
| 2026-07-02 | 原型验证器 | 4 类检查，评分 0-100，auto-fix |
| 2026-07-02 | 6 阶段全管线完成 | ① 想法捕获 → ② 产品思路 → ③ 产品结构 → ④ 原型 → ⑤ PRD → ⑥ 交付 |
| 2026-07-02 | AIPM-AAT 集成 | 5-pass LLM 从 pipeline 提取 AATProductSpec（Features 5×15criteria, Flows 3×17steps, API 29, Rules 6），存入 34KB JSON。AAT API 端点 `/api/aat/spec/{id}` 可用 |
| 2026-07-02 | 技术栈 | 前端 Vue 3 + Element Plus + Vite / 后端 FastAPI + LangChain + SQLAlchemy |
| 2026-07-02 | 部署 | Docker Compose 一键启动，前端 Vercel + 后端 Railway |
| 2026-07-05 | 追问引擎 V2 | 3步首次对话 + 置信度评分 + breadcrumb 追踪 + 卡住自动跳过；stage_ready 需均值置信度≥0.7 |
| 2026-07-05 | 需求卡片落盘 | 每条 WS 消息后写 requirement_slots 表，刷新不丢 |
| 2026-07-05 | 首页想法种子 | 创建项目时的初步想法作为第一条用户消息入库 + AI 引用回应 |
| 2026-07-07 | 用户体系立项 | 先做完整单用户体系（L1+L2）：User 表 + JWT + 密码哈希 + 项目归属。协作体系（L3）后续按需补 |

## MVP 完成 ✓

6 阶段全管线：① 追问引擎（WebSocket）→ ② 产品思路（auto）→ ③ 产品结构（auto）→ ④ 原型生成 + 校验 → ⑤ PRD 文档 → ⑥ Epic/Story/Sprint 交付

## 下一阶段

### 🔐 用户体系（进行中 2026-07-07）

**范围：**完整单用户体系，协作留后续。

后端：
- [ ] `User` 模型（id/email/username/hashed_password/created_at）
- [ ] 密码哈希（passlib bcrypt）+ JWT（python-jose）
- [ ] auth 端点：注册/登录/获取当前用户
- [ ] `Project.owner_id` 外键 + 所有 project API 按 owner 过滤
- [ ] WebSocket token 鉴权 + 项目归属校验
- [ ] 现有数据迁移（存量 project 归属默认用户或清空）

前端：
- [ ] 登录/注册页
- [ ] token 存储（localStorage）+ 请求拦截器注入 Authorization
- [ ] 路由守卫（未登录跳登录）
- [ ] 顶部显示用户 + 登出
- [ ] WS 连接带 token

**技术选型：** JWT（无状态，适合前后端分离 + Railway 部署），bcrypt 密码哈希，token 存 localStorage。

### 旧待办

- [x] AIPM 端 AAT Spec 生成 ✅ 2026-07-02
- [x] AAT 端消费 CLI ✅ 2026-07-02（`aat aipm` 命令，38 tests from 56KB spec）
- [x] 追问引擎体验优化 ✅ 2026-07-02（6轮→2轮，3x 提速）
- [x] WebSocket 全链路验证 ✅ 2026-07-02（2轮→requirement_card→auto ②③）
- [ ] `aat aipm --url http://aipm:8000 --pid xxx` 实时拉取测试（太慢，5-pass LLM ~200s，留待优化）
- [ ] 前端浏览器端实际验证（browser tool policy blocked）
- [ ] Docker build 验证（Docker 未安装在 Mac mini）

## 风险

1. 追问引擎做成聊天机器人而非专业引导工具
2. LLM 原型生成质量问题
3. 范围蔓延（守住「想法→PRD」线）

---

*关联文件：README.md（项目总览 + 详细设计）*
