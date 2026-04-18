# 智研舱 Codex 可执行 Issue 列表 v1

作者：OpenAI GPT-5.4 Pro  
日期：2026-04-18

---

## 0. 使用方式

这份文档是把《智研舱 PRD + 页面结构图 + 后端模块拆分清单》继续下钻成 **Codex 可以按顺序执行的 backlog**。

建议使用方法：

1. **一次只让 Codex 做 1 个 issue**
2. 每个 issue 独立开分支，例如 `feat/zyc-05-evidence-qa`
3. 每次完成后先人工验收，再进入下一个 issue
4. 所有 issue 都遵守：
   - 不重写现有 `visual_rag / seekdb / jobs/worker`
   - 不引入第二套任务队列
   - 优先复用现有 `api/*_service.py + commands/*.py + worker` 风格
   - 所有新增长期记忆必须带 `source_refs`
   - 所有新增产物必须能追溯到 `run_id`

---

## 1. 总体开发顺序

```text
Phase 0  仓库指令与脚手架
  ZYC-00 -> ZYC-01 -> ZYC-02

Phase 1  项目空间与统一问答主线
  ZYC-03 -> ZYC-04 -> ZYC-05 -> ZYC-06

Phase 2  项目画像 / 对比 / 输出
  ZYC-07 -> ZYC-08 -> ZYC-09

Phase 3  记忆 / Harness / Runs
  ZYC-10 -> ZYC-11

Phase 4  比赛版打磨
  ZYC-12
```

---

## 2. Issue 总表

| ID | 标题 | Phase | 依赖 | 产出 |
|---|---|---|---|---|
| ZYC-00 | 新增 AGENTS.md 与 docs 导航骨架 | 0 | 无 | Codex 可持续施工的仓库说明 |
| ZYC-01 | 建立 Project Workspace 路由与命名别名层 | 0 | ZYC-00 | `projects/*` 新页面骨架 |
| ZYC-02 | 新增领域模型与统一响应 schema | 0 | ZYC-00 | Project / Evidence / Run / Artifact 基础类型 |
| ZYC-03 | 实现项目列表页与项目总览页骨架 | 1 | ZYC-01, ZYC-02 | 能从项目入口进入新产品主线 |
| ZYC-04 | 实现项目 CRUD 与 overview 聚合 API | 1 | ZYC-02 | `/api/projects*` 与总览接口 |
| ZYC-05 | 实现统一证据问答服务与 evidence card schema | 1 | ZYC-02, ZYC-04 | `/ask` + 统一返回格式 |
| ZYC-06 | 实现证据工作台前端与线程体验 | 1 | ZYC-03, ZYC-05 | 可提问、追问、看证据 |
| ZYC-07 | 实现结构化抽取、source profile 与 overview rebuild job | 2 | ZYC-04 | 项目画像自动生成 |
| ZYC-08 | 实现 Compare 服务、API、页面与导出 | 2 | ZYC-07 | 文档差异分析闭环 |
| ZYC-09 | 实现 Artifact/Defense 生成服务与输出页 | 2 | ZYC-05, ZYC-08 | 综述/答辩提纲/问题卡片 |
| ZYC-10 | 实现 Memory Center 与长期记忆治理 | 3 | ZYC-07, ZYC-09 | 项目记忆可见可管 |
| ZYC-11 | 实现最小可用 Harness：router/planner/skill registry/run trace | 3 | ZYC-05, ZYC-10 | Agent 产品感和可解释性 |
| ZYC-12 | Demo 数据、评测钩子、稳定性与比赛版打磨 | 4 | 前面全部 | 比赛演示版本 |

---

## 3. Issue 详细说明

---

### ZYC-00｜新增 AGENTS.md 与 docs 导航骨架

**目标**  
让 Codex 在后续长任务中有统一的仓库规则、命名规范和开发边界。

