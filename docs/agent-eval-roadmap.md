# aotutest → Agent 测评 / LLM 测试 平台 · 实施路线图（路线三 · 混合演进）

> 版本：v1.0 ｜ 2026-08-03 ｜ 决策已锁定（见 §0）
> 关联文档：`升级方案评审报告.md`（路线权衡与 RACI 来源）

---

## 0. 决策锁定（来自甲方确认）

| 维度 | 决策 |
|---|---|
| 路线 | **路线三：混合演进**（eval-native 评测舱 + 复用 aotutest 身份/多租户底座 + 功能开关解耦） |
| 多租户 | **继续服务多租户**；agent/LLM 能力按租户开通 |
| 架构投入 | **干净架构投入**（评测舱独立、依赖隔离、不污染现有传统模型） |
| 传统自动化 | **彻底转向 agent/LLM 测试**为主；传统自动化作为"辅舱"（保留确定性脚本作回归基线） |

**一句话目标**：以 agent 测评 + LLM 测试 为绝对主线，传统自动化退居辅舱，通过 tenant 功能开关保证"用不到的甲方不被臃肿、不被强制、数据不出域"。

---

## 1. 架构目标态

```
                    ┌─────────────────────────────────────────┐
                    │  共享身份/多租户底座（复用 aotutest）        │
                    │  auth · RBAC · Organization · TenantFeature│
                    └───────────────┬───────────────────────────┘
                                    │ 统一鉴权 + 功能开关门禁
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
  ┌──────────────┐          ┌────────────────────┐      ┌──────────────────┐
  │ 传统自动化舱  │  (辅)    │  Agent 测评 / LLM    │ (主) │  智能体自动化舱   │ (辅)
  │ Selenium/API │          │  评测舱（eval-native）│      │  agent 生成/执行  │
  │ 性能/安全     │          │  Dataset·Grader·Trace│      │  复用执行基础设施 │
  └──────────────┘          └─────────┬──────────┘      └──────────────────┘
                                      │
                          ┌───────────┴────────────┐
                          ▼                        ▼
                  质量门禁（CI）            可观测（Langfuse/OTel）
```

- **评测舱**是新建的 eval-native 模块群（可独立 app 或独立服务），不依赖传统 `testcase/testsuite` 模型。
- **TenantFeature** 是唯一的"能力闸门"，UI/API/计费三重门禁全部基于它。

---

## 2. Phase 0 · 多租户功能开关（✅ 已完成 2026-08-03）

**交付物**（`agent-eval-v2` 分支，`apps/tenant_features/`）：
- `TenantFeature` 模型（`tenant` + `feature_code` + `enabled` + `quota` + `expires_at`），含 `is_active`（过期自动失效）。
- `tenant_has_feature(org, code)` 辅助函数 + `HasTenantFeature` DRF 权限类（严格 fail-closed）。
- `TenantFeatureViewSet`（`/api/tenant-features/features/`）：成员只读本租户状态，租户管理员可开关。
- 回归测试 `tests.py`：**4 tests OK**，覆盖"他租户拒绝 / 无组织拒绝 / 关闭后拒绝"。

**已验证**：`manage.py check` 无问题；迁移 `0001_initial` 已生成。

**下一步（本阶段收尾）**：将 Phase 0 合入主线并推送到演进分支远端，作为后续所有阶段的基底。

---

## 3. Phase 1 · 身份/多租户底座复用边界（2 周）

**目标**：明确评测舱如何消费现有底座，避免耦合泄漏。

| 任务 | 负责角色 |
|---|---|
| 定义评测舱与底座的契约：统一用 `request.user.organization` + `HasTenantFeature` 做门禁，禁止评测舱直连传统表 | 架构/技术负责人 + 多租户权限专家 |
| 把 `TenantFeature` 接入现有 RBAC 文档与前端菜单渲染（用不到的入口不显示） | 平台/前端 |
| 复用现有 `AIModelConfig` 模式做"租户自有模型配置"，确保不订阅 LLM 的租户数据零出域 | 安全/合规 |
| 补 Phase 0 的 admin 开通界面（租户管理员自助开通入口 / 平台侧批量开通） | 平台/前端 |

