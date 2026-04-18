# 智研舱（ZhiyanCang）PRD v1.0
## 面向 Codex 的产品设计、页面结构与后端拆分清单

作者：OpenAI GPT-5.4 Pro  
日期：2026-04-18

---

## 0. 这份文档怎么用

这是一份直接给 Codex 落地开发的文档，不是比赛宣讲稿。

目标只有一个：**把现有 `notebook-Multimodal-RAG` 从“功能型开源底座”改造成“项目级 Agent 产品”**。

这份文档包含四部分：
1. 产品 PRD
2. 页面结构图与前端路由规划
3. 后端模块拆分清单
4. Codex 实施顺序与落地约束

---

# 1. 产品总述

## 1.1 产品名

**中文名：智研舱**  
**英文名：Project Memory Copilot**

## 1.2 一句话定位

一个面向**科研、竞赛、项目申报、复杂资料研读**的多模态 Agent 工作台。  
它不是“聊天式知识库”，而是一个**会持续学习、会记住项目、会组织证据、会生成产物**的 AI 项目副驾。

## 1.3 产品主张

用户把论文、PDF、PPT、网页、图片、图表、音视频、规则文档等资料放进项目空间后，系统会：

- 自动建立项目画像
- 自动抽取结构化事实
- 自动维护长期记忆
- 根据问题类型调用合适 agent
- 基于证据回答，而不是空口回答
- 最终生成综述、对比报告、答辩提纲、问答卡片等成果

## 1.4 为什么这个方向适合当前仓库

当前仓库已经有以下底座能力：

- 多模态资料导入与 notebook 管理
- 文本检索与 source chat
- Visual RAG 搜索、索引、会话、memory graph
- SeekDB 检索与异步 Worker
- 前后端完整 Web 架构

所以正确方向不是“推倒重写一个新应用”，而是：

> **保留现有能力层，新增项目级 harness、agent 编排、多层 memory 和高价值工作流。**

---

# 2. 产品 PRD

## 2.1 背景问题

当前项目的问题不是没有能力，而是**没有产品主线**：

- 顶层仍是 Open Notebook 的技术形态，不是一个清晰的 AI 产品
- 首页和导航暴露的是 notebooks / podcasts / search / sources / transformations / vrag，而不是用户任务
- Visual RAG 很强，但只是功能点，没有被提升为产品主角
- memory 只停留在视觉会话层，没有变成项目长期记忆
- 缺少对比、结构化抽取、答辩辅助、成果输出等高价值工作流
- 缺少 agent run trace、memory governance、eval harness，难以体现“前沿 AI 产品”属性

## 2.2 目标用户

### P0 目标用户
1. **竞赛型学生团队**  
   需要阅读比赛规则、技术文档、论文、往届资料，并准备答辩。

2. **科研型学生/老师**  
   需要阅读多篇论文、做综述、比对图表、生成研究汇报。

3. **项目申报/课题团队**  
   需要分析申报书、评分标准、修改意见、多版本文档。

### P1 延展用户
- 企业知识工程团队
- 招投标文档分析团队
- 政策/法规研究团队

## 2.3 核心使用场景

### 场景 A：竞赛备赛
用户导入比赛规则、题目说明、技术文档、论文、PPT、演示稿、往届样例。  
系统输出：
- 项目画像
- 关键要求清单
- 风险点
- 评委可能提问
- 答辩提纲
- 证据化回答

### 场景 B：科研阅读
用户导入多篇论文和实验记录。  
系统输出：
- 研究主题图谱
- 方法对比
- 数据图表解释
- 文献综述草稿
- 值得追问的问题

### 场景 C：文档对比与修改
用户导入申报书 v1/v2、评分标准、评审意见。  
系统输出：
- 差异项
- 缺失项
- 冲突项
- 建议补写内容
- 变更摘要

## 2.4 产品目标

### P0 业务目标
- 将“上传文档 + 聊天”升级为“项目工作台”
- 把 Visual RAG、文本 RAG、memory、artifact 输出整合成单一体验
- 让系统能完成至少 4 类高价值任务：问答、对比、记忆、输出

### P0 技术目标
- 引入 **project harness**，将工具调用、agent handoff、memory 写入、trace 展示统一起来
- 引入 **project memory** 和 **user memory**
- 引入 **eval harness**，可对核心能力做回归评测

## 2.5 非目标

