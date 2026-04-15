# CLAUDE.md

本文件为 Claude Code（claude.ai/code）在该代码库中工作时提供指导。

## 项目概述

Open Notebook 是一款开源的 AI 研究助手（Google Notebook LM 的替代品）。它采用 Next.js 作为前端、FastAPI 作为后端，SeekDB (MySQL) 作为数据库。AI 工作流由 LangGraph 提供支持，AI 供应商抽象由 Esperanto 库处理。

## 开发命令

```bash
# 安装依赖
uv sync

# 启动所有服务（SeekDB + Redis + API + 前端）
make start-all

# 使用 SeekDB 开发配置启动服务
make seekdb-dev-up

# 停止所有服务
make stop-all

# 检查服务状态
make status

# 查看所有服务的日志
make seekdb-dev-logs

# Python 代码检查（自动修复）
make ruff

# Python 类型检查
make lint

# 运行 Python 测试
uv run pytest

# 运行单个测试文件
uv run pytest tests/test_domain.py

# 运行测试并生成覆盖率报告
uv run pytest --cov=open_notebook

# 运行前端（在 frontend/ 目录）
cd frontend && npm run dev

# 运行 API 服务器
make api
# 或：uv run --env-file .env run_api.py

# 启动后台 worker（播客、异步任务）
OPEN_NOTEBOOK_JOB_BACKEND=arq uv run open-notebook-worker

# 代码格式化（Python）
ruff check . --fix
ruff format .
```

## 高层架构

项目采用三层架构。以下文件组合阅读可以了解全貌：

| 文件 | 独特价值 |
|---|---|
| `docs/7-DEVELOPMENT/architecture.md` | 三层架构、LangGraph 工作流、AI 供应商集成、设计模式 |
| `open_notebook/graphs/CLAUDE.md` | LangGraph 状态机设计、节点函数、检查点机制 |
| `open_notebook/ai/CLAUDE.md` | ModelManager 工厂、Esperanto 库用法、多供应商回退逻辑 |
| `open_notebook/database/CLAUDE.md` | SeekDB 业务存储层、数据仓库、迁移系统 |
| `open_notebook/domain/CLAUDE.md` | 领域模型（Notebook、Source、Note、ChatSession）、仓库模式 |
| `open_notebook/podcasts/CLAUDE.md` | 播客生成工作流、说话人分配 |
| `api/CLAUDE.md` | FastAPI 路由组织、服务模式、端点开发 |
| `frontend/src/CLAUDE.md` | React/Next.js 模式、Zustand + TanStack Query 状态、API 集成层 |

根目录的 `CLAUDE.md` 链接了以上所有文件 — 进行改动前务必先查阅相关文件。

### 五个 LangGraph 工作流

理解以下五个工作流对大多数后端开发工作至关重要：

1. **source.py** — 内容摄取（PDF、URL、文本）：提取 → 分块 → 向量嵌入 → 保存到 SeekDB
2. **chat.py** — 多轮对话，包含消息历史、上下文构建、流式响应
3. **ask.py** — 搜索 + 合成：LLM 规划搜索 → 向量/文本搜索 → LLM 合成答案，流式返回结果
4. **transformation.py** — 应用自定义 Jinja2 提示规则到数据源，生成 SourceInsight 记录
5. **prompt.py** — 通用一次性 LLM 任务（例如自动生成笔记标题）

以上五个工作流都使用 `provision_langchain_model()` 进行智能供应商选择。

### AI 供应商系统

- **Esperanto** 库提供统一接口，支持 8+ 供应商（OpenAI、Anthropic、Google、Groq、Ollama、Mistral、DeepSeek、xAI）
- **凭证**：每个供应商有独立的加密凭证记录，通过设置界面配置（不再是环境变量存储 API 密钥）
- **ModelManager**：工厂类，检测可用供应商、根据上下文大小选择最佳模型、失败时回退到更便宜/更小的模型
- 支持通过 `config={"configurable": {"model_override": "anthropic/claude-opus-4"}}` 进行单次请求覆盖

### 数据库：SeekDB (MySQL)

- 图数据库，内置向量嵌入 — 无需单独的向量数据库
- 模式迁移通过 AsyncMigrationManager 在 API 启动时自动运行
- 迁移文件位于 `/migrations/` 目录，为编号的 Python 文件（如 N_up.py、N_down.py...）
- 记录 ID 使用 SeekDB 语法：`table:id`（例如 `notebook:abc123`）
- `ensure_record_id()` 辅助函数防止格式错误的 ID

## 关键约定

- **Python**：Ruff 代码检查（88 字符行宽）、Google 风格文档字符串、全程使用 async/await — 请求处理器中无同步 I/O
- **TypeScript**：严格模式、函数式组件 + Hooks，非必要不使用 `any`
- **前端国际化**：所有用户可见文本必须使用翻译键 — 禁止硬编码字符串
- **LangGraph 状态持久化**：检查点通过 SqliteSaver 存储在 `/data/sqlite-db/`；会话 ID 必须唯一避免冲突
- **API 端点模式**：路由 → 服务（编排） → 领域/仓库 → SeekDB。服务调用 LangGraph 图。路由仅处理 HTTP 和验证。
- **后台任务**：异步任务（播客生成、数据源处理）通过 seekdb-Commands 任务队列提交，通过 `/commands/{id}` 轮询状态
- **Mypy**：Streamlit 页面（`pages/*.py`、`app_home.py`）通过 `pyproject.toml` 排除在类型检查之外

## 重要注意事项

- **每次 API 启动都会运行迁移** — 检查日志中的错误；失败的迁移会阻止启动
- **前端 API URL**：在 `.env.local` 中配置（默认：`http://localhost:5055`）。远程访问时需设置 `API_URL=http://你的服务器IP:5055`
- **聊天/搜索工作流可能需要数分钟** — 无内置超时。为优化用户体验，使用流式传输（SSE）让用户看到进度
- **凭证系统**：AI 供应商的 API 密钥以加密记录形式存储在数据库中，而非环境变量。通过设置界面的 `/settings` 配置
- **软删除**：数据通过 `archived=true` 标记，而非物理删除
- **内容提取**：content-core 库用于文件和 URL 提取；支持 50+ 文件类型，但内容提取是同步的 — 大文件会短暂阻塞 API

## 代码质量

```bash
make ruff     # 自动修复 Python 代码问题
make lint     # mypy 类型检查
uv run pytest # 运行测试
```

已配置 pre-commit hooks（`.pre-commit-config.yaml`）— 可通过 `uv run pre-commit install` 安装。

## Docker 构建

```bash
make docker-build-local  # 本地构建，不推送
make docker-push         # 多平台 buildx 推送（仅版本标签，不更新 latest）
make docker-release     # 推送版本 + 更新 v1-latest 标签
```

使用 `Dockerfile.single` 构建单容器镜像变体。

用中文回答我