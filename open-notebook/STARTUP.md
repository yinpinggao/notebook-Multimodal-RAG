# Open Notebook 启动指南

本文档说明如何启动 Open Notebook 项目。项目使用 **SeekDB** 作为数据库，**Redis** 作为任务队列，**FastAPI** 作为后端 API，**Next.js** 作为前端界面。

## 快速启动（推荐）

使用 Makefile 一键启动所有服务：

```bash
# 1. 创建环境配置文件
cp .env.seekdb.example .env.seekdb

# 2. 一键启动所有服务（SeekDB + Redis + API + Worker + Frontend）
make seekdb-dev-up
```

这会自动：
- 启动 SeekDB 和 Redis Docker 容器
- 等待 SeekDB 就绪
- 启动 API 后端（端口 5055）
- 启动后台 Worker（异步任务）
- 启动 Next.js 前端（端口 3000）

启动完成后访问：
- **前端界面**: http://localhost:3000
- **API 文档**: http://localhost:5055/docs
- **API 健康检查**: http://localhost:5055/health

## 分步启动（手动控制）

如果需要更细粒度的控制，可以在不同终端中分别启动各服务：

### 步骤 1：准备环境配置文件

```bash
cp .env.seekdb.example .env.seekdb
```

### 步骤 2：启动数据库和队列

```bash
# 使用 Docker Compose 启动 SeekDB 和 Redis
make database-seekdb
# 或等效命令：docker compose -f docker-compose.dev.yml -f docker-compose.seekdb.yml up -d seekdb redis
```

等待 SeekDB 就绪（约 10-20 秒）。

### 步骤 3：启动 API 后端

```bash
make api
# 或等效命令：uv run --env-file .env.seekdb run_api.py
```

API 会在 http://127.0.0.1:5055 启动，支持热重载。

### 步骤 4：启动后台 Worker（异步任务）

```bash
# 在另一个终端中启动
OPEN_NOTEBOOK_JOB_BACKEND=arq uv run open-notebook-worker
```

Worker 处理异步任务：播客生成、内容向量化、洞察创建等。

### 步骤 5：启动前端

```bash
# 在另一个终端中启动
cd frontend && npm run dev
```

前端会在 http://localhost:3000 启动。

## 服务管理命令

| 命令 | 说明 |
|------|------|
| `make seekdb-dev-up` | 启动所有服务 |
| `make seekdb-dev-stop` | 停止所有服务 |
| `make seekdb-dev-status` | 查看各服务运行状态 |
| `make seekdb-dev-logs` | 实时查看所有服务日志 |
| `make status` | 查看所有服务状态 |

## 环境变量说明

关键环境变量（见 `.env.seekdb.example`）：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `OPEN_NOTEBOOK_SEEKDB_DSN` | `mysql://root:SeekDBRoot123!@seekdb:2881/open_notebook_ai` | SeekDB 连接字符串 |
| `OPEN_NOTEBOOK_AI_CONFIG_BACKEND` | `seekdb` | AI 配置存储后端 |
| `OPEN_NOTEBOOK_SEARCH_BACKEND` | `seekdb` | 搜索后端 |
| `OPEN_NOTEBOOK_JOB_BACKEND` | `arq` | 异步任务后端（使用 Redis） |
| `OPEN_NOTEBOOK_REDIS_URL` | `redis://redis:6379/0` | Redis 连接地址 |
| `OPEN_NOTEBOOK_ENCRYPTION_KEY` | `change-me-to-a-secret-string` | 凭证加密密钥（生产环境必须修改） |
| `OPEN_NOTEBOOK_PASSWORD` | `open-notebook-change-me` | API 访问密码 |

### 开发环境变量（可选覆盖）

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `API_HOST` | `127.0.0.1` | API 监听地址 |
| `API_PORT` | `5055` | API 监听端口 |
| `API_RELOAD` | `true` | 是否启用热重载 |

## Docker 方式启动（不推荐开发使用）

使用 Docker Compose 启动完整容器化版本：

```bash
# 启动所有容器（API + 前端）
make dev

# 或启动完整版本（包含更多配置）
make full
```

## 停止服务

```bash
# 停止所有服务（包括 Docker 容器）
make stop-all

# 或仅停止 SeekDB 开发栈
make seekdb-dev-stop
```

## 验证服务状态

```bash
# 查看所有服务状态
make status

# 检查 API 健康状态
curl http://localhost:5055/health

# 检查 API 配置
curl http://localhost:5055/api/config
```

## 常见问题

### SeekDB 连接失败

```bash
# 确认容器正在运行
docker ps | grep seekdb

# 查看 SeekDB 日志
docker compose logs seekdb

# 重新启动
make database-seekdb
```

### 端口被占用

```bash
# 查看端口占用
lsof -i :5055   # API
lsof -i :3000   # 前端
lsof -i :2881   # SeekDB
```

### API 报错 401 Unauthorized

确保请求头中包含密码认证：
```
Authorization: Bearer open-notebook-change-me
```

或修改 `.env.seekdb` 中的 `OPEN_NOTEBOOK_PASSWORD` 为你的密码。

### 播客生成无响应

确认后台 Worker 正在运行：
```bash
pgrep -f "open-notebook-worker"
```

如果未运行，重新启动：
```bash
OPEN_NOTEBOOK_JOB_BACKEND=arq uv run open-notebook-worker
```

### 迁移数据库

API 启动时会自动运行数据库迁移。如果需要手动触发：
```bash
uv run --env-file .env.seekdb python -c "
import asyncio
from open_notebook.database.async_migrate import AsyncMigrationManager
asyncio.run(AsyncMigrationManager().run_migration_up())
"
```