以下不是第一阶段重点：

- 不追求再接入更多 LLM 供应商
- 不优先做团队协作与权限系统
- 不优先做复杂工作流编排 UI
- 不优先做泛行业大而全平台

## 2.6 MVP 核心能力（必须做）

### 1）项目空间（Project Workspace）
替代 notebook 概念。

能力：
- 创建项目
- 导入资料
- 项目总览
- 最近任务/产物

### 2）证据问答（Evidence QA）
一个统一的“项目副驾”入口。

要求：
- 自动判断文本问答 / 图表问答 / 多模态联合问答
- 回答必须附证据
- 证据至少包含：来源文件、页码、引用文本、必要时的图像缩略信息

### 3）结构化抽取（Structured Extraction）
导入后自动抽取：
- 主题
- 关键词
- 术语
- 人物/机构
- 时间节点
- 指标与结论
- 风险项
- 要求项

### 4）多文档对比（Compare）
支持：
- 两个文件对比
- 同一文件版本对比
- 规则 vs 方案
- PPT vs 正文

输出：
- 相同点
- 差异点
- 冲突点
- 缺失点
- 需人工确认点

### 5）长期记忆（Memory Center）
支持：
- 项目记忆
- 用户偏好记忆
- 记忆来源可追溯
- 允许人工确认、编辑、冻结、删除

### 6）成果生成（Output Studio）
生成：
- 项目综述
- 文献综述
- 修改建议
- 答辩提纲
- 评委问题清单
- 问答卡片

### 7）运行轨迹（Runs / Trace）
展示一次任务里：
- 目标
- agent plan
- 调用的工具
- 读取的证据
- 写入的记忆
- 生成的产物
- 失败原因

## 2.7 差异化能力

### 差异化 1：项目级 Harness
不是一个 chat bot，而是一个有 control plane 的 agent 系统：
- planner
- router
- skill registry
- run manager
- memory writer
- guardrails
- evaluator

### 差异化 2：多层 memory
分成：
- Run Memory：单次任务上下文
- Evidence Memory：证据层
- Project Memory：项目长期记忆
- User Memory：用户偏好与习惯

### 差异化 3：证据优先
回答不允许只给结论，必须给证据卡片。

### 差异化 4：答辩辅助
系统天然适合计算机设计大赛、科研汇报、项目答辩场景。

## 2.8 关键指标

### 产品指标
- 首次导入后 60 秒内可看到项目画像（对 demo 数据）
- 80% 以上回答带有效证据引用
- 至少 70% 的对比任务可输出结构化差异清单
- 产物生成从问答可一键进入，不超过 2 次点击

### 体验指标
- 用户在 3 分钟内完成一次完整闭环：导入 → 提问 → 查看证据 → 生成报告
- 运行轨迹可回放
- memory 可见、可管、可删除

---

# 3. 产品体验与信息架构

## 3.1 新的信息架构原则

前台不再以“功能目录”组织，而以“项目工作流”组织。

### 当前问题
当前导航类似：
- notebooks
- podcasts
- search
- sources
- transformations
- vrag

这更像开发者视角。

### 新导航原则
改为用户任务视角：
- 项目
- 证据
- 对比
- 记忆
- 输出
- 运行

## 3.2 页面结构图（新版）

```text
/dashboard
  /projects
    /page.tsx                        # 项目列表页
    /new/page.tsx                    # 新建项目
    /[projectId]
      /layout.tsx                    # 项目级布局
      /overview/page.tsx             # 项目总览
      /evidence/page.tsx             # 统一证据问答工作台
      /evidence/[threadId]/page.tsx  # 指定会话
      /compare/page.tsx              # 文档对比中心
      /memory/page.tsx               # 记忆中心
      /outputs/page.tsx              # 产物工坊
      /runs/page.tsx                 # agent 运行轨迹
      /sources/page.tsx              # 项目资料列表
      /sources/[sourceId]/page.tsx   # 资料详情 / 阅读器
      /settings/page.tsx             # 项目设置

  /admin
    /models/page.tsx                 # 模型与 provider 管理（低优先）
    /evals/page.tsx                  # 回归评测与数据集管理
    /jobs/page.tsx                   # 异步任务面板
```

## 3.3 当前路由到新路由的映射