**建议改动文件**
- `AGENTS.md`（新增，仓库根目录）
- `docs/product-prd.md`
- `docs/architecture.md`
- `docs/routes.md`
- `docs/apis.md`
- `docs/memory-policy.md`
- `README.dev.md` 或 `MAINTAINER_GUIDE.md`（仅增加索引链接，不重写）

**必须写进 AGENTS.md 的内容**
- 产品新名字：智研舱 / Project Memory Copilot
- 当前代码底座：保留 Open Notebook + Visual RAG 能力层
- 当前目标：按项目工作流组织，不再按 notebooks/search/vrag 平铺
- 代码组织约束
- 禁止事项
- 每次任务必须更新哪些文档
- 每次提交必须做的验证动作

**验收标准**
- 新增 `AGENTS.md`
- `docs/` 下至少有 5 个文档骨架
- 文档之间相互链接，不是空文件
- 没有修改业务逻辑
- 项目能正常启动

**不做**
- 不改任何 API 逻辑
- 不改数据库表
- 不改前端业务页面

**建议验证**
- 文档链接检查
- 基础 lint 或已有测试不报错

---

### ZYC-01｜建立 Project Workspace 路由与命名别名层

**目标**  
先把产品前台命名从 “notebook 工具” 变成 “project 工作台”，但底层可先不重构数据模型。

**建议改动文件**
- `frontend/src/app/(dashboard)/projects/page.tsx`
- `frontend/src/app/(dashboard)/projects/new/page.tsx`
- `frontend/src/app/(dashboard)/projects/[projectId]/layout.tsx`
- `frontend/src/app/(dashboard)/projects/[projectId]/overview/page.tsx`
- `frontend/src/app/(dashboard)/projects/[projectId]/evidence/page.tsx`
- `frontend/src/app/(dashboard)/projects/[projectId]/compare/page.tsx`
- `frontend/src/app/(dashboard)/projects/[projectId]/memory/page.tsx`
- `frontend/src/app/(dashboard)/projects/[projectId]/outputs/page.tsx`
- `frontend/src/app/(dashboard)/projects/[projectId]/runs/page.tsx`
- 现有导航组件（把主入口从 notebooks 调整为 projects）
- 必要时新增 `frontend/src/lib/project-alias.ts`

**实现要求**
- 第一阶段允许 `projectId` 暂时映射到现有 notebook id
- 页面可先用 mock / placeholder data，只要布局和路由成立
- `/vrag` 不删除，但不再主导航主打
- 新导航文案使用：项目、证据、对比、记忆、输出、运行

**验收标准**
- 新路由可访问
- 主导航能进入 `/dashboard/projects`
- 项目内布局能切换六个主标签
- 不破坏现有 notebook 页面

**不做**
- 不做真实项目 CRUD
- 不做真实问答
- 不删旧路由

---

### ZYC-02｜新增领域模型与统一响应 schema

**目标**  
在后端先把新产品的数据骨架立起来，让后续 API 和前端有稳定 contract。

**建议改动文件**
- `open_notebook/domain/projects.py`
- `open_notebook/domain/evidence.py`
- `open_notebook/domain/memory.py`
- `open_notebook/domain/artifacts.py`
- `open_notebook/domain/runs.py`
- `api/schemas/`（如果仓库已有 schema 目录则复用，否则新增）
- `docs/apis.md`
- `docs/architecture.md`

**至少定义这些 schema**
- `ProjectSummary`
- `ProjectOverviewResponse`
- `EvidenceCard`
- `AskResponse`
- `CompareSummary`
- `ArtifactRecord`
- `MemoryRecord`
- `AgentRun`
- `AgentStep`

**实现要求**
- 优先用当前仓库已有的类型系统 / pydantic 风格
- 字段命名以 PRD 为准
- `EvidenceCard` 必须包含 `source_name/source_id/page_no/excerpt/citation_text/internal_ref`
- `MemoryRecord` 必须包含 `source_refs/status/confidence`
- `ArtifactRecord` 必须包含 `created_by_run_id`

