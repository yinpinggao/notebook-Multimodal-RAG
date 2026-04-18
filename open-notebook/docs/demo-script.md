# 智研舱 Demo Script

用于 `ZYC-12` 的比赛演示文档。

目标是把“能开发”讲成“能演示、能参赛”。

## 1. 演示目标

在 3 分钟内完成一条完整闭环：

1. 打开 demo 项目
2. 做一次证据问答
3. 做一次规则 vs 方案对比
4. 展示一条项目记忆
5. 展示一个答辩相关产物

## 2. 演示前准备

### 2.1 资料准备

导入或预置以下材料：

- `examples/zhiyancang_demo/competition_brief.md`
- `examples/zhiyancang_demo/solution_plan.md`
- `examples/zhiyancang_demo/evidence_brief.md`
- `examples/zhiyancang_demo/judge_focus.md`

建议项目名：

`智研舱 Demo 项目`

### 2.2 页面准备

演示时优先准备这几个页面：

- `/projects`
- `/projects/[projectId]/overview`
- `/projects/[projectId]/evidence`
- `/projects/[projectId]/compare`
- `/projects/[projectId]/memory`
- `/projects/[projectId]/outputs`
- `/projects/[projectId]/runs`

如果管理页已接好，再准备：

- `/admin/evals`
- `/admin/jobs`

## 3. 3 分钟脚本

### 0:00 - 0:20

开场口径：

“智研舱不是一个聊天式知识库，而是一个面向竞赛、科研和项目申报的 Project Memory Copilot。这里所有资料、证据、记忆和产物都挂在同一个项目空间里。”

动作：

- 打开项目列表
- 进入 `智研舱 Demo 项目`

### 0:20 - 0:50

口径：

“先看项目总览。这里不是功能目录，而是项目当前状态。系统会围绕这个项目持续组织证据、对比和产物。”

动作：

- 展示总览页
- 点出资料数量、推荐问题、最近活动

### 0:50 - 1:30

口径：

“接着做证据问答。系统回答时不是只给结论，而是要给出处。”

推荐问题：

- 当前方案覆盖了哪些评分项？
- 为什么这个产品不是普通聊天式知识库？

动作：

- 进入证据页
- 发起问题
- 展示答案和证据卡
- 明确指出 `source_name`、`citation_text`、`internal_ref`

### 1:30 - 2:05

口径：

“再看对比。这里把规则文档和方案说明做结构化分析，不只输出一段总结。”

动作：

- 进入 compare 页
- 选择 `competition_brief.md` 和 `solution_plan.md`
- 展示覆盖项、缺失项、风险项、待确认项

### 2:05 - 2:25

口径：

“项目不是问完就结束。稳定事实会进入项目记忆，而且每条记忆都带来源。”

动作：

- 进入 memory 页
- 展示至少 1 条带 `source_refs` 的记忆

### 2:25 - 2:45

口径：

“最后看输出。系统会把问答和对比沉淀成可以直接用于答辩的材料。”

动作：

- 进入 outputs 页
- 展示答辩提纲、问题卡片或差异摘要

### 2:45 - 3:00

口径：

“如果需要回归评测或排查失败任务，管理页可以看最小 eval 和 jobs 状态。评测先收三条：evidence faithfulness、compare consistency、memory source coverage。”

动作：

- 如果管理页已可用，打开 `/admin/evals` 或 `/admin/jobs`
- 否则直接口述最小评测口径

## 4. 演示中的推荐问题

1. 当前方案覆盖了哪些评分项？
2. 规则文档与方案说明之间还缺什么？
3. 为什么长期记忆必须带 `source_refs`？
4. 如果证据不足，系统应该怎么处理？

## 5. 失败兜底

### 问答较慢

先展示已有证据卡或历史线程，再补一句：

“现场模型速度受环境影响，但证据化回答的结构已经固定下来。”

### compare 未完成

先展示已完成的 compare 结果或说明结构化输出模板，再补一句：

“compare 是异步任务，状态和失败原因会直接展示给用户。”

### 输出未完成

先展示既有产物或说明输出类型，再补一句：

“产物由项目上下文驱动，不是脱离证据单独生成。”

## 6. 统一口径

统一用词不要混：

- 智研舱 / ZhiyanCang
- Project Memory Copilot
- 项目空间
- 证据问答
- 对比
- 记忆
- 输出
- 运行

避免把主叙事说回：

- notebook 工具箱
- 搜索能力集合
- 单轮聊天助手