| 当前概念 | 新概念 | 处理策略 |
|---|---|---|
| notebooks | projects | 主概念替换 |
| notebooks/[id] | projects/[projectId]/overview | 详情首页改成总览 |
| notebooks/[id]/visual | projects/[projectId]/evidence | 变为证据工作台的一部分 |
| sources | projects/[projectId]/sources | 收进项目内部 |
| search | projects/[projectId]/evidence | 并入统一问答/检索 |
| transformations | projects/[projectId]/outputs | 并入产物工坊 |
| podcasts | projects/[projectId]/outputs | 作为一种产物类型 |
| vrag | projects/[projectId]/evidence | 保留兼容页，不再主打 |

---

# 4. 关键页面 PRD

## 4.1 项目列表页 `/dashboard/projects`

### 页面目标
让用户先看到“项目”，不是先看到聊天框。

### 核心模块
- 项目卡片列表
- 最近活动
- 最近产物
- 推荐 demo 项目
- 新建项目按钮

### 关键动作
- 创建项目
- 进入项目
- 复制 demo 项目
- 删除/归档项目

### 接口
- `GET /api/projects`
- `POST /api/projects`
- `DELETE /api/projects/{projectId}`

## 4.2 项目总览页 `/dashboard/projects/[projectId]/overview`

### 页面目标
让用户 10 秒内理解：这是什么项目、有哪些资料、什么最重要。

### 核心模块
1. 项目摘要卡
2. 资料统计卡
3. 核心主题与术语
4. 风险点 / 开放问题
5. 时间线
6. 推荐问题
7. 最近运行任务
8. 最近产物

### 关键动作
- 一键进入提问
- 一键生成综述
- 一键生成答辩提纲
- 点击风险项进入证据定位

### 接口
- `GET /api/projects/{projectId}/overview`
- `POST /api/projects/{projectId}/overview/rebuild`

## 4.3 证据工作台 `/dashboard/projects/[projectId]/evidence`

### 页面目标
提供统一的问答、检索、视觉分析入口。

### 交互布局
左侧：会话列表 / 推荐问题  
中间：聊天与答案区  
右侧：证据卡片 / 来源定位 / 运行轨迹摘要

### 核心功能
- 自然语言提问
- 自动路由到 text / visual / compare / synthesis agent
- 证据卡片展示
- 追问与会话续写
- 从证据生成产物

### 回答格式要求
每次回答包含：
- `answer`
- `evidence_cards[]`
- `confidence`
- `memory_updates[]`
- `suggested_followups[]`

### 证据卡片字段
- source_name
- page_no
- excerpt
- image_thumb（可选）
- citation_text
- relevance_reason
- internal_ref

### 接口
- `POST /api/projects/{projectId}/ask`
- `GET /api/projects/{projectId}/threads`
- `GET /api/projects/{projectId}/threads/{threadId}`
- `POST /api/projects/{projectId}/threads/{threadId}/followup`

## 4.4 对比中心 `/dashboard/projects/[projectId]/compare`

### 页面目标
把“文档对比”从 prompt 技巧变成显式工作流。

### 核心模块
- 选择对比对象
- 对比维度选择
- 差异摘要
- 结构化差异表
- 冲突项与缺失项
- 导出报告

### 支持模式
- 文件 A vs 文件 B
- 文件 v1 vs v2
- 规则 vs 方案
- PPT vs 正文

### 输出格式
- summary
- similarities[]
- differences[]
- conflicts[]
- missing_items[]
- human_review_required[]

### 接口
- `POST /api/projects/{projectId}/compare`
- `GET /api/projects/{projectId}/compare/{compareId}`
- `POST /api/projects/{projectId}/compare/{compareId}/export`

## 4.5 记忆中心 `/dashboard/projects/[projectId]/memory`

### 页面目标
让长期记忆可见、可控、可验证。

### 分类
- 项目背景
- 术语定义
- 已确认事实
- 历史决策
- 用户偏好
- 待确认记忆

### 记忆展示字段
- memory_text
- scope
- type
- confidence
- freshness
- source_refs
- status（draft / accepted / frozen / deprecated）
- decay_policy

### 关键动作
- 接受写入
- 编辑
- 冻结
- 删除
- 合并冲突

### 接口
- `GET /api/projects/{projectId}/memory`
- `PATCH /api/projects/{projectId}/memory/{memoryId}`
- `DELETE /api/projects/{projectId}/memory/{memoryId}`
- `POST /api/projects/{projectId}/memory/rebuild`