**验收标准**
- 能在后端 import 这些 schema
- 新增最小单元测试或 schema snapshot
- `docs/apis.md` 写明这些 response contract

**不做**
- 不做数据库迁移
- 不做真实 service 逻辑

---

### ZYC-03｜实现项目列表页与项目总览页骨架

**目标**  
让用户先从“项目”进入，而不是先看到技术功能入口。

**建议改动文件**
- `frontend/src/app/(dashboard)/projects/page.tsx`
- `frontend/src/app/(dashboard)/projects/[projectId]/overview/page.tsx`
- `frontend/src/components/projects/project-card.tsx`
- `frontend/src/components/projects/project-overview-header.tsx`
- `frontend/src/components/projects/topic-cluster-card.tsx`
- `frontend/src/components/projects/risk-list-card.tsx`
- `frontend/src/components/projects/timeline-card.tsx`

**页面要求**
- 项目列表页：项目卡片、新建按钮、demo 项目入口、最近活动占位
- 项目总览页：项目摘要、资料统计、主题、风险、时间线、推荐问题、最近产物

**实现要求**
- 第一版可以先读取 mock API 或 placeholder fetch
- 组件要按后续真实 API 可替换的方式拆分
- 页面上显式使用 “项目空间 / Project Workspace” 文案

**验收标准**
- 页面样式完整
- 组件拆分清晰
- 后续接 API 不需要推倒重写

**不做**
- 不接真实后端 overview
- 不做复杂交互状态

---

### ZYC-04｜实现项目 CRUD 与 overview 聚合 API

**目标**  
把项目入口从假数据升级为真实后端接口。

**建议改动文件**
- `api/routers/projects.py`
- `api/project_workspace_service.py`
- `api/project_overview_service.py`
- 可能需要的持久化层适配文件
- 相关测试文件

**需要提供的接口**
- `GET /api/projects`
- `POST /api/projects`
- `DELETE /api/projects/{projectId}`
- `GET /api/projects/{projectId}/overview`
- `POST /api/projects/{projectId}/overview/rebuild`（先返回 queued 也可以）

**实现要求**
- 第一阶段允许复用 notebook 作为底层实体
- 提供 project alias 映射层，不要求立刻完整迁移数据表
- overview 可以先做聚合占位：source count、artifact count、recent runs、topics/risk 空数组也可
- 返回结构必须遵守 ZYC-02 schema

**验收标准**
- 前端项目页能读到真实项目列表
- overview 页能读到真实接口
- 允许空项目，但结构稳定
- 至少有接口测试或 service 单测

**不做**
- 不做复杂权限
- 不做自动抽取内容

---

### ZYC-05｜实现统一证据问答服务与 Evidence Card schema

**目标**  
把现有 source chat / search / visual_rag 包装成一个统一的 `/ask` 服务。

**建议改动文件**
- `api/routers/project_evidence.py`
- `api/project_evidence_service.py`
- `open_notebook/evidence/evidence_card_service.py`
- `open_notebook/evidence/citation_service.py`
- 必要时 `open_notebook/agent_harness/router.py`（最小版）
- 与现有 `visual_rag`、`source_chat` 交互的适配层

**需要提供的接口**
- `POST /api/projects/{projectId}/ask`
- `GET /api/projects/{projectId}/threads`
- `GET /api/projects/{projectId}/threads/{threadId}`
- `POST /api/projects/{projectId}/threads/{threadId}/followup`

**实现要求**
- `mode=auto` 时自动判断 text / visual / mixed
- 尽量复用现有检索能力，不重写算法
- 输出统一结构：
  - `answer`
  - `confidence`
  - `evidence_cards[]`
  - `memory_updates[]`
  - `run_id`
  - `suggested_followups[]`
- 如果证据不足，答案里明确标注不确定，不要假装确定

**验收标准**
- 至少一条文本问题能走通
- 至少一条视觉问题能走通
- 两种回答都返回统一 evidence card 结构
- 有基本测试或 demo 脚本