**里程碑 M1**：任一新评测 API 加上 `HasTenantFeature` 后，未开通租户调用返回 403，且前端入口不可见。

---

## 4. Phase 2 · eval-native 评测舱（核心，4–6 周，单租户先验证）

映射 `agent-testing-handbook` 的 M1–M5，作为新模块群落地（参考 handbook `starter/` 的 `judge.py`/`adapter.py`/`web.py`/184 条数据集）。

| 里程碑 | 内容 | 负责角色 |
|---|---|---|
| M2 数据集管理 | `EvalDataset` 模型（dataset + expected + 边缘用例标记）；导入/版本管理；≥30% 边缘用例 | AI QE / Agent 测试专家 |
| M3 评估引擎 | 评分器框架：规则 / LLM-as-Judge / Agent-as-Judge（四原则 + 无 key 降级）；pass@k / 多维分数 | AI QE |
| M4 Trace 回放 | 适配器把规划/工具步打点成 Trace 存储 + 回放 UI；失败归因（规划弱 vs 工具错） | AI QE + 平台/前端 |
| M5 报告看板 | 评测报告 / 分数趋势 / 质量门禁阈值；零依赖起步，再接现有 reports 舱 | 平台/前端 |

**关键约束（handbook 原则）**：先在**单一甲方**跑满 **≥500 条真实用例**验证需求，再全量推广。绝不在验证前固化平台。

**里程碑 M2–M5 完成 = 评测舱可用**：非技术同事能上传数据集、跑一次评测、看懂报告。

---

## 5. Phase 3 · 智能体自动化"辅舱"（2–3 周）

| 任务 | 负责角色 |
|---|---|
| agent 用例生成：基于需求/代码生成测试用例，人工校准 | AI QE |
| 复用 aotutest 现有执行/设备基础设施（UiDevice / 执行器）跑 agent 生成的测试 | 架构 + 传统自动化 owner |
| **保留确定性脚本作回归基线**，agent 负责生成与探索，不 100% 替传统脚本 | 全体（风险共识） |
| agentic UI 执行（BrowserUse 类）灰度，监控可靠性（目标 ≥85% 再扩大） | AI QE + 运维 |

**里程碑 M6**：一条"需求 → agent 生成用例 → 确定性+agent 混合执行 → 报告"的端到端链路跑通。

---

## 6. Phase 4 · 质量门禁 + 可观测进 CI（1–2 周）

| 任务 | 负责角色 |
|---|---|
| 扩展 `.github/workflows/ci.yml`：新增 eval 维度质量门禁（分数阈值 + 回归拦截，复用 handbook `agent-eval.yml` 的"门禁自检"思路） | 运维 + AI QE |
| 生产可观测：Langfuse/OTel 接入 Trace；失败用例回流闭环 | 运维 + AI QE |
| 评测结果并入现有安全审计基线（新增 eval 维度扫描项） | 安全/合规 |

**里程碑 M7**：提交一个故意劣化的 Prompt/评测，CI 自动拦截并指出掉的是哪个指标。

---

## 7. 跨阶段横切关注点

- **安全/合规**：LLM 调用一律走租户自有 `AIModelConfig`；未开通 LLM 的租户数据**绝不**外送；评测数据纳入现有审计基线。
- **多租户**：所有新能力以 `TenantFeature` 闸门接入，无例外。
- **成本**：`quota` 字段支撑按调用计费；agent 自动化降低"脚本编写"人工成本，但保留确定性基线控制不稳定成本。
- **不臃肿**：评测舱独立 app/服务、依赖隔离、不污染 `testcase/testsuite` 模型。

---

## 8. 角色分工（RACI，沿用评审报告 §9）

| 角色 | 主导阶段 |
|---|---|
| 架构/技术负责人 | 总体裁定、Phase 1 契约 |
| 多租户/权限专家 | Phase 0/1（TenantFeature、RBAC 升级） |
| AI QE / Agent 测试专家 | Phase 2/3/4（评测引擎、数据集、Grader、门禁） |
| 平台/前端 | Phase 1/2（舱式入口、看板） |
| 交付/PM | 排期、客户影响、迁移 |
| 安全/合规 | LLM 出域、审计基线延续 |
| 运维/部署 | Phase 4（CI 门禁、可观测、部署） |