## 4.6 产物工坊 `/dashboard/projects/[projectId]/outputs`

### 页面目标
把问答和分析沉淀为可交付成果。

### 产物类型
- 项目综述
- 文献综述
- 差异报告
- 风险清单
- 答辩提纲
- 评委问题清单
- 问答卡片
- 汇报讲稿
- 播客音频（后续）

### 关键动作
- 新建产物
- 从回答生成产物
- 从对比结果生成产物
- 导出 markdown / pdf / docx（pdf/docx 后做）

### 接口
- `POST /api/projects/{projectId}/artifacts`
- `GET /api/projects/{projectId}/artifacts`
- `GET /api/projects/{projectId}/artifacts/{artifactId}`
- `POST /api/projects/{projectId}/artifacts/{artifactId}/regenerate`

## 4.7 运行轨迹页 `/dashboard/projects/[projectId]/runs`

### 页面目标
增强可解释性与调试性。

### 核心模块
- 任务列表
- 单次 run 详情
- step timeline
- tool calls
- evidence reads
- memory writes
- artifact outputs
- failures / retries

### 接口
- `GET /api/projects/{projectId}/runs`
- `GET /api/projects/{projectId}/runs/{runId}`
- `GET /api/projects/{projectId}/runs/{runId}/trace`

## 4.8 资料详情页 `/dashboard/projects/[projectId]/sources/[sourceId]`

### 页面目标
让用户看到原始材料，而不是只看 AI 总结。

### 核心模块
- 文档阅读器
- 页码导航
- 视觉页面摘要
- 结构化抽取结果
- 证据锚点
- 对这个资料发起问答 / 对比 / 产物生成

---

# 5. Agent 与 Harness 设计

## 5.1 总体原则

前台只暴露一个角色：**项目副驾**。  
后台由多个 agent 协作，但不让用户感知“切换 bot”。

## 5.2 Agent 清单

### A. Intake Agent
职责：
- 资料导入后分析文件类型
- 生成 source profile
- 生成项目画像初稿
- 提取术语、主题、风险、时间线

### B. Evidence Agent
职责：
- 统一处理问答
- 判断走 text search / visual search / mixed search
- 组装证据卡片

### C. Compare Agent
职责：
- 进行文档差异检测
- 生成结构化对比结果

### D. Synthesis Agent
职责：
- 基于证据与记忆生成综述、摘要、报告

### E. Defense Coach Agent
职责：
- 生成评委问题
- 识别薄弱点
- 生成证据化回答

### F. Memory Curator Agent
职责：
- 从 run 结果中筛选值得写入长期记忆的内容
- 合并冲突记忆
- 处理记忆衰减与确认状态

## 5.3 Harness 组件

### Planner
对复杂任务做粗粒度拆分。

### Router
判断请求类型：
- ask
- compare
- summarize
- defense
- extract
- rebuild

### Skill Registry
预定义 skill，避免大模型每次从零规划。

推荐 skill：
- `ingest_project_sources`
- `build_project_overview`
- `answer_with_evidence`
- `compare_sources`
- `write_project_memory`
- `generate_artifact`
- `prepare_defense_pack`

### Run Manager
维护 run 生命周期：
- queued
- running
- waiting_review
- completed
- failed
- cancelled

### Context Packer
负责上下文压缩与上下文拼装。

### Memory Writer
执行 memory policy，决定什么能写入长期记忆。

### Guardrails
保证：
- 必须证据优先
- 不足证据时明确不确定
- 不把未确认结论写成强记忆

### Evaluator Hooks
每次 run 完成后可触发小型自动评测。

## 5.4 推荐的 run 流程

```text
User Request
  -> Router
  -> Planner（复杂任务才进入）
  -> Skill Selection
  -> Tool Calls / Existing Services
  -> Evidence Aggregation
  -> Answer / Compare / Artifact
  -> Memory Curation
  -> Run Trace Persist
  -> Optional Eval
```

---

# 6. Memory 设计

## 6.1 四层 memory

### 1）Run Memory
单次任务上下文。  
来源：当前会话、tool output、reasoning trace。  
现有 Visual RAG session / memory_graph 可以直接复用。

### 2）Evidence Memory
项目证据层。  
本质是高频检索用的证据单元。

存储对象：
- page summary
- chunk
- image summary
- bbox evidence
- structured fact
- citation block

