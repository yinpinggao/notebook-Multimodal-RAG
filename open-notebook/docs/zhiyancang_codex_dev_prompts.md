# 智研舱 Codex 开发顺序 Prompt v1

作者：OpenAI GPT-5.4 Pro  
日期：2026-04-18

---

## 0. 使用方法

这份文档给你一组可以直接粘给 Codex 的 prompt。  
推荐流程：

1. 先执行 **P0 全局启动 prompt**
2. 再按顺序执行 `P1 -> P12`
3. 每次只做一个 prompt
4. 等 Codex 完成并人工验收后，再进入下一个 prompt

---

## P0｜全局启动 Prompt（先发一次）

```text
你正在修改仓库 `notebook-Multimodal-RAG/open-notebook`。

目标不是继续做“另一个 NotebookLM”，而是把当前项目逐步改造成一个新的 AI 产品：**智研舱（Project Memory Copilot）**。

产品定位：
- 面向科研、竞赛、项目申报、复杂资料研读
- 一个“会持续学习、会记住项目、会组织证据、会生成产物”的 AI 项目副驾
- 前台主线按项目工作流组织：项目、证据、对比、记忆、输出、运行
- 后台保留现有 Open Notebook + Visual RAG + SeekDB + Worker 能力层

硬约束：
1. 不要大规模重写现有 `visual_rag / vrag / seekdb / jobs/worker`
2. 不要引入第二套任务队列
3. 保持现有 `api/routers + api/*_service.py + commands/*.py + worker` 风格
4. 新功能优先新增包装层，而不是推翻底层
5. 所有长期记忆必须带 `source_refs`
6. 所有产物必须带 `created_by_run_id`
7. 如果证据不足，回答必须表达不确定，而不是假装确定
8. 每次任务结束都要输出：
   - Summary
   - Files Changed
   - Validation
   - Known Gaps

实施原则：
- 一次只实现当前 issue
- 先 contract/schema，再 service，再 UI
- 优先交付最小可运行版本
- 不要顺手做额外大改
- 若发现现有仓库已有相同能力，优先复用而不是重造

先阅读：
- `AGENTS.md`（若已存在）
- `docs/product-prd.md`
- `docs/architecture.md`
- `docs/routes.md`
- `docs/apis.md`
- `docs/memory-policy.md`

如果这些文件还不存在，就按当前 issue 先补齐最小骨架。

收到后，不要立刻改很多文件；先说明你准备修改的文件、实现范围、验证方式，然后再开始编码。
```

---

## P1｜ZYC-00 新增 AGENTS.md 与 docs 导航骨架

```text
实现 issue: ZYC-00

目标：
为仓库新增 `AGENTS.md` 和 `docs/` 下的核心文档骨架，让后续 Codex 长任务有统一指令与上下文。

请完成：
1. 在仓库根目录新增 `AGENTS.md`
2. 在 `docs/` 下新增或完善：
   - `product-prd.md`
   - `architecture.md`
   - `routes.md`
   - `apis.md`
   - `memory-policy.md`
3. 在 `README.dev.md` 或 `MAINTAINER_GUIDE.md` 中增加这些文档的索引入口
4. 文档内容要精炼，但不能是空壳；至少包括：
   - 产品定位
   - 代码组织规则
   - 禁止事项
   - 新路由规划
   - 新 API 骨架
   - memory policy

硬约束：
- 不修改业务逻辑
- 不改数据库
- 不改前端业务页面
- 不删除现有 `CLAUDE.md`，可以共存

验收标准：
- 新增 `AGENTS.md`
- `docs/` 下有 5 个可读文档
- 文档之间有互相引用
- 项目仍可启动

请先给出：
- 准备改哪些文件
- 每个文件写什么
- 打算如何验证
然后再开始实现。
```

---

## P2｜ZYC-01 建立 Project Workspace 路由与命名别名层

```text
实现 issue: ZYC-01

目标：
在不破坏现有 notebook 功能的前提下，新增新的产品主路线由：Project Workspace。

请完成：
1. 在 `frontend/src/app/(dashboard)/projects/` 下新增页面骨架：
   - `page.tsx`
   - `new/page.tsx`
   - `[projectId]/layout.tsx`
   - `[projectId]/overview/page.tsx`
   - `[projectId]/evidence/page.tsx`
   - `[projectId]/compare/page.tsx`
   - `[projectId]/memory/page.tsx`
   - `[projectId]/outputs/page.tsx`
   - `[projectId]/runs/page.tsx`
2. 调整 dashboard 主导航，把主入口改成 `projects`
3. 第一阶段允许 `projectId` 直接映射现有 notebook id
4. `/vrag` 不删除，但不要继续作为主导航主入口

实现要求：
- 页面先允许 placeholder 内容
- 文案使用：项目、证据、对比、记忆、输出、运行
- 不要删除旧 notebook 页面
- 若需要，新增一个轻量 alias 工具层（例如 `project-alias.ts`）

验收标准：
- 所有新路由都能访问
- 主导航可进入 `/dashboard/projects`
- 项目内 layout 可切换六个标签
- 旧页面不受影响

请先列出：
- 会修改哪些现有导航/布局文件
- 新增哪些 route files
- 是否需要 alias 层
然后再编码。
```

---

## P3｜ZYC-02 新增领域模型与统一响应 schema

```text
实现 issue: ZYC-02

目标：
为新产品主线建立统一的后端 contract，让后续 service/API/UI 都围绕稳定 schema 开发。

请完成：
1. 在 `open_notebook/domain/` 下新增或完善：
   - `projects.py`
   - `evidence.py`
   - `memory.py`
   - `artifacts.py`
   - `runs.py`
2. 若仓库已有 schema 目录则复用，否则新增最小 schema 文件
3. 至少定义这些结构：
   - `ProjectSummary`
   - `ProjectOverviewResponse`
   - `EvidenceCard`
   - `AskResponse`
   - `CompareSummary`
   - `ArtifactRecord`
   - `MemoryRecord`
   - `AgentRun`
   - `AgentStep`
4. 更新 `docs/apis.md`，写清新 contract

字段要求：
- `EvidenceCard` 必须有 `source_name/source_id/page_no/excerpt/citation_text/internal_ref`
- `MemoryRecord` 必须有 `source_refs/status/confidence`
- `ArtifactRecord` 必须有 `created_by_run_id`
- `AgentRun`/`AgentStep` 要能支持后续 trace

硬约束：
- 先不要做数据库迁移
- 先不要做真实 service
- 尽量沿用仓库已有的 pydantic / type 风格

验收标准：
- 新 schema 可 import
- 有最小单测或 schema snapshot
- `docs/apis.md` 已同步

先输出：
- 计划定义哪些类型
- 放在哪些文件
- 如何避免和现有类型冲突
然后再实现。
```

---

## P4｜ZYC-03 实现项目列表页与项目总览页骨架

```text
实现 issue: ZYC-03

目标：
让用户先从“项目”进入，而不是先看到功能目录。

请完成：
1. 实现项目列表页 UI
2. 实现项目总览页 UI 骨架
3. 新增可复用组件：
   - `project-card.tsx`
   - `project-overview-header.tsx`
   - `topic-cluster-card.tsx`
   - `risk-list-card.tsx`
   - `timeline-card.tsx`
4. 页面先允许使用 mock 数据或 placeholder fetch，但组件边界要贴近未来真实 API

页面要求：
- 项目列表页：项目卡片、新建按钮、demo 项目入口、最近活动占位
- 总览页：摘要、资料统计、主题、风险、时间线、推荐问题、最近产物

硬约束：
- 不接真实后端逻辑也可以
- 不做复杂状态管理
- 不在这一轮实现问答

验收标准：
- `/dashboard/projects`
- `/dashboard/projects/[projectId]/overview`
都具备完整布局
- 组件拆分合理
- 后续接真实 API 时不需要推倒重写

先输出：
- 组件拆分计划
- 数据接口预期 shape
- 如何与 ZYC-02 schema 对齐
然后再动手。
```

---

## P5｜ZYC-04 实现项目 CRUD 与 overview 聚合 API

```text
实现 issue: ZYC-04

目标：
把项目页从 placeholder 升级为真实后端数据。

请完成：
1. 新增 router：
   - `api/routers/projects.py`
2. 新增 service：
   - `api/project_workspace_service.py`
   - `api/project_overview_service.py`
3. 提供接口：
   - `GET /api/projects`
   - `POST /api/projects`
   - `DELETE /api/projects/{projectId}`
   - `GET /api/projects/{projectId}/overview`
   - `POST /api/projects/{projectId}/overview/rebuild`
4. 第一阶段允许底层继续复用 notebook 作为实体，但对外暴露 project 语义

实现要求：
- 返回结构遵守 ZYC-02 schema
- overview 先做聚合占位也可以：source count / artifact count / recent runs / 空 topics/risk
- 加最小测试
- 前端项目页改成真实请求

硬约束：
- 不做复杂权限
- 不做结构化抽取
- 不删 notebook API

验收标准：
- 项目列表页能显示真实项目
- 总览页能拿到真实 overview 数据
- 空项目也能稳定返回

请先说明：
- 你准备如何把 notebook 映射为 project
- overview 聚合第一版准备包含哪些字段
- 会修改哪些前端 fetch 逻辑
然后实现。
```

---

## P6｜ZYC-05 实现统一证据问答服务与 Evidence Card schema

```text
实现 issue: ZYC-05

目标：
把现有 source chat / search / visual_rag 封装成统一的项目级 `/ask` 服务。

请完成：
1. 新增 router：
   - `api/routers/project_evidence.py`
2. 新增 service：
   - `api/project_evidence_service.py`
3. 新增证据封装：
   - `open_notebook/evidence/evidence_card_service.py`
   - `open_notebook/evidence/citation_service.py`
4. 如有必要，新增最小 `router.py` 用于区分 text / visual / mixed
5. 提供接口：
   - `POST /api/projects/{projectId}/ask`
   - `GET /api/projects/{projectId}/threads`
   - `GET /api/projects/{projectId}/threads/{threadId}`
   - `POST /api/projects/{projectId}/threads/{threadId}/followup`

实现要求：
- `mode=auto` 自动路由 text / visual / mixed
- 优先复用现有能力，不重写检索逻辑
- 返回统一结构：
  - `answer`
  - `confidence`
  - `evidence_cards[]`
  - `memory_updates[]`
  - `run_id`
  - `suggested_followups[]`
- 如果证据不足，输出要明确不确定

验收标准：
- 至少一条文本问答走通
- 至少一条视觉相关问答走通
- 两种都返回统一 EvidenceCard 结构
- 加最小测试或 demo 调用脚本

先输出：
- 你准备复用哪些现有 service / api
- text / visual / mixed 的最小判定规则
- EvidenceCard 组装策略
然后再实现。
```

---

## P7｜ZYC-06 实现证据工作台前端与线程体验

```text
实现 issue: ZYC-06

目标：
把 `/ask` 真正变成用户可用的产品工作台。

请完成：
1. 实现：
   - `/dashboard/projects/[projectId]/evidence/page.tsx`
   - `/dashboard/projects/[projectId]/evidence/[threadId]/page.tsx`
2. 新增组件：
   - `copilot-chat-panel.tsx`
   - `evidence-card.tsx`
   - `evidence-side-panel.tsx`
   - `answer-block.tsx`
   - `source-jump-button.tsx`
3. 左中右布局：
   - 左：线程列表 / 推荐问题
   - 中：聊天和答案
   - 右：证据卡 / 来源定位 / run 摘要

实现要求：
- 支持首问和追问
- 若现有仓库已有 SSE/streaming 能力则复用，否则先普通请求
- 证据卡可跳到来源详情
- 保留 `run_id` 入口，为后续 runs 页面做铺垫

验收标准：
- 能提问
- 能看到答案和证据卡
- 能切换线程
- 能点击来源跳转

硬约束：
- 不实现完整 runs 页面
- 不实现长期 memory 操作 UI

先输出：
- 前端状态流怎么设计
- 是否用 streaming
- 哪些字段会在回答区显示
然后再编码。
```

---

## P8｜ZYC-07 实现结构化抽取、Source Profile 与 Overview Rebuild Job

```text
实现 issue: ZYC-07

目标：
让系统在用户提问前就自动形成项目画像。

请完成：
1. 新增：
   - `open_notebook/evidence/structured_extractor.py`
   - `open_notebook/project_os/source_profile_service.py`
   - `open_notebook/project_os/overview_service.py`
2. 新增/扩展 command：
   - `commands/project_commands.py`
3. 扩展 overview rebuild：
   - `POST /api/projects/{projectId}/overview/rebuild`
4. 抽取这些内容：
   - topics
   - keywords
   - terms
   - people/orgs
   - timeline events
   - metrics
   - risks
   - requirements

实现要求：
- 尽量利用现有 source text / page summary / image summary
- 第一版可用规则 + LLM 混合
- 支持异步 job，job 状态可查询或最少能回传 queued/running/completed
- 总览页要能展示真实抽取结果

验收标准：
- 对 demo 数据能抽出至少 2 类结构化信息
- overview 页显示真实主题/风险/时间线中的至少一部分
- rebuild job 跑得通

硬约束：
- 不做复杂知识图谱页面
- 不要求所有文件类型一次做全

先输出：
- structured fact 最小字段设计
- 计划新增哪些 job/command
- 如何把抽取结果接到 overview
然后再开始。
```

---

## P9｜ZYC-08 实现 Compare 服务、API、页面与导出

```text
实现 issue: ZYC-08

目标：
把文档对比做成显式工作流。

请完成：
1. 新增：
   - `api/routers/project_compare.py`
   - `api/project_compare_service.py`
   - `open_notebook/agents/compare_agent.py`
   - `open_notebook/project_os/compare_service.py`
   - `commands/compare_commands.py`
2. 实现前端：
   - `/dashboard/projects/[projectId]/compare/page.tsx`
   - `compare-form.tsx`
   - `compare-summary.tsx`
   - `diff-table.tsx`
   - `conflict-list.tsx`
3. 接口：
   - `POST /api/projects/{projectId}/compare`
   - `GET /api/projects/{projectId}/compare/{compareId}`
   - `POST /api/projects/{projectId}/compare/{compareId}/export`

实现要求：
- 第一版只支持 A vs B
- 优先使用结构化 facts 对比，再回落摘要对比
- 输出结构：
  - `summary`
  - `similarities[]`
  - `differences[]`
  - `conflicts[]`
  - `missing_items[]`
  - `human_review_required[]`
- 导出先支持 markdown

验收标准：
- 至少两份文本资料可对比
- 页面可看到摘要与差异表
- 导出 markdown 可查看

先输出：
- compare 结果的数据结构
- 同步/异步执行策略
- 前端页面分区设计
然后再实现。
```

---

## P10｜ZYC-09 实现 Artifact / Defense 生成服务与输出页

```text
实现 issue: ZYC-09

目标：
把问答、对比和项目画像变成可交付成果。

请完成：
1. 新增：
   - `api/routers/project_artifacts.py`
   - `api/project_artifact_service.py`
   - `open_notebook/project_os/artifact_service.py`
   - `open_notebook/project_os/defense_service.py`
   - `open_notebook/agents/synthesis_agent.py`
   - `open_notebook/agents/defense_coach_agent.py`
   - `commands/artifact_commands.py`
2. 实现前端：
   - `/dashboard/projects/[projectId]/outputs/page.tsx`
   - `artifact-list.tsx`
   - `artifact-editor.tsx`
   - `artifact-template-picker.tsx`

第一阶段必须支持的产物：
- 项目综述
- 差异报告
- 答辩提纲
- 评委问题清单
- 问答卡片

实现要求：
- 允许从 thread / compare result / overview 三类输入生成
- 产物记录必须带 `created_by_run_id`
- markdown 存储
- source refs 保留下来

验收标准：
- 至少 3 类产物可以生成
- 至少 1 类支持从问答一键生成
- 至少 1 类支持从 compare 结果生成

先输出：
- artifact 数据流设计
- 哪些模板会先做
- 产物页面如何避免过度复杂
然后再实现。
```

---

## P11｜ZYC-10 实现 Memory Center 与长期记忆治理

```text
实现 issue: ZYC-10

目标：
把长期记忆做成显式、可审查、可编辑的系统能力。

请完成：
1. 新增：
   - `api/routers/project_memory.py`
   - `api/project_memory_service.py`
   - `open_notebook/memory_center/powermem_adapter.py`
   - `open_notebook/memory_center/memory_policy.py`
   - `open_notebook/memory_center/memory_writer.py`
   - `open_notebook/memory_center/memory_resolver.py`
   - `open_notebook/agents/memory_curator_agent.py`
2. 前端：
   - `/dashboard/projects/[projectId]/memory/page.tsx`
   - `memory-list.tsx`
   - `memory-card.tsx`
   - `memory-review-dialog.tsx`
   - `memory-conflict-panel.tsx`
3. 接口：
   - `GET /api/projects/{projectId}/memory`
   - `PATCH /api/projects/{projectId}/memory/{memoryId}`
   - `DELETE /api/projects/{projectId}/memory/{memoryId}`
   - `POST /api/projects/{projectId}/memory/rebuild`

实现要求：
- 第一版即使没有完全接上真实 PowerMem，也要先建立 adapter 层
- memory policy 要写清：
  - 有证据的稳定事实可入长期记忆
  - 用户确认的偏好/决策可入长期记忆
  - 未确认内容必须是 `draft`
- 状态支持：
  - `draft`
  - `accepted`
  - `frozen`
  - `deprecated`

验收标准：
- memory 页面能列出记忆
- 能接受/编辑/删除
- 每条长期记忆有 `source_refs`

先输出：
- 你准备如何设计 adapter，避免后续替换成本高
- memory policy 最小实现规则
- 前端如何展示不同状态
然后再实现。
```

---

## P12｜ZYC-11 实现最小可用 Harness：router / planner / skill registry / run trace

```text
实现 issue: ZYC-11

目标：
把系统升级成有 control plane 的 agent 产品，而不是一堆 service 的集合。

请完成：
1. 新增：
   - `open_notebook/agent_harness/router.py`
   - `open_notebook/agent_harness/planner.py`
   - `open_notebook/agent_harness/skill_registry.py`
   - `open_notebook/agent_harness/run_manager.py`
   - `open_notebook/agent_harness/context_packer.py`
   - `open_notebook/agent_harness/trace_store.py`
   - `open_notebook/agent_harness/guardrails.py`
2. 新增 run API：
   - `api/routers/project_runs.py`
   - `api/project_run_service.py`
3. 前端：
   - `/dashboard/projects/[projectId]/runs/page.tsx`
   - `run-list.tsx`
   - `run-detail.tsx`
   - `step-timeline.tsx`
   - `tool-call-card.tsx`

第一阶段最小 skill 集：
- `answer_with_evidence`
- `build_project_overview`
- `compare_sources`
- `generate_artifact`
- `write_project_memory`

实现要求：
- 不是所有请求都要复杂 planning
- simple ask 直接走 router -> evidence skill 即可
- ask/compare/artifact/memory rebuild 都要留下 `run_id`
- trace 至少包括：
  - input
  - selected skill
  - tool calls
  - evidence reads
  - memory writes
  - outputs
  - failures

验收标准：
- runs 页面可看到 run 列表
- 进入某个 run 可看 step timeline
- ask 和 compare 至少两类任务有 trace

先输出：
- 你准备怎样把新 harness 挂接到现有 service，而不是推倒重写
- skill registry 最小设计
- trace 数据结构
然后实现。
```

---

## P13｜ZYC-12 Demo 数据、评测钩子、稳定性与比赛版打磨

```text
实现 issue: ZYC-12

目标：
把“能开发”变成“能演示、能参赛”。

请完成：
1. 准备 demo 数据与说明：
   - 放到 `examples/` 下
   - 新增 `docs/demo-script.md`
2. 新增：
   - `commands/eval_commands.py`
   - `open_notebook/agent_harness/evaluator_hooks.py`
3. 增加简版后台页：
   - `/admin/evals`
   - `/admin/jobs`
4. 统一产品文案、命名、入口，让比赛版以“智研舱”为主
5. 增加失败提示、重试提示、demo 引导

最小 eval 先做：
- evidence faithfulness
- compare consistency
- memory source coverage

验收标准：
- 能用 demo 项目在 3 分钟内演示导入/总览/提问/证据/对比/输出闭环
- 有最小评测命令或页面入口
- README/首页文案已切换到新产品叙事

硬约束：
- 不追求复杂后台
- 不追求多租户
- 不做花哨动画

先输出：
- demo 数据包结构
- 最小 eval 如何实现
- 需要改哪些文案与入口
然后再开始。
```

---

## 1. 每次 issue 完成后，继续追加的固定 prompt

```text
请不要结束在“代码已修改”。

现在继续完成这 4 件事：
1. 运行与当前改动直接相关的测试 / lint / 构建检查
2. 把结果写成 Summary / Files Changed / Validation / Known Gaps 四段
3. 如果有 trade-off，明确说明为什么这样做
4. 如果当前 issue 已完成，请指出下一 issue 最合理的切入文件
```

---

## 2. 若 Codex 开始失控时，使用这个收束 prompt

```text
暂停扩散实现范围。

只保留当前 issue 的最小闭环，删除或回退以下类型的额外改动：
- 与当前 issue 无关的大范围重命名
- 第二套基础设施
- 额外 provider / model 接入
- 与当前 issue 无关的 UI 美化
- 无验收价值的抽象层

然后输出：
- 当前 issue 的最小可交付版本还差什么
- 你准备保留哪些改动
- 你准备回退哪些改动
等我确认后再继续。
```

---

## 3. 若要让 Codex 做“补测试”，使用这个 prompt

```text
不要改业务功能，只为当前 issue 补测试与验证。

要求：
- 优先补最有价值的单测 / 集成测试
- 如果某些地方暂时不易测试，增加最小 demo 脚本或 mock
- 列出哪些核心路径已经被覆盖，哪些还没有
- 不做无意义的快照堆砌
```