## 架构概览

```
┌─────────────────┐
│  Next.js 前端    │  :3000
│  (localhost)     │
└────────┬────────┘
         │ HTTP REST
         ▼
┌─────────────────┐
│  FastAPI 后端    │  :5055
│  (uvicorn)      │
├────────┬────────┤
│        │        │
│        ▼        ▼
│  ┌─────────┐  ┌─────────┐
│  │ SeekDB  │  │  Redis  │
│  │ (MySQL) │  │ (任务队) │
│  │  :2881  │  │  :6379  │
│  └─────────┘  └─────────┘
│  ┌─────────┐
│  │ Worker  │
│  │ (arq)   │
│  └─────────┘
```

- **SeekDB**: 数据持久化（Notebook、Source、Note、Credential 等）
- **Redis**: 异步任务队列（播客生成、向量化等）
- **Worker**: 后台任务处理器，轮询 Redis 队列
- **API**: 协调所有操作，提供 REST 接口

## VRAG 多模态检索与推理

Open Notebook 支持 **VRAG (Vision-perception RAG)** 功能，可以对 PDF/PPT 文档中的图像、图表、表格进行语义检索和视觉推理。

### 什么是 VRAG？

VRAG 是一个多模态 RAG 系统，能够：
- 从文档中提取图像并生成 CLIP 向量嵌入
- 通过自然语言检索相关图像和文本
- 使用 ReAct Agent 进行多轮视觉推理（搜索 → bbox 裁剪 → 总结 → 回答）
- 支持流式输出和 DAG 推理过程可视化

### 前提条件

使用 VRAG 前需要：
1. **OpenAI API Key**：用于 CLIP 嵌入和 GPT-4o 推理
2. **上传文档**：先将 PDF 文件作为 Source 上传到 notebook

### API 端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/vrag/chat/stream` | POST | VRAG 流式对话（SSE） |
| `/api/vrag/search` | POST | 直接多模态检索 |
| `/api/vrag/index` | POST | 触发 Source 图像索引 |
| `/api/vrag/bbox/crop` | POST | bbox 裁剪图像区域 |
| `/api/vrag/sessions` | GET | 列出 VRAG 会话 |
| `/api/vrag/sessions/{id}/graph` | GET | 获取 DAG 推理图状态 |
| `/api/vrag/reindex` | POST | 重建 Source 的图像索引 |

### 使用流程

> **认证说明**：API 默认开启密码认证（如果未设置 `OPEN_NOTEBOOK_PASSWORD` 则认证跳过，开发环境可直接访问）。生产环境需设置密码后，在请求头中附带认证：
> ```
> Authorization: Bearer your-password
> ```

**1. 索引文档图像**

```bash
curl -X POST http://localhost:5055/api/vrag/index \
  -H "Content-Type: application/json" \
  -d '{
    "source_id": "your-source-id",
    "source_path": "/path/to/document.pdf",
    "source_type": "pdf",
    "generate_summaries": true,
    "dpi": 150
  }'
```

**2. VRAG 对话（流式）**

```bash
curl -X POST http://localhost:5055/api/vrag/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "question": "图表中展示的增长趋势是什么?",
    "notebook_id": "your-notebook-id",
    "source_ids": ["your-source-id"],
    "max_steps": 10,
    "stream": true
  }' \
  -N
```

返回 SSE 事件流：
- `dag_update`：推理步骤更新（search/bbox_crop/summarize/answer）
- `complete`：最终答案
- `error`：错误信息

**3. 直接多模态检索（不经过 Agent）**

```bash
curl -X POST http://localhost:5055/api/vrag/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "revenue chart",
    "source_ids": ["your-source-id"],
    "image_top_k": 5,
    "text_top_k": 5
  }'
```

### VRAG Agent 工作原理

```
用户提问
    │
    ▼
┌─────────────────┐
│   Agent 决策     │  ← LLM 决定下一步 action
│  (search/bbox/  │
│   summarize/   │
│   answer)       │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
search    bbox_crop
    │         │
    ▼         ▼
返回图像   裁剪区域
    │         │
    └────┬────┘
         ▼
┌─────────────────┐
│  更新 Memory    │  ← DAG 记忆图累积视觉证据
│     Graph       │
└────────┬────────┘
         ▼
┌─────────────────┐
│  生成最终答案    │  ← 综合所有视觉证据
│  (带图像引用)   │
└─────────────────┘
```

### 环境变量

VRAG 使用以下环境变量（通过 `.env.seekdb` 配置）：

| 变量名 | 说明 |
|--------|------|
| `OPENAI_API_KEY` | OpenAI API Key（用于 CLIP 嵌入和 GPT-4o） |

如果没有设置，会使用 open-notebook 内部存储的 API Key（通过前端设置）。

### 相关文件

- `open_notebook/vrag/` — VRAG 核心模块
- `open_notebook/vrag/api.py` — FastAPI 路由
- `open_notebook/vrag/agent.py` — ReAct Agent
- `open_notebook/vrag/search_engine.py` — 多模态检索引擎
- `open_notebook/vrag/indexer.py` — PDF 图像索引器

## 更多资源

- [开发文档](docs/7-DEVELOPMENT/quick-start.md) — 开发环境详细配置
- [架构文档](docs/7-DEVELOPMENT/architecture.md) — 系统架构详解
- [配置指南](docs/5-CONFIGURATION/index.md) — 环境变量完整说明
- [故障排除](docs/6-TROUBLESHOOTING/index.md) — 常见问题解答