### 3）Project Memory
项目长期记忆。  
存储：
- 项目背景
- 术语定义
- 已确认事实
- 历史决策
- 风险项
- 开放问题

### 4）User Memory
用户长期偏好。

存储：
- 输出偏好
- 语言风格
- 常用视角
- 老师/评委关注点

## 6.2 Memory policy

### 能写入长期记忆的内容
只允许两类：
1. 有证据支撑的稳定事实
2. 用户明确确认的偏好 / 决策

### 不允许直接写入长期记忆的内容
- 临时推测
- 单次 run 的未验证结论
- 无引用的自由回答
- 互相冲突但未解决的信息

## 6.3 Memory record schema

```json
{
  "id": "mem_xxx",
  "scope": "project|user",
  "type": "fact|term|decision|risk|preference",
  "text": "...",
  "confidence": 0.86,
  "freshness": "2026-04-18T10:00:00Z",
  "source_refs": ["src_1:p12", "src_2:p4"],
  "accepted": false,
  "status": "draft",
  "decay_policy": "strong|normal|weak",
  "conflict_group": "term:model_name"
}
```

## 6.4 存储策略

- **SeekDB**：热证据与结构化检索层
- **PowerMem**：长期记忆层（project/user memory）
- **business_store / 业务表**：实体、任务、关系、产物

---

# 7. 后端模块拆分清单

## 7.1 总原则

**不推倒现有代码，只在现有工程上加一层 Project Harness。**

保留：
- `open_notebook/visual_rag/`
- `open_notebook/vrag/`
- `open_notebook/seekdb/`
- `open_notebook/jobs/`
- `api/` 现有服务式组织方式
- `frontend/src/app/(dashboard)` 现有 Next.js 架构

新增模块要与现有风格兼容。

## 7.2 推荐的代码目录

### 后端目录（新增）

```text
open-notebook/
  api/
    routers/
      projects.py
      project_evidence.py
      project_compare.py
      project_memory.py
      project_artifacts.py
      project_runs.py
    project_workspace_service.py
    project_evidence_service.py
    project_compare_service.py
    project_memory_service.py
    project_artifact_service.py
    project_run_service.py
    project_overview_service.py

  commands/
    project_commands.py
    project_memory_commands.py
    compare_commands.py
    artifact_commands.py
    eval_commands.py

  open_notebook/
    agent_harness/
      __init__.py
      planner.py
      router.py
      skill_registry.py
      run_manager.py
      context_packer.py
      trace_store.py
      guardrails.py
      evaluator_hooks.py

    agents/
      __init__.py
      intake_agent.py
      evidence_agent.py
      compare_agent.py
      synthesis_agent.py
      defense_coach_agent.py
      memory_curator_agent.py

    project_os/
      __init__.py
      overview_service.py
      source_profile_service.py
      timeline_service.py
      compare_service.py
      artifact_service.py
      defense_service.py

    memory_center/
      __init__.py
      powermem_adapter.py
      memory_policy.py
      memory_writer.py
      memory_resolver.py
      user_profile_service.py

    evidence/
      __init__.py
      structured_extractor.py
      fact_service.py
      evidence_card_service.py
      citation_service.py
      source_locator.py

    domain/
      projects.py
      evidence.py
      compare.py
      memory.py
      artifacts.py
      runs.py
```

## 7.3 各模块职责

### `api/project_workspace_service.py`
职责：
- 项目 CRUD
- 项目首页聚合查询
- 项目统计信息

### `api/project_evidence_service.py`
职责：
- 接收问答请求
- 调用 router / planner / evidence agent
- 组装回答结构

### `api/project_compare_service.py`
职责：
- 创建 compare job
- 获取 compare 结果
- 导出 compare 报告

### `api/project_memory_service.py`
职责：
- 列出长期记忆
- 审核/编辑/删除记忆
- rebuild memory

### `api/project_artifact_service.py`
职责：
- 创建产物
- 读取产物
- 重生成产物

### `api/project_run_service.py`
职责：
- run 列表
- trace 详情
- 失败重试

### `open_notebook/agent_harness/router.py`
职责：
- 判定意图类型
- 区分 simple ask / compare / artifact / defense / rebuild

### `open_notebook/agent_harness/planner.py`
职责：
- 仅对复杂任务做高层计划
- 产生 skill plan