**不做**
- 不做复杂 planner
- 不做长期 memory 写入

---

### ZYC-06｜实现证据工作台前端与线程体验

**目标**  
把 `/ask` 能力真正做成产品主界面，而不是后台接口。

**建议改动文件**
- `frontend/src/app/(dashboard)/projects/[projectId]/evidence/page.tsx`
- `frontend/src/app/(dashboard)/projects/[projectId]/evidence/[threadId]/page.tsx`
- `frontend/src/components/evidence/copilot-chat-panel.tsx`
- `frontend/src/components/evidence/evidence-card.tsx`
- `frontend/src/components/evidence/evidence-side-panel.tsx`
- `frontend/src/components/evidence/answer-block.tsx`
- `frontend/src/components/evidence/source-jump-button.tsx`

**布局要求**
- 左侧：线程列表 / 推荐问题
- 中间：聊天与答案
- 右侧：证据卡片 / 来源定位 / run 摘要

**实现要求**
- 支持首问与追问
- 支持流式输出更好；如果仓库已有 SSE 能力则复用，否则先用普通请求
- 证据卡片可点击跳去来源页码/来源详情
- 保留 `run_id` 展示位置，为后续 runs 页面做铺垫

**验收标准**
- 用户能提问、看到答案、看到证据卡
- 能切换线程
- 能从回答跳到来源详情页（哪怕先是占位跳转）

**不做**
- 不做 runs 全量页面
- 不做记忆写入展示

---

### ZYC-07｜实现结构化抽取、Source Profile 与 Overview Rebuild Job

**目标**  
让系统在“提问前”就对资料形成项目画像。

**建议改动文件**
- `open_notebook/evidence/structured_extractor.py`
- `open_notebook/project_os/source_profile_service.py`
- `open_notebook/project_os/overview_service.py`
- `commands/project_commands.py`
- `api/project_overview_service.py`
- 需要的表/集合定义文件
- 测试文件

**至少抽取这些内容**
- topics
- keywords
- terms
- people/orgs
- timeline events
- metrics
- risks
- requirements

**实现要求**
- 优先从已有 source 文本、page summary、image summary 里抽取
- 第一版可以是规则 + LLM 混合抽取
- 支持异步 command：`project.build_overview` 或 `project.extract_facts`
- overview rebuild 完成后能刷新项目总览页

**验收标准**
- 对 demo PDF 能抽出至少 topics/keywords/risks 中的 2 类
- 项目总览页能显示真实抽取结果
- rebuild job 有状态反馈

**不做**
- 不追求所有文件类型一次做全
- 不做复杂图谱可视化

---

### ZYC-08｜实现 Compare 服务、API、页面与导出

**目标**  
把“文档对比”做成显式工作流，而不是依赖 prompt 技巧。

**建议改动文件**
- `api/routers/project_compare.py`
- `api/project_compare_service.py`
- `open_notebook/agents/compare_agent.py`
- `open_notebook/project_os/compare_service.py`
- `commands/compare_commands.py`
- `frontend/src/app/(dashboard)/projects/[projectId]/compare/page.tsx`
- `frontend/src/components/compare/compare-form.tsx`
- `frontend/src/components/compare/compare-summary.tsx`
- `frontend/src/components/compare/diff-table.tsx`
- `frontend/src/components/compare/conflict-list.tsx`

**需要提供的接口**
- `POST /api/projects/{projectId}/compare`
- `GET /api/projects/{projectId}/compare/{compareId}`
- `POST /api/projects/{projectId}/compare/{compareId}/export`

**输出结构**
- `summary`
- `similarities[]`
- `differences[]`
- `conflicts[]`
- `missing_items[]`
- `human_review_required[]`

**实现要求**
- 第一版先支持 `source A vs source B`
- 可优先使用结构化 facts 对比，再回落到摘要对比
- 导出先支持 markdown，不必先做 pdf/docx