---

## 9. 里程碑与时间线（建议）

| 周次 | 里程碑 |
|---|---|
| W1–2 | Phase 1 底座契约 + 功能开关接入前端 |
| W3–8 | Phase 2 评测舱 M2–M5（单租户验证 ≥500 用例） |
| W9–11 | Phase 3 辅舱端到端链路 |
| W12–13 | Phase 4 门禁 + 可观测进 CI |
| 全程 | 安全合规评审穿插 |

---

## 10. 下一步 30 天行动（立即启动）

1. **合入 Phase 0**：将 `agent-eval-v2` 推送到远端演进分支，作为基底。
2. **Phase 1 启动**：架构师出"评测舱与底座契约"文档；前端完成功能开关菜单渲染。
3. **Phase 2 单租户试点**：选一个甲方，用 handbook 脚手架（`starter/`）落地 M2–M3，真实跑 ≥500 用例，验证需求。
4. **安全合规预评审**：明确 LLM 出域边界与租户模型配置方案。

> 注：本路线图与 `升级方案评审报告.md` 配套使用；路线三已为最终决策，不再评估"纯扩充 / 纯新建"。

---

## 11. 实施进度（演进分支 `agent-eval-v2`，基于 `new-main` `8fbf5f6`）

> 提交链路：`8fbf5f6`(new-main) → `0033b4c`(Phase0 功能开关) → 本批次(Phase1 契约 + Phase2 M2/M3/M4 评测舱核心)

| 阶段 | 里程碑 | 状态 | 交付物 |
|---|---|---|---|
| Phase 0 | 多租户功能开关 | ✅ 已完成 | `apps/tenant_features`（TenantFeature + HasTenantFeature fail-closed + 视图集） |
| **Phase 1** | **底座契约**（门禁 + 严格隔离） | ✅ **已落地** | `apps/eval_pod` 所有 API 叠加 `HasTenantFeature(AGENT_EVAL)` 门禁 + `TenantAwareViewSetMixin(staff_has_full_access=False)`；EvalDataset/EvalCase/GraderConfig/EvalRun 全部按 `organization` 隔离，平台管理员亦非"超级读者" |
| **Phase 2 · M2** | **数据集管理** | ✅ **已落地** | `EvalDataset` + `EvalCase`（含 `is_edge` 边缘用例标记、`edge_ratio`/`case_count` 属性） |
| **Phase 2 · M3** | **评估引擎** | ✅ **已落地** | `graders.py`：规则（精确/包含/正则）+ LLM-as-Judge（复用 `AIModelConfig`）+ **无配置/失败确定性降级 `HEURISTIC`（零外送）**；`grade_run` 汇总（含边缘用例通过率）；`EvalRun.run` @action 端到端落库 |
| Phase 2 · M4 | **Trace 步骤级观测** | ✅ **已落地** | `EvalTrace` + `EvalTraceStep`（规划/工具/观察/输出/错误步骤，按 step_index 回放）；`/api/eval/traces/` 存储+检索；失败归因基座（区分「规划弱」vs「工具错」）；租户隔离经 `run__organization` + 越权创建拦截 |
| Phase 2 · M3+ | **红队/安全扫描（REDTEAM）** | ✅ **已落地** | `GraderConfig.grader_type=REDTEAM` + `graders.redteam_grade`：离线启发式扫描 **PII 泄漏 / 越狱-注入企图 / 毒性内容**（零外送），可选 LLM 升级；命中即不通过、默认 PENDING 待复核（对齐 Opik Guardrails + promptfoo/Giskard + Inspect AI elicitation） |
| Phase 2 · M5 | **报告看板（后端聚合）** | ✅ **后端已落地** | `EvalDatasetViewSet.report`：数据集下运行趋势（按时间升序）+ 聚合概览（latest/best/worst/avg）+ 各评分器维度汇总（grader_breakdown）；前端看板（Vue）待接入 |
| Phase A · **A1** | 报告看板（Vue 前端） | ✅ **已落地** | `frontend/src/views/eval/EvalDashboard.vue` + `src/api/eval.js` + 路由 `/eval` + 侧边菜单「Agent 测评」：报告概览 + 全局榜单(A4) + B1 生成 + A3 Diff + 运行详情抽屉(B4 基线/对比·B3 分析·C1 门禁·C2 导出) |
| Phase 3 · B1/B4/B3 | 智能体自动化辅舱 | ✅ **已落地** | `agents.generate_cases`(B1 生成，离线+LLM 升级+降级) / `set_baseline`+`compare`(B4 基线) / `analyze`(B3 分析)；生成用例经 `run` 复用执行设施（B2） |
| Phase 4 · C1/C2/C3 | 门禁 + 可观测进 CI | ✅ **已落地** | `agents.eval_gate`(C1 阈值+回归拦截) / `EvalTraceViewSet.export`(C2 Langfuse/OTel 导出) / `.github/workflows/eval-gate.yml`(C3 CI 门禁) |
| 横切·安全 | 租户自有模型配置（**A2**） | ✅ **已落地** | 给 `AIModelConfig` 加 `organization` 字段 + `for_tenant()` 取数；评测舱 LLM 裁判只取本租户激活配置，平台级配置不被取用，无自有模型租户确定性降级（零外域） |
| Phase A · **A4** | 全局/跨数据集榜单（leaderboard） | ✅ **已落地** | `EvalRunViewSet.leaderboard`：模型排名（按 `model_config.model_name`）+ 数据集排名，复用 report 聚合，严格按租户隔离；`EvalRun.model_config` 溯源字段支撑跨模型比较 |
| Phase A · **A3** | 数据集版本化 + Diff | ✅ **已落地** | `EvalCase.code` 业务键 + `EvalDatasetViewSet.clone_version`（v1→v2 自动 bump，复制用例保留 code）+ `EvalDatasetViewSet.diff`（按 code 对应返回 added/removed/changed/unchanged + 字段级差异）；历史数据无 code 时回退 `case-<id>`；严格租户隔离（对齐 Langfuse datasets / One-Eval DataFlow） |

