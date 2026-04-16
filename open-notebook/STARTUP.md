# Open Notebook 启动指南

这份文档基于当前重构后的项目结构整理，适用于现在的一体化 `Open Notebook + Visual RAG`。

项目运行时由这几部分组成：
- `SeekDB`：主数据库与检索存储
- `Redis`：异步任务队列
- `FastAPI`：后端 API
- `Worker`：异步任务处理器
- `Next.js`：前端界面

## 推荐启动方式

在项目根目录执行：

```bash
cp .env.seekdb.example .env.seekdb
make seekdb-dev-up
```

启动完成后访问：
- 前端：`http://localhost:3000`
- API 文档：`http://localhost:5055/docs`
- 健康检查：`http://localhost:5055/health`

`make seekdb-dev-up` 会自动完成这些事情：
- 启动 `SeekDB` 和 `Redis` 容器
- 等待 `SeekDB` 就绪
- 启动 `FastAPI` 后端
- 启动 `Worker`
- 启动 `Next.js` 前端

## 手动分步启动

如果你想分别控制每个进程，可以按下面方式启动。

### 1. 准备环境变量

```bash
cp .env.seekdb.example .env.seekdb
```

### 2. 启动 SeekDB 和 Redis

```bash
make database-seekdb
```

等价命令：

```bash
docker compose -f docker-compose.dev.yml -f docker-compose.seekdb.yml up -d seekdb redis
```

### 3. 启动 API

```bash
uv run --env-file .env.seekdb run_api.py
```

也可以使用：

```bash
make api
```

默认地址：
- API：`http://127.0.0.1:5055`
- Docs：`http://127.0.0.1:5055/docs`

### 4. 启动 Worker

另开一个终端：

```bash
OPEN_NOTEBOOK_JOB_BACKEND=arq uv run --env-file .env.seekdb open-notebook-worker
```

也可以用：

```bash
make worker
```

### 5. 启动前端

另开一个终端：

```bash
cd frontend
npm run dev
```

前端默认地址：
- `http://localhost:3000`

## 常用管理命令

| 命令 | 说明 |
|------|------|
| `make seekdb-dev-up` | 启动整套开发环境 |
| `make seekdb-dev-stop` | 停止整套开发环境 |
| `make seekdb-dev-status` | 查看开发环境状态 |
| `make seekdb-dev-logs` | 查看 API / Worker / Frontend 日志 |
| `make database-seekdb` | 只启动 SeekDB 和 Redis |
| `make api` | 只启动 API |
| `make worker` | 只启动 Worker |

## Worker 负责什么

`Worker` 不只是“可选项”，很多功能都依赖它：
- source 异步处理
- 文本向量化
- insight 创建
- podcast 生成
- Visual RAG 图像索引 / 重建

如果 `Worker` 没有运行，你会看到这些任务一直停留在“排队中”。

检查状态：

```bash
make seekdb-dev-status
```

或：

```bash
pgrep -f "open-notebook-worker"
```

## Visual RAG 的当前入口

重构后，Visual RAG 已经是 notebook 内部功能页。

主要入口：
- `http://localhost:3000/notebooks/<notebook-id>/visual`

兼容入口：
- `http://localhost:3000/vrag`

说明：
- `/vrag` 现在只是兼容页面，会跳转或先让你选择 notebook
- 不再推荐使用旧的 `/vrag?id=...` 作为主入口

## Visual RAG 的当前 API