**验收标准**
- 至少能对比两份文本型资料
- 页面能展示差异摘要与结构化差异表
- 导出 markdown 可下载/可查看

**不做**
- 不做多文件批量对比
- 不做复杂 diff 可视化动画

---

### ZYC-09｜实现 Artifact / Defense 生成服务与输出页

**目标**  
把问答、对比和项目画像沉淀成可交付成果。

**建议改动文件**
- `api/routers/project_artifacts.py`
- `api/project_artifact_service.py`
- `open_notebook/project_os/artifact_service.py`
- `open_notebook/project_os/defense_service.py`
- `open_notebook/agents/synthesis_agent.py`
- `open_notebook/agents/defense_coach_agent.py`
- `commands/artifact_commands.py`
- `frontend/src/app/(dashboard)/projects/[projectId]/outputs/page.tsx`
- `frontend/src/components/artifacts/artifact-list.tsx`
- `frontend/src/components/artifacts/artifact-editor.tsx`
- `frontend/src/components/artifacts/artifact-template-picker.tsx`

**第一阶段必须支持的产物类型**
- 项目综述
- 差异报告
- 答辩提纲
- 评委问题清单
- 问答卡片

**实现要求**
- 允许从 thread / compare result / overview 三种来源生成产物
- 产物记录必须带 `created_by_run_id`
- 产物内容使用 markdown 存储
- 生成时保留 source refs

**验收标准**
- 用户可以在输出页创建至少 3 类产物
- 至少一种产物可从问答结果一键生成
- 至少一种产物可从 compare 结果生成

**不做**
- 不先做播客音频
- 不先做 docx/pdf 导出

---

### ZYC-10｜实现 Memory Center 与长期记忆治理

**目标**  
把长期记忆从“隐式存在”变成“显式可审查”。

**建议改动文件**
- `api/routers/project_memory.py`
- `api/project_memory_service.py`
- `open_notebook/memory_center/powermem_adapter.py`
- `open_notebook/memory_center/memory_policy.py`
- `open_notebook/memory_center/memory_writer.py`
- `open_notebook/memory_center/memory_resolver.py`
- `open_notebook/agents/memory_curator_agent.py`
- `frontend/src/app/(dashboard)/projects/[projectId]/memory/page.tsx`
- `frontend/src/components/memory/memory-list.tsx`
- `frontend/src/components/memory/memory-card.tsx`
- `frontend/src/components/memory/memory-review-dialog.tsx`
- `frontend/src/components/memory/memory-conflict-panel.tsx`

**需要提供的接口**
- `GET /api/projects/{projectId}/memory`
- `PATCH /api/projects/{projectId}/memory/{memoryId}`
- `DELETE /api/projects/{projectId}/memory/{memoryId}`
- `POST /api/projects/{projectId}/memory/rebuild`

**实现要求**
- 第一版即使未完整接 PowerMem，也要做 adapter 层，避免后续重写 service
- Memory policy 明确：
  - 只有稳定事实或用户确认偏好可以进入长期记忆
  - 未确认内容只能是 `draft`
- 支持状态：
  - `draft`
  - `accepted`
  - `frozen`
  - `deprecated`

**验收标准**
- memory 页面能看到项目记忆列表
- 能接受 / 编辑 / 删除一条记忆
- 每条长期记忆有 `source_refs`

**不做**
- 不做复杂跨用户共享
- 不做自动衰减可视化

---

### ZYC-11｜实现最小可用 Harness：router / planner / skill registry / run trace

**目标**  
把系统从“多个 service 拼接”升级成“有 control plane 的 agent 产品”。

