# aotutest → Agent 测评 / LLM 测试 全栈平台 · 完整升级方案

> 版本 v1.0 ｜ 2026-08-06 ｜ **✅ 已审批 · 执行中（Phase A 进行中）**
> 配套详档：`docs/eval-platform-benchmark.md`（9 个开源项目横向对标）、`docs/agent-eval-roadmap.md`（分阶段路线图）、公众号《多Agent协作测试系统实战》分析（benchmark §3）。
> 用户已于 2026-08-06 批准「按 A→B→C 全量」推进，按 §6 顺序批量交付。截至本批次：Phase A·**A2（租户自有模型/出域隔离）** 与 **A4（全局/跨数据集榜单）** 已落地并通过测试。

---

## 0. 一句话目标与红线

- **目标**：把 aotutest 从「传统自动化测试平台」升级为「agent 测评 + LLM 测试的全栈平台」，传统自动化（Selenium/API/性能/安全）退居辅舱。
- **红线（不可妥协）**：
  1. 评测舱与现有 `testcase/testsuite` 模型**完全解耦**，不污染存量客户数据；
  2. 所有新能力以 `TenantFeature` 闸门接入，**无超级读者**（平台管理员亦非跨租户读者）；
  3. **数据不出域**：LLM 调用一律走租户自有 `AIModelConfig`，未订阅租户零外送（离线启发式降级）；
  4. 不重造轮子、不照搬重基建（坚持 Django+Postgres，不引 ClickHouse）。

---

## 1. 现状盘点（已落地，本方案在此基础上补齐）

| 模块 | 状态 | 说明 |
|---|---|---|
| Phase 0 多租户功能开关 | ✅ | `apps.tenant_features`，fail-closed 门禁 |
| Phase 1 底座契约 | ✅ | `HasTenantFeature` + `TenantAwareViewSetMixin(staff_has_full_access=False)` |
| M2 数据集管理 | ✅ | `EvalDataset` / `EvalCase`（含 `is_edge` 边缘用例标记） |
| M3 评估引擎 | ✅ | 规则 + LLM-Judge + 6 类指标（offline 降级）+ **HITL 人机复核门** |
| M4 Trace 步骤级观测 | ✅（后端） | `EvalTrace` / `EvalTraceStep`，回放 + 失败归因（规划弱 vs 工具错） |
| 红队 REDTEAM | ✅ | PII 泄漏 / 越狱-注入 / 毒性 离线扫描 |
| M5 报告看板 | ✅（后端） | `dataset.report`：趋势 + 聚合（latest/best/worst/avg）+ 维度汇总 |

> **当前缺口**：M5 **前端**看板、Phase3 智能体辅舱、Phase4 门禁/可观测、租户自有模型、数据集版本化+Diff、全局榜单。

---

## 2. 开源对标结论（9 个项目，精炼）

完整横向对比表见 `docs/eval-platform-benchmark.md` §1/§2。可借鉴要点：

| 范式 | 代表项目 | 我们借鉴了什么 / 还差什么 |
|---|---|---|
| 评估引擎 | DeepEval(30+指标)、Giskard(强制 reason) | ✅ 已落地 6 类指标 + HITL 复核门；指标库仍可继续扩 |
| 可观测 / Trace | Langfuse、Arize Phoenix、Opik | ✅ 已落地 M4 Trace；Opik 生产监控看板 ✅ 已落地 M5 后端 |
| 测试 / 红队 / CI | promptfoo(红队+CI门禁)、Giskard(扫描) | ✅ 红队已落地；**CI 质量门禁待做** |
| 全栈编排 | One-Eval(NL2Eval+人机协同)、Inspect AI(扩展式评测) | ✅ HITL 已落地；`grader_type` 插件架构已对齐；Phase3 编排待做 |
| 明确不抄 | Langfuse 的 ClickHouse 重基建 | 坚持 Django+Postgres，不引 ClickHouse |

**对标九强**：promptfoo、DeepEval、Langfuse、One-Eval(北大)、Giskard、Ragas、Opik(Comet)、Arize Phoenix、Inspect AI(UK AISI)。

---

## 3. 公众号文章启示（直接映射）

文章《多Agent协作测试系统实战》核心 = **四角色分工 + 渐进四步 + 错误传播防护**。与本方案映射：

| 文章观点 | 本方案落点 |
|---|---|
| 四角色分工（调度 / 用例生成 / 执行调度 / 结果分析） | Phase 3 把「生成 / 执行 / 分析」拆成独立 Agent，避免单 Agent 上下文稀释 |
| 渐进四步法 | 落地顺序：先用例生成 Agent → 再执行 → 再分析 → 最后调度（每步独立交付价值） |
| 错误传播（用例预期错 → 分析误报） | 分析端合理性校验 + **HITL 复核门**（✅ 已落地） |
| 中间格式必须稳定 | `EvalCase` schema 是系统「中间格式」，冻结演进、下游强依赖 |