### `open_notebook/agent_harness/skill_registry.py`
职责：
- 注册 skill
- 定义输入输出 schema
- 定义可调用工具集

### `open_notebook/agent_harness/run_manager.py`
职责：
- 创建 run
- 更新状态
- 记录 steps
- 写 trace

### `open_notebook/agent_harness/context_packer.py`
职责：
- 选取 relevant memory
- 选取 relevant evidence
- 控制 prompt 大小
- 生成 compact context

### `open_notebook/agent_harness/trace_store.py`
职责：
- 持久化 step、tool call、memory write、artifact id

### `open_notebook/agent_harness/guardrails.py`
职责：
- 低证据时降置信度
- 阻止无证据写 memory
- 输出前校验 citation 是否为空

### `open_notebook/agents/evidence_agent.py`
职责：
- 调用 text retrieval / visual rag / mixed search
- 组装 evidence cards
- 生成回答

### `open_notebook/agents/compare_agent.py`
职责：
- 读取两个 source 的结构化事实
- 生成差异清单与摘要

### `open_notebook/agents/memory_curator_agent.py`
职责：
- 从 run 中筛选值得写入 memory 的内容
- 处理 conflict group

### `open_notebook/memory_center/powermem_adapter.py`
职责：
- PowerMem 的读写封装
- scope 管理
- search / add / update / archive

### `open_notebook/evidence/structured_extractor.py`
职责：
- 从 source 文本与页面摘要中抽取 structured facts

### `open_notebook/evidence/evidence_card_service.py`
职责：
- 统一证据卡片 schema
- 生成 citation、excerpt、source locator

---

# 8. 与现有代码的对接策略

## 8.1 继续复用的现有能力

### Visual RAG
继续作为视觉问答能力层，不直接暴露给用户做“主产品入口”。

处理策略：
- 保留 `open_notebook/visual_rag/api.py`
- 新增 `project_evidence_service` 包装层
- 由 `Evidence Agent` 根据问题类型决定是否调用 visual_rag

### VRAG Agent / Memory Graph
继续作为 **Run Memory** 的底层。

处理策略：
- 不替换 `MultimodalMemoryGraph`
- 在项目级 run 中把它作为 step evidence graph 来引用

### SeekDB Retrieval
继续作为热证据检索层。

处理策略：
- 复用 `retrieval_service.py`
- 为 structured facts / evidence cards 增加 collection 或表结构

### Jobs / Worker / Commands
继续作为长任务执行框架。

处理策略：
- 不新引入 Celery
- 通过 `commands/*.py` 新增项目级任务
- 统一复用 job store / queue / worker

## 8.2 需要改名但不一定改底层实现的概念

| 原名 | 新名 | 底层是否重写 |
|---|---|---|
| notebook | project space | 否，先做别名迁移 |
| source chat | evidence QA | 否，包装即可 |
| visual rag | visual evidence | 否，包装即可 |
| transformation | artifact generation | 否，包装即可 |
| podcast | audio artifact | 否，包装即可 |

## 8.3 建议新增 command

```text
project.build_overview
project.extract_facts
project.compare_sources
project.generate_artifact
project.prepare_defense_pack
project.refresh_memory
project.eval_run
```

每个 command 要遵守现有 command registry + job queue 机制。

---

# 9. 数据模型设计

## 9.1 业务实体

### ProjectSpace
```json
{
  "id": "proj_xxx",
  "name": "计算机设计大赛-多模态RAG项目",
  "description": "...",
  "owner_id": "user_xxx",
  "status": "active",
  "created_at": "...",
  "updated_at": "..."
}
```

### SourceProfile
```json
{
  "id": "sp_xxx",
  "project_id": "proj_xxx",
  "source_id": "src_xxx",
  "source_type": "pdf|ppt|image|audio|web",
  "title": "...",
  "summary": "...",
  "topics": ["..."],
  "keywords": ["..."],
  "risks": ["..."],
  "timeline_events": [],
  "fact_count": 42
}
```

### StructuredFact
```json
{
  "id": "fact_xxx",
  "project_id": "proj_xxx",
  "source_id": "src_xxx",
  "fact_type": "term|claim|metric|time|person|org|risk|requirement",
  "text": "...",
  "normalized_key": "...",
  "page_no": 12,
  "confidence": 0.82,
  "citation_text": "..."
}
```