**本批次质量验证**：
- `apps.eval_pod` 回归测试 **47 tests OK**（45 基线 + 新增 2 项端到端 `EvalEndToEndTest`：劣化版触发 C1 门禁并精确指出 mean_score/pass_rate 掉点 / 等价候选过门禁且基线对比不判回归）。
- `manage.py check` 无问题；Phase B/C/A1 全链路落地。
- 本批次交付：Phase B（B1 用例生成 / B3 分析 / B4 确定性基线 + B2 复用执行设施）+ Phase C（C1 质量门禁 / C2 Trace 导出 / C3 CI 门禁工作流）+ Phase A·**A1 Vue 前端看板**；含 `EvalRun.is_baseline`、`EvalCase.code` 迁移（本地生成不入库）。
- **端到端演示**：`apps/eval_pod/management/commands/demo_eval_flow.py` —— 离线零外送跑通「需求→生成(B1)→评测→基线(B4)→门禁(C1 精确指指标)→分析(B3)→Trace 导出(C2)」，已在开发库实跑验证（演示数据落在独立 `demo-eval` 租户，可安全删除，命令支持 `--clean` 重建）。
- 说明：`apps/requirement_analysis` 自带 4 项测试存在 `core_projects.owner_id` 缺失的历史失败，与本次改动无关（未触碰 Project 模型），不阻塞本次交付。

**工程约定提醒（重要）**：本项目 `.gitignore` 忽略所有 `apps/*/migrations/*`，迁移**本地生成、不入库**（`makemigrations` 后由 syncdb/本地迁移建表）。因此：
- 测试前需本地 `makemigrations`（本项目约定，迁移不入版本库）；
- CI 现有 `makemigrations --check` 在全新 clone 上会因迁移被忽略而潜在失效，建议后续单独立项修复（要么 CI 前置 `makemigrations`，要么改为提交迁移）。
- 本批次仅提交 `apps/eval_pod/` 源码、`backend/settings.py`、`backend/urls.py`、`docs/agent-eval-roadmap.md`，不提交任何迁移文件。

