# AIPM Agent — 生产部署指南

## 架构

```
[浏览器] → nginx (:80, 前端静态 + 反向代理)
              ├── /           → Vue SPA (dist)
              ├── /api/*      → backend:8000
              └── /ws/*       → backend:8000 (WebSocket)
[backend] → FastAPI (uvicorn, 2 workers) → 数据库
```

前端和后端**同源**（都经 nginx :80），因此 `VITE_API_URL=""`（相对路径），
无跨域问题，WebSocket 走 `/ws/` 代理。

## 上线前检查清单

### 1. 环境配置（必须）

复制并填写生产环境变量：

```bash
cp backend/.env.example backend/.env.prod
```

`backend/.env.prod` 必填项：

| 变量 | 说明 |
|------|------|
| `JWT_SECRET` | **强随机串**。生成：`python3 -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `OPENAI_API_KEY` | 真实 LLM key |
| `OPENAI_BASE_URL` | LLM 服务地址 |
| `DATABASE_URL` | 生产建议 PostgreSQL：`postgresql+asyncpg://user:pass@host:5432/aipm` |
| `CORS_ORIGINS` | 你的域名，**不能含 localhost**，如 `https://app.yourdomain.com` |
| `APP_ENV` | `production`（compose 已强制） |
| `DEBUG` | `false`（compose 已强制） |

> 后端启动时会运行 `validate_production()`，配置不安全会**直接拒绝启动**（fail-fast）。

### 2. 启动

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

访问 `http://<服务器IP>/`。

### 3. HTTPS（强烈建议）

生产必须上 HTTPS，否则 JWT token 在传输中可被窃取。两种方式：

- **反代层加 TLS**：在 nginx 前再挂一层 Caddy / Traefik / 云负载均衡，自动签发证书
- **直接改 nginx.conf**：加 443 server 块 + Let's Encrypt 证书

## 已落实的生产加固

| 项 | 状态 |
|----|------|
| JWT 密钥强随机 + 启动校验 | ✅ fail-fast |
| 密码 bcrypt 哈希 | ✅ |
| 登录限流 5 次/5 分钟/IP+邮箱 | ✅ |
| 注册限流 3 次/小时/IP | ✅ |
| 生产关闭 DEBUG / SQL echo | ✅ |
| 生产关闭 API docs (/docs) | ✅ |
| CORS 严格白名单 | ✅ |
| 后端非 root 用户运行 | ✅ |
| 后端不暴露到宿主机（仅经 nginx） | ✅ |
| 安全响应头（X-Frame-Options 等） | ✅ nginx |
| 项目所有权隔离（API + WS） | ✅ |

## 已知限制 / 后续

- **限流是单实例内存态**：多实例部署需换 Redis 后端限流
- **SQLite → PostgreSQL**：多 worker/多实例并发写建议用 PG
- **协作体系（L3）**：项目共享、成员权限尚未实现
- **L2 可选完善**：邮箱验证、密码找回、第三方登录
- **数据库迁移**：当前用 `create_all`；表结构变更建议引入 Alembic