### EvidenceCard
```json
{
  "id": "ev_xxx",
  "project_id": "proj_xxx",
  "thread_id": "thr_xxx",
  "source_id": "src_xxx",
  "page_no": 4,
  "excerpt": "...",
  "image_path": "...",
  "citation_text": "...",
  "relevance_reason": "...",
  "score": 0.91
}
```

### ArtifactRecord
```json
{
  "id": "art_xxx",
  "project_id": "proj_xxx",
  "artifact_type": "overview|compare_report|defense_pack|qa_cards",
  "title": "...",
  "content_md": "...",
  "status": "ready",
  "source_refs": ["src_1", "src_2"],
  "created_by_run_id": "run_xxx"
}
```

### AgentRun
```json
{
  "id": "run_xxx",
  "project_id": "proj_xxx",
  "run_type": "ask|compare|artifact|memory_rebuild",
  "status": "queued|running|completed|failed",
  "input_json": {},
  "output_json": {},
  "started_at": "...",
  "completed_at": "..."
}
```

### AgentStep
```json
{
  "id": "step_xxx",
  "run_id": "run_xxx",
  "step_index": 3,
  "agent_name": "evidence_agent",
  "tool_name": "visual_rag.search",
  "input_json": {},
  "output_json": {},
  "status": "ok|failed"
}
```

## 9.2 存储建议

### 继续使用 business_store 的关系边
现有 `artifact`、`reference`、`refers_to` 关系可继续复用。  
建议新增：
- `project_contains_source`
- `artifact_generated_by_run`
- `memory_supported_by_evidence`
- `fact_extracted_from_source`

### 新增表建议
- `project_space`
- `source_profile`
- `structured_fact`
- `evidence_card`
- `agent_run`
- `agent_step`
- `compare_job`
- `memory_review_log`

---

# 10. API 设计

## 10.1 项目管理

### `GET /api/projects`
返回项目列表。

### `POST /api/projects`
创建项目。

请求：
```json
{
  "name": "智研舱 Demo",
  "description": "比赛演示项目"
}
```

## 10.2 项目总览

### `GET /api/projects/{projectId}/overview`
返回：
```json
{
  "project": {},
  "stats": {},
  "topics": [],
  "risks": [],
  "timeline": [],
  "suggested_questions": [],
  "recent_artifacts": []
}
```

## 10.3 证据问答

### `POST /api/projects/{projectId}/ask`
请求：
```json
{
  "thread_id": "optional",
  "question": "这个项目的主要创新点是什么？",
  "mode": "auto"
}
```

返回：
```json
{
  "thread_id": "thr_xxx",
  "answer": "...",
  "confidence": 0.84,
  "evidence_cards": [],
  "memory_updates": [],
  "run_id": "run_xxx",
  "suggested_followups": []
}
```

## 10.4 对比

### `POST /api/projects/{projectId}/compare`
请求：
```json
{
  "left_source_id": "src_a",
  "right_source_id": "src_b",
  "compare_mode": "general"
}
```

返回：
```json
{
  "compare_id": "cmp_xxx",
  "status": "queued",
  "run_id": "run_xxx"
}
```

## 10.5 Memory

### `GET /api/projects/{projectId}/memory`
返回按类别分组的 memory。

### `PATCH /api/projects/{projectId}/memory/{memoryId}`
请求：
```json
{
  "status": "accepted",
  "text": "可选修改后的内容"
}
```

## 10.6 Artifacts

### `POST /api/projects/{projectId}/artifacts`
请求：
```json
{
  "artifact_type": "defense_pack",
  "title": "答辩问题与回答",
  "source_thread_id": "thr_xxx"
}
```

### `GET /api/projects/{projectId}/artifacts/{artifactId}`
返回 markdown 内容与引用源。

## 10.7 Runs

### `GET /api/projects/{projectId}/runs`
### `GET /api/projects/{projectId}/runs/{runId}`
### `GET /api/projects/{projectId}/runs/{runId}/trace`

---

# 11. 前端组件拆分建议

## 11.1 新组件目录