**建议改动文件**
- `open_notebook/agent_harness/router.py`
- `open_notebook/agent_harness/planner.py`
- `open_notebook/agent_harness/skill_registry.py`
- `open_notebook/agent_harness/run_manager.py`
- `open_notebook/agent_harness/context_packer.py`
- `open_notebook/agent_harness/trace_store.py`
- `open_notebook/agent_harness/guardrails.py`
- `api/routers/project_runs.py`
- `api/project_run_service.py`
- `frontend/src/app/(dashboard)/projects/[projectId]/runs/page.tsx`
- `frontend/src/components/runs/run-list.tsx`
- `frontend/src/components/runs/run-detail.tsx`
- `frontend/src/components/runs/step-timeline.tsx`
- `frontend/src/components/runs/tool-call-card.tsx`

**第一阶段最小 skill 集**
- `answer_with_evidence`
- `build_project_overview`
- `compare_sources`
- `generate_artifact`
- `write_project_memory`

**实现要求**
- 不是所有请求都必须 complex planning
- simple ask 可直接走 router -> evidence skill
- 每次 ask / compare / artifact / memory rebuild 都有 `run_id`
- run 记录至少包括：
  - input
  - selected skill
  - tool calls
  - evidence reads
  - memory writes
  - outputs
  - failure

**验收标准**
- runs 页面能看到 run 列表
- 打开 run 可见 step timeline
- 至少 ask 和 compare 两类任务能留下 trace

**不做**
- 不做多 agent 并发调度
- 不做复杂审批流

---

### ZYC-12｜Demo 数据、评测钩子、稳定性与比赛版打磨

**目标**  
把“能开发”变成“能演示、能参赛”。

**建议改动文件**
- `examples/` 下 demo 数据与说明
- `docs/demo-script.md`
- `commands/eval_commands.py`
- `open_notebook/agent_harness/evaluator_hooks.py`
- `/admin/evals` 和 `/admin/jobs` 页面（可简版）
- 首页文案、导航文案、图标和 demo 引导
- 部署脚本或启动说明

**必须补齐**
- demo 项目预置
- 一键演示路径
- 最小评测：
  - evidence faithfulness
  - compare consistency
  - memory source coverage
- job 失败重试与状态提示
- 比赛演示文案统一为“智研舱”

**验收标准**
- 可以用 demo 项目在 3 分钟内演示完整闭环
- 有最小 eval 脚本或管理页入口
- 关键失败场景有清晰提示
- README/文案已从 notebook 主叙事切到 project 主叙事

**不做**
- 不追求大而全的后台
- 不追求复杂多租户

---

## 4. 推荐分支策略

```text
main
  ├─ feat/zyc-00-agents-docs
  ├─ feat/zyc-01-project-routes
  ├─ feat/zyc-02-domain-schemas
  ├─ feat/zyc-03-project-pages
  ├─ feat/zyc-04-project-api
  ├─ feat/zyc-05-evidence-service
  ├─ feat/zyc-06-evidence-ui
  ├─ feat/zyc-07-overview-extraction
  ├─ feat/zyc-08-compare-flow
  ├─ feat/zyc-09-artifact-output
  ├─ feat/zyc-10-memory-center
  ├─ feat/zyc-11-harness-runs
  └─ feat/zyc-12-demo-evals-polish
```

---

## 5. 给 Codex 的统一验收模板

每个 issue 完成后，都要求 Codex 在回复里给出固定格式：

```text
[Summary]
- 本次完成了什么

[Files Changed]
- 关键文件列表

[Why]
- 为什么这样改，和现有仓库如何兼容

[Validation]
- 跑了哪些测试 / lint / 手动验证

[Known Gaps]
- 还没做什么
- 下一 issue 的前置条件是否满足
```

---

## 6. 不建议合并的 issue

下面这些不要让 Codex 一次做太多，否则容易失控：

- 不要把 ZYC-05 和 ZYC-11 合并
- 不要把 ZYC-07、ZYC-08、ZYC-09 一次性合并
- 不要把 Memory Center 和 Harness 同时大改
- 不要在 ZYC-03 阶段就要求全量真实 API

---

## 7. 最终建议

真正给 Codex 下任务时，遵守一句话：

> **一次一个 issue；先 contract，再 service，再 UI；每一步都可跑、可看、可回退。**
