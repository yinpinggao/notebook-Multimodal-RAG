# 智研舱功能验收清单（可直接发给 Codex）

## 1. 给 Codex 的总控验收 Prompt

```text
先不要继续开发新功能。请对你刚完成的修改做一轮完整验收。

要求：
1. 先复述本次修改对应的 issue 目标、范围限制、验收标准。
2. 检查当前代码是否真的满足这些验收标准，而不是只看代码是否写完。
3. 运行相关启动、测试、lint、typecheck 或最小验证命令。
4. 输出 changed files，并按“核心改动 / 辅助改动 / 风险改动”分类。
5. 找出当前仍未完成、实现不完整、容易出 bug 的地方。
6. 如果发现问题，先给出修复计划，再修复，再重新验证。
7. 最后明确回答：现在是否可以进入下一个 issue。

输出格式：
- issue goal
- acceptance checklist
- changed files
- checks run
- problems found
- fixes applied
- remaining risks
- ready for next issue: yes / no
```

---

## 2. 通用人工验收清单

### 2.1 基础可运行性
- [ ] 前端可以启动
- [ ] 后端可以启动
- [ ] 当前改动没有导致 import 报错
- [ ] 当前改动没有导致 route 注册失败
- [ ] 页面能正常加载，不出现明显白屏

### 2.2 当前 issue 完成度
- [ ] 当前 issue 的目标已经实现
- [ ] 当前 issue 的范围限制没有被破坏
- [ ] 当前 issue 的验收标准逐条满足
- [ ] 当前 issue 没有偷偷夹带大量无关改动

### 2.3 回归风险
- [ ] 旧页面没有明显被改坏
- [ ] 旧 API 没有明显被改坏
- [ ] 字段命名没有随意变化
- [ ] 空态、报错态、加载态至少有基础处理
- [ ] 没有新增明显不可控的大依赖

---

## 3. 按产品闭环的 Smoke Test

## 3.1 Project / Overview
- [ ] 可以进入 Projects 列表页
- [ ] 可以打开单个 Project
- [ ] Overview 页面可以加载
- [ ] Overview 空数据时不崩
- [ ] Overview 至少能展示摘要或占位内容

## 3.2 Evidence / Ask
- [ ] Evidence 页面可以打开
- [ ] 输入问题后可以返回 answer
- [ ] 返回结果包含 evidence cards 或 citation 区域
- [ ] 推荐追问可以点击
- [ ] 连续提问两次不会直接报错

## 3.3 Compare
- [ ] Compare 页面可以打开
- [ ] 可以选择两个 source
- [ ] 可以发起 compare
- [ ] 可以看到运行状态（queued / running / completed / failed）
- [ ] 可以看到 similarities / differences / conflicts / missing_items 中至少一部分结果

## 3.4 Memory
- [ ] Memory 页面可以打开
- [ ] 可以看到 memory 列表或空态
- [ ] 可以看到 memory 的状态、来源或置信度字段
- [ ] 接受 / 删除 /冻结 之类动作不会直接报错

## 3.5 Outputs
- [ ] Outputs 页面可以打开
- [ ] 可以看到 artifact 列表或空态
- [ ] 可以生成至少一种 artifact
- [ ] 可以查看 artifact 详情
- [ ] regenerate 不会直接报错

## 3.6 Runs
- [ ] Runs 页面可以打开
- [ ] 可以看到至少一条 run 或空态
- [ ] 可以打开 run 详情
- [ ] 可以看到 step / status / output 摘要之一

---

## 4. 按后端接口的最小验收

### 4.1 Projects API
- [ ] GET /api/projects 正常返回
- [ ] POST /api/projects 正常返回
- [ ] GET /api/projects/{projectId}/overview 正常返回
- [ ] 返回字段稳定，不缺关键字段

### 4.2 Ask API
- [ ] POST /api/projects/{projectId}/ask 正常返回
- [ ] 返回 answer
- [ ] 返回 evidence_cards
- [ ] 返回 suggested_followups 或空数组
- [ ] 返回 run_id 或线程标识字段

### 4.3 Compare API
- [ ] POST /api/projects/{projectId}/compare 正常返回
- [ ] 可以查状态
- [ ] 可以拿到结果详情
- [ ] 结果结构稳定

### 4.4 Memory API
- [ ] GET /api/projects/{projectId}/memory 正常返回
- [ ] PATCH / action API 正常返回
- [ ] 错误输入不会把服务打崩

### 4.5 Artifacts API
- [ ] POST /api/projects/{projectId}/artifacts 正常返回
- [ ] GET list 正常返回
- [ ] GET detail 正常返回

### 4.6 Runs API
- [ ] GET /api/projects/{projectId}/runs 正常返回
- [ ] GET run detail 正常返回
- [ ] GET trace 或 steps 正常返回

---

## 5. 给 Codex 的“发现问题就修复” Prompt

```text
请不要进入下一个 issue。先根据刚才的验收结果修复问题。

要求：
1. 只修复本轮验收中发现的问题，不扩需求。
2. 先列出 problems found 和对应修复策略。
3. 再实施修复。
4. 修复后重新运行最小验证。
5. 最后输出：
   - fixes applied
   - checks rerun
   - remaining risks
   - ready for next issue: yes / no
```

---

## 6. 给 Codex 的“准备进入下一个 issue” Prompt

```text
请基于刚才的验收结论，判断当前改动是否已经达到进入下一个 issue 的条件。

要求：
1. 如果还不够，请明确列出必须先补的内容。
2. 如果已经够，请推荐下一个最合理的 issue。
3. 说明为什么这个 issue 应该是下一步，而不是别的 issue。
4. 输出进入下一步前建议保留的 Git checkpoint 提示。

输出格式：
- current status
- blockers
- next recommended issue
- why this next
- checkpoint advice
```

---

## 7. 你自己人工判断“能不能进入下一步”的标准

只有同时满足下面 4 条，才建议进入下一个 issue：

- [ ] 当前 issue 的验收标准基本完成
- [ ] 主链路 smoke test 没有明显断裂
- [ ] 没有 P0 级报错或页面崩溃
- [ ] Codex 已经完成一轮自检 + 修复 + 再验证

如果这 4 条里有 1 条不满足，先修，不要继续堆功能。