当前 canonical API 为：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/visual-rag/search` | `POST` | 统一视觉检索 |
| `/api/visual-rag/chat/stream` | `POST` | 视觉问答流式对话 |
| `/api/visual-rag/index` | `POST` | 提交视觉索引任务 |
| `/api/visual-rag/reindex` | `POST` | 重建某个 source 的视觉索引 |
| `/api/visual-rag/sessions` | `GET` | 列出视觉会话 |
| `/api/visual-rag/sessions/{session_id}` | `GET` | 读取会话详情 |
| `/api/visual-rag/sessions/{session_id}/graph` | `GET` | 读取推理图 |
| `/api/visual-rag/sessions/{session_id}` | `DELETE` | 删除会话 |
| `/api/visual-assets/{asset_id}/file` | `GET` | 安全读取视觉图片资产 |

兼容别名仍然保留：
- `/api/vrag/*`

但新接入、脚本和文档都应该优先使用：
- `/api/visual-rag/*`

## Visual RAG 使用示例

### 提交视觉索引任务

```bash
curl -X POST http://localhost:5055/api/visual-rag/index \
  -H "Content-Type: application/json" \
  -d '{
    "source_id": "your-source-id",
    "generate_summaries": true,
    "dpi": 150
  }'
```

返回示例：

```json
{
  "source_id": "your-source-id",
  "command_id": "command:xxxx",
  "status": "queued"
}
```

### 发起视觉问答

```bash
curl -X POST http://localhost:5055/api/visual-rag/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "question": "第 3 页的图表说明了什么？",
    "notebook_id": "your-notebook-id",
    "source_ids": ["your-source-id"],
    "max_steps": 10,
    "stream": true
  }' \
  -N
```

### 直接做视觉检索

```bash
curl -X POST http://localhost:5055/api/visual-rag/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "revenue chart",
    "source_ids": ["your-source-id"],
    "image_top_k": 5,
    "text_top_k": 5
  }'
```

## 认证说明

如果你设置了 `OPEN_NOTEBOOK_PASSWORD`，请求 API 时需要带上：

```http
Authorization: Bearer your-password
```

开发环境如果未设置密码，部分接口可以直接访问。

## 关键环境变量

常用变量见 `.env.seekdb.example`，这里列最关键的几项：

| 变量名 | 说明 |
|--------|------|
| `OPEN_NOTEBOOK_SEEKDB_DSN` | SeekDB 连接串 |
| `OPEN_NOTEBOOK_AI_CONFIG_BACKEND` | AI 配置后端，默认 `seekdb` |
| `OPEN_NOTEBOOK_SEARCH_BACKEND` | 搜索后端，默认 `seekdb` |
| `OPEN_NOTEBOOK_JOB_BACKEND` | 异步任务后端，默认 `arq` |
| `OPEN_NOTEBOOK_REDIS_URL` | Redis 地址 |
| `OPEN_NOTEBOOK_PASSWORD` | API 密码 |
| `OPEN_NOTEBOOK_ENCRYPTION_KEY` | 凭证加密密钥 |

## 当前目录结构说明

这次重构后，和 Visual RAG 相关的目录应该这样理解：
- `open_notebook/visual_rag/`：当前运行中的 canonical Visual RAG HTTP/API 与检索索引模块
- `open_notebook/storage/`：视觉资产、视觉会话、迁移逻辑
- `open_notebook/vrag/`：仍保留的共享 agent / workflow / search / tools 逻辑
- `references/vrag-original/`：原始 VRAG 参考代码，仅供查阅，不参与主应用运行

## 常见问题

### 1. `SeekDB` 连不上

```bash
docker ps | grep -E "seekdb|redis"
docker compose -f docker-compose.dev.yml -f docker-compose.seekdb.yml logs seekdb
```

如果还不行，重启：

```bash
make seekdb-dev-stop
make seekdb-dev-up
```

### 2. 任务一直排队不执行

大概率是 `Worker` 没启动。

启动它：

```bash
make worker
```

### 3. 前端打不开

检查 3000 端口：

```bash
lsof -i :3000
```

前端日志：

```bash
tail -f .logs/seekdb-dev/frontend.log
```

### 4. API 打不开

检查 5055 端口：

```bash
lsof -i :5055
```

API 日志：

```bash
tail -f .logs/seekdb-dev/api.log
```

### 5. Visual RAG 没结果

按这个顺序检查：
- source 是否已经处理完成
- source 是否是 PDF
- worker 是否正在运行
- 该 source 是否已经提交过 visual index
- 模型配置里是否至少有可用 chat / vision / embedding 配置

## 推荐的开发调试顺序

平时最省事的流程是：

```bash
cp .env.seekdb.example .env.seekdb
make seekdb-dev-up
make seekdb-dev-status
```

然后在浏览器里完成：
1. 创建 notebook
2. 上传 PDF source
3. 等 source 处理完成
4. 打开 `/notebooks/<id>/visual`
5. 提交视觉索引
6. 开始视觉问答