> 文章结论：**对我们升级「高度有帮助」（直接相关）**——它提供了 Phase 3 的可落地架构蓝图与必须防范的风险。

---

## 4. 目标架构（终态）

```
                ┌──────────────────────────────────────────────┐
                │  共享身份/多租户底座（复用 aotutest）              │
                │  auth · RBAC · Organization · TenantFeature      │
                └───────────────┬────────────────────────────────┘
                                │ 统一鉴权 + 功能开关门禁
      ┌─────────────────────────┼─────────────────────────┐
      ▼                         ▼                         ▼
┌──────────────┐      ┌──────────────────────┐    ┌──────────────────┐
│ 传统自动化舱  │ (辅) │  Agent 测评/LLM 测试   │(主)│ 智能体自动化辅舱  │(辅,Phase3)
│ Selenium/API │      │  评测舱（eval-native）  │    │ 生成/执行/分析Agent│
│ 性能/安全     │      │ Dataset·Grader·Trace   │    │ 复用执行基础设施  │
│              │      │ Report·REDTEAM·版本化  │    │                  │
└──────────────┘      └──────────┬───────────┘    └──────────────────┘
                                  │
                     ┌────────────┴────────────┐
                     ▼                         ▼
            质量门禁（CI 分数阈值+回归拦截）  可观测（Trace/OTel，M4 奠基）
```

---

## 5. 完整升级路线（三阶段，含交付物 / 验收）

### Phase A —— 评测舱完整性（1–2 周，纯后端可独立验证）
- **A1. M5 前端 Vue 看板**：接 `dataset.report`，趋势折线 + 概览卡片 + 维度表。
  - *验收*：非技术同事能看懂评测报告。
- **A2. AIModelConfig.organization（租户自有模型）**：给 `AIModelConfig` 加 `organization`；LLM 裁判只取本租户激活配置，无则离线降级。
  - *验收*：跨租户 LLM 数据零串扰、零外送（兑现「全栈多租户出域」承诺）。
- **A3. 数据集版本化 + Diff**：`version` 升级为快照（copy-on-write）+ 版本间用例 Diff。
  - *验收*：可回滚、可比对两版差异。
- **A4. 全局 / 跨数据集榜单**：模型排名、维度对比（复用 report 聚合）。
  - *验收*：多数据集横向可比。

### Phase B —— 智能体自动化辅舱（2–3 周）
- **B1. 用例生成 Agent**：需求 / API 文档 → 结构化 `EvalCase` JSON（稳定中间格式）。
- **B2. 复用 aotutest 执行设施**（UiDevice / 执行器）跑生成用例。
- **B3. 分析 Agent**：机械断言 + LLM-Judge + 跨用例模式识别，接 HITL。
- **B4. 保留确定性基线**：agent 负责生成 / 探索，传统脚本作回归基线。
  - *验收*：一条「需求 → 生成 → 执行 → 报告」端到端链路跑通。

### Phase C —— 质量门禁 + 可观测进 CI（1–2 周）
- **C1. CI 质量门禁**：分数阈值 + 回归拦截（复用 report 接口，劣化即红）。
- **C2. Trace 可观测接入**：OTel / Langfuse 风格，M4 已奠基。
- **C3. 评测纳入安全审计基线**。
  - *验收*：提交一个故意劣化的 Prompt / 评测，CI 自动拦截并指出掉哪个指标。

---

## 6. 执行方式（审批后）

- 按 **Phase A → B → C** 顺序推进；每个 Phase 内子项合并到同一次提交，**减少来回、批量交付**。
- 每个 Phase 结束给一次可运行 / 可测试交付（Django 测试 + 本地迁移）。
- 持续坚持：迁移本地生成不入库、零外送降级、租户隔离、不污染传统模型。

---

## 7. 风险与开放问题

- **前端资源**：A1 看板、A3 Diff UI 需前端配合——本期是否排期？
- **A2 迁移**：改 `AIModelConfig` 需迁移，旧平台级配置归属需定（建议默认挂平台组织或各租户）。
- **B 阶段 adapter**：执行基础设施抽象程度决定工作量。
- **红线核查**：每次 PR 自查「是否污染传统模型 / 是否越权 / 是否外送」。

---

## 8. 审批请求

请确认：
1. 方案方向（Phase A / B / C）是否认可？
2. 优先级是否调整（例如先 A2 出域地基，再 A1 看板）？
3. 前端资源（A1 / A3）本期是否纳入？

**审批通过后，我将从你指定的起点开始执行，并按 Phase 批量交付（而非逐项来回）。**