---

## 12. 开源对标与借鉴（2026-08-06 增补）

> 完整分析见 `docs/eval-platform-benchmark.md`。结论：不重造轮子、不照搬重基建；评估引擎指标库借鉴 DeepEval，可观测借鉴 Langfuse 的"层"但用 Django+Postgres 实现（不引 ClickHouse）。

**对标六强**：promptfoo（TS/红队/CI，MIT）、DeepEval（Python/30+ 指标/pytest 风，Apache-2.0）、Langfuse（Next.js+ClickHouse 全栈可观测）、One-Eval（React+Vite+FastAPI+LangGraph，NL2Eval+人机协同+中文基准）、Giskard（Python/agent checks+红队扫描）、Ragas（RAG 专用）。

**公众号《多Agent协作测试系统实战》评估 → 高度相关**：四角色分工（调度/用例生成/执行调度/结果分析）、结果分析=LLM-as-Judge、渐进四步落地、代价（中间格式设计/错误传播/调度单点）。直接细化 M3 与 Phase 3；其"错误传播→需分析端合理性校验+人机复核门"为我们补足 HITL 的依据。

**我方最该补的四件事（按性价比）**：
1. (A) 丰富 grader 指标库（faithfulness/relevancy/bias/toxicity/tool_correctness/plan_adherence）+ 强制 reason；
2. (B) 人机协同复核门（`EvalResult.review_status`，阻断误报）；
3. (C) 数据集版本化 + Diff；
4. (D) Trace 模型（步骤级观测，M4）。

**红队/安全维度**作为独立评测类型（`kind=REDTEAM`）单独立项，借鉴 promptfoo/Giskard。

---

## 13. 修订后的分阶段计划（融入对标借鉴）

| 阶段 | 里程碑 | 借鉴来源 | 状态 |
|---|---|---|---|
| Phase A · **A3** | 数据集版本化 + Diff | promptfoo/DeepEval/One-Eval | ✅ 已落地 |
| Phase 2 · M3+ | **指标库扩充**（faithfulness/relevancy/bias/toxicity/tool_correctness/plan_adherence，全 offline 降级）+ **强制 reason** | DeepEval / Giskard | ✅ 已落地 |
| Phase 2 · M3+ | **人机协同复核门**（review_status + reviewer，阻断误报） | One-Eval / Giskard | ✅ 已落地 |
| Phase 2 · M4 | Trace 模型（步骤级观测/回放，Django+Postgres） | Langfuse / One-Eval | ✅ 已落地（回放 UI 经 A1 看板 + C2 导出） |
| Phase 2 · M5 | 多维报告 / 模型排名 / 趋势 | One-Eval / Langfuse | ✅ 已落地（含 A1 Vue 前端看板） |
| Phase 2 · 安全 | 红队评测类型（kind=REDTEAM，越狱/泄漏扫描） | promptfoo / Giskard | ✅ 已落地（offline 启发式优先，可选 LLM 升级） |
| Phase 3 | 多 Agent 编排（生成/执行/分析 拆分，按文章四步法渐进） | 公众号文章 | ✅ 已落地（B1 生成 / B4 基线 / B3 分析 / B2 复用执行设施） |
| Phase 4 | CI 质量门禁（分数阈值 + 回归拦截 + 安全 PR 审查） | promptfoo / DeepEval | ✅ 已落地（C1 门禁 / C2 导出 / C3 `eval-gate.yml`） |
| 横切 | `AIModelConfig` 加 `organization`（租户自有模型，彻底隔离出域） | — | ✅ 已落地（见 A2） |

**设计原则（写入 Phase 3）**：① 分工提升专注度（文章）；② 中间格式（`EvalCase` schema）必须稳定；③ 错误传播防护 = 分析端合理性校验 + 人机复核门；④ 所有 LLM 指标必须有 offline/HEURISTIC 降级，保证未订阅租户零出域。
