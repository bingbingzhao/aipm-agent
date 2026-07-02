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

## MVP 完成 ✓

6 阶段全管线：① 追问引擎（WebSocket）→ ② 产品思路（auto）→ ③ 产品结构（auto）→ ④ 原型生成 + 校验 → ⑤ PRD 文档 → ⑥ Epic/Story/Sprint 交付

## 下一阶段

- [x] AIPM 端 AAT Spec 生成 ✅ 2026-07-02
- [x] AAT 端消费 CLI ✅ 2026-07-02（`aat aipm` 命令，38 tests from 56KB spec）
- [ ] `aat aipm --url http://aipm:8000 --pid xxx` 实时拉取测试
- [ ] 前端 WebSocket 实际对接验证
- [ ] 本地部署全栈跑通

## 风险

1. 追问引擎做成聊天机器人而非专业引导工具
2. LLM 原型生成质量问题
3. 范围蔓延（守住「想法→PRD」线）

---

*关联文件：README.md（项目总览 + 详细设计）*