```text
frontend/src/components/projects/
  project-card.tsx
  project-create-dialog.tsx
  project-overview-header.tsx
  topic-cluster-card.tsx
  risk-list-card.tsx
  timeline-card.tsx

frontend/src/components/evidence/
  copilot-chat-panel.tsx
  evidence-card.tsx
  evidence-side-panel.tsx
  answer-block.tsx
  source-jump-button.tsx

frontend/src/components/compare/
  compare-form.tsx
  compare-summary.tsx
  diff-table.tsx
  conflict-list.tsx

frontend/src/components/memory/
  memory-list.tsx
  memory-card.tsx
  memory-review-dialog.tsx
  memory-conflict-panel.tsx

frontend/src/components/artifacts/
  artifact-list.tsx
  artifact-editor.tsx
  artifact-template-picker.tsx

frontend/src/components/runs/
  run-list.tsx
  run-detail.tsx
  step-timeline.tsx
  tool-call-card.tsx
```

## 11.2 状态管理建议

- 项目数据：React Query
- 会话与回答流：SSE + local state
- 运行状态：polling + React Query
- 临时 UI 状态：zustand（可选）

---

# 12. Codex 落地顺序

## Phase 1：先把产品主线立起来

### 目标
让产品从“功能目录”变成“项目工作台”。

### 必做
1. notebook 重命名为 project（前台文案级别先改）
2. 新建 `/dashboard/projects`
3. 新建 `/dashboard/projects/[projectId]/overview`
4. 新建 `/dashboard/projects/[projectId]/evidence`
5. 复用现有 search/source_chat/visual_rag 实现统一问答
6. 问答结果统一为 evidence card 结构

### 验收
- 可以创建项目
- 可以进入项目总览
- 可以在 evidence 页面提问并看到证据卡片

## Phase 2：把高价值能力做出来

### 必做
1. `structured_extractor.py`
2. overview 自动构建
3. compare 页面与 compare command
4. artifacts 页面与 artifact generation
5. memory center 基础读写

### 验收
- 能生成项目画像
- 能对比两份文档
- 能生成答辩提纲或综述
- 能看到项目长期记忆

## Phase 3：把 agent 产品感做出来

### 必做
1. run trace 页面
2. skill registry
3. planner/router 更细化
4. memory policy & review
5. eval hooks

### 验收
- 每次任务都有 run_id
- 可以看到步骤轨迹
- 可以看到 memory 是否被写入
- 可以触发回归评测

## Phase 4：比赛版打磨

### 必做
1. demo 数据预置
2. 首页文案与命名统一
3. 一键演示路径
4. 输出版式优化
5. 稳定性修复

---

# 13. 给 Codex 的实现约束

## 13.1 不要做的事

- 不要大规模重写 SeekDB / visual_rag 底层
- 不要再扩更多模型 provider
- 不要引入第二套任务队列
- 不要先做复杂权限系统
- 不要先做花哨动画

## 13.2 必须做的事

- 保持现有 API / worker 风格
- 新功能优先走 command registry + job queue
- 所有新回答都用统一 response schema
- 所有新长期记忆都必须带 `source_refs`
- 所有新产物都必须能追溯到 run_id

## 13.3 代码组织规则

- `api/routers/` 放 HTTP 路由
- `api/*_service.py` 放聚合服务
- `open_notebook/*` 放领域能力层
- `commands/*.py` 放长任务 command
- 前端按项目、证据、对比、记忆、输出、运行拆组件

---

# 14. 建议新增的仓库文档

为了让 Codex 长任务更稳，建议在仓库新增：

```text
AGENTS.md
/docs/
  product-prd.md
  architecture.md
  routes.md
  apis.md
  memory-policy.md
  skill-catalog.md
  evals.md
```

## 14.1 AGENTS.md 内容建议

只写导航，不写百科全书。

包括：
- 本仓库目标
- 关键目录说明
- 编码规则
- 文档索引
- 开发顺序
- 哪些模块不要随便重写

## 14.2 docs/memory-policy.md

明确：
- 哪些信息允许写入长期记忆
- 哪些必须人工确认
- 哪些只放 run memory

## 14.3 docs/skill-catalog.md

列出每个 skill：
- 输入
- 输出
- 可用工具
- done condition
- 失败处理

---

# 15. 最终一句话给 Codex

> 在现有 `open-notebook + visual_rag + seekdb + jobs` 底座上，构建一个新的“项目级 agent 工作台”。优先做 `projects / overview / evidence / compare / memory / outputs / runs` 这 7 个主页面，以及 `agent_harness / agents / memory_center / evidence / project_os` 这 5 个后端能力层。不要推翻底层，先完成产品主线收口与统一 response schema。

