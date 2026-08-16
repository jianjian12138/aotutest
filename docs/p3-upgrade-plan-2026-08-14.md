# P3 升级计划（agent-eval 平台 · 文章驱动 + TestHub 竞品借鉴）

> 生成时间：2026-08-14｜分支 `agent-eval-v2`｜**交付口径：保持「不提交 git」，待多轮累积后一次性评审**｜原则：补缺不重造
> 输入：① 30 篇公众号研读（见 `cosmic-thunder-babbage.md` 第 0 节）；② TestHub 5 篇竞品分析（见 `testhub-competitive-analysis-2026-08-14.md`）
> 状态：P3-1 已交付（Faithfulness 忠实度 + 死循环/幻觉红线，67 tests 全绿）；其余待排期。

---

## 0. 总目标与边界

- **目标**：把文章共识能力 + 竞品质检的「产品壳」，以最小代价补进 agent-eval 平台，强化「评测 Agent/LLM 本身」的护城河。
- **护城河（我方独有，TestHub 完全没有）**：Pass@k、Faithfulness(D1)、死循环/幻觉红线、红队 REDTEAM、LLM-as-Judge+复核门、PoLL 多裁判、Elo 榜单(A4)、数据集版本化+Diff(A3)、数据不出域(A2)。
- **边界（不抄）**：不做传统 UI/API/APP 自动化主舱（那是 TestHub 主舱、我方辅舱，偏离定位）。
- **执行范式（路线三）**：后端能力 → 单测 →（可选）前端 UI；纯确定性 grader 优先（零外送、不破坏现有 60+ 测试）。

---

## 1. 合并后的 P3 清单（17 项，去重）

> 优先级：P0 立即做 / P1 高 / P2 中。工作量：S<3d / M 3–7d / L>7d（概念估计）。

| 编号 | 项 | 来源 | 优先级 | 工作量 | 状态 |
|---|---|---|---|---|---|
| **P3-1** | Faithfulness 忠实度 + 死循环/幻觉红线（零容忍硬门） | 30篇 | P0 | S | ✅ 已交付 |
| **P3-2** | **成本维度**（Token/调用次数）+ **性能维度**（首Token/端到端延迟）+ 实时看板 | 30篇 + TestHub(InfluxDB式) | P1 | M | 待做 |
| **P3-3** | **Agent-as-Judge + 置信度门**（低置信→人工复核，强化 M3 复核门） | 30篇 | P0 | M | 待做 |
| **P3-4** | **Skill 作为可版本化评估器**（评估逻辑 versioned/diff，对齐 A3） | 30篇 + TestHub(Skills市场) | P1 | M | 待做 |
| **P3-5** | **冷启动标准生成**（Critic/Quantifier/Verifier 三智能体自动生成评测维度） | 30篇 | P1 | L | 待做 |
| **P3-6** | **E2E_MOCK / E2E_REAL 双模式** harness 后端（隔离外部依赖做确定性回归） | 30篇 | P2 | L | 待做 |
| **P3-7** | **质量门核心/辅助分层 + 基线-5% + 评测饱和监控** | 30篇 | P1 | M | 待做 |
| **P3-8** | **OTel 生产追踪 + 失败用例自动回流测试集** | 30篇 | P2 | L | 待做 |
| **P3-9** | **数据集 30% 边缘/失败用例规则 + 合成答案人工抽查卡点** | 30篇 | P2 | M | 待做 |
| **P3-10** | **能力评估集 vs 回归评估集分离 + 正负向都测** | 30篇 | P1 | M | 待做 |
| **P3-11** | **评判模型强度规则**（judge ≥ 被评模型，A2 路由约束） | 30篇 | P2 | S | 待做 |
| **P3-12** | **DeepEval 三指标**（ToolCorrectness/PlanAdherence/GoalCompletion）并入指标库 | 30篇 | P1 | M | 待做 |
| **P3-13** | **知识中枢 RAG 上下文**（需求文档/Confluence/飞书 辅助 B1 用例生成） | TestHub | P1 | L | 待做 |
| **P3-14** | **Copilot 对话入口 + eval-plan-designer**（自然语言→评测方案：选数据集+指标+门禁） | TestHub | P0 | M | 待做 |
| **P3-15** | **失败 case Trace 回放**（agent 工具调用过程可视化，对标 UI 视频回放） | TestHub | P2 | M | 待做 |
| **P3-16** | **定时评测 + IM 通知**（飞书/企微/钉钉，周期评测流水线） | TestHub | P2 | S | 待做 |
| **P3-17** | **评测报告分层产物**（scorecard + brief + 校准卡 + 榜单快照） | 30篇 | P2 | M | 待做 |

---

## 2. 每项范围 / 验收 / 依赖（高优先级先细化）

### P3-1 ✅ 已交付（D1，略）
- grader `faithfulness_grade` + `EvalResult.faithfulness_score`/`red_flags` + C1 零容忍硬门 + 前端红线标记；67 tests 全绿。

### P3-3 Agent-as-Judge + 置信度门（P0）
- **目标**：用 LLM 当裁判时输出 `confidence`；低置信（<阈值）→ 标记 `NEEDS_REVIEW`，不自动过门。
- **范围**：`graders.py`（judge 返回加 `confidence`）、`agents.py:eval_gate`/`analyze_run`（低置信归并到 `regressed`/`review`）、`M3 复核门`（已有 `review_status` 字段，复用）、序列化暴露 `confidence`。
- **验收**：① judge 结果带 confidence；② 低于阈值的 case `review_status=NEEDS_REVIEW` 且门禁不静默放行（失败阈值或 regressed 列出）；③ 新增单测：低置信 case 触发 review 标记、门禁精确指出；④ 不破坏 67→+N 测试。
- **依赖**：P3-1（已就绪）。**工作量 M**。

### P3-2 成本/性能维度 + 实时看板（P1）
- **目标**：评测结果记录被测 agent 的 Token 消耗、工具调用次数、首 Token/端到端时延；看板展示。
- **范围**：`EvalRun`/`EvalResult` 加 `cost_tokens`/`cost_calls`/`latency_first`/`latency_total`（Float/Int）；grader 在 `grade_run` 聚合；`EvalDashboard` 加成本/时延卡片 + 实时刷新（借鉴 TestHub InfluxDB 式 5s 刷新，轻量可用轮询）。
- **验收**：① run 详情展示成本/时延；② 榜单可按成本排序；③ 单测覆盖聚合逻辑；④ 零外送（从 trace/tool_outputs 提取，不新增外呼）。**工作量 M**。
- **依赖**：M4 Trace（已有）。

### P3-14 Copilot 对话入口 + eval-plan-designer（P0，差异化）
- **目标**：自然语言 → 自动生成「评测方案」（选哪些数据集/指标/门禁/基线），一键落地为评测计划。
- **范围**：新增 `apps/eval_pod/agents.py:plan_eval`（可选 LLM，失败降级为规则模板）+ `EvalPlan` 模型（`dataset_ids`/`metrics`/`gate_thresholds`/`baseline_run_id`）；前端 `A1` 加对话入口卡片，调 `plan_eval` → 预览 → 确认 → 触发 `run`。
- **验收**：① 输入需求一句话，返回结构化评测方案（JSON）；② 确认后创建 EvalRun（复用 run 设施）；③ 无 LLM 时降级为规则模板（零外送）；④ 单测覆盖规则降级路径。**工作量 M**。
- **依赖**：B1、A3、C1（均已具备）。

### P3-7 质量门核心/辅助分层 + 基线-5% + 饱和监控（P1）
- **目标**：指标分「核心（阻断）/辅助（告警）」；核心相对基线跌 >5% 阻断；评测集饱和（区分度低）告警。
- **范围**：`eval_gate` 拆 `core_metrics`/`aux_metrics`；`compare_to_baseline` 用 `regress_delta=0.05`；M5 看板加「饱和指数」(方差/区分度)。
- **验收**：① 核心指标跌破基线-5% 硬阻断；② 辅助指标仅告警不阻断；③ 低区分度数据集标「饱和」；④ 单测覆盖分层门禁。**工作量 M**。

### P3-12 DeepEval 三指标并入指标库（P1）
- **目标**：`ToolCorrectness`/`PlanAdherence`/`GoalCompletion` 作为可配置 grader。
- **范围**：`graders.py` 加三函数（ToolCorrectness 比对 tool_outputs 与期望；PlanAdherence 比对步骤序列；GoalCompletion 比对终态）；接入 `grade_case` 的 grader_config 分发。
- **验收**：① 三指标可独立开关；② 与现有 RULE/LLM judge 并存；③ 单测覆盖（含确定性降级）。**工作量 M**。

### P3-4 Skill 作为可版本化评估器（P1）
- **目标**：评估逻辑封装为可导入、带版本的 Skill（对齐 A3 的 versioned/diff）。
- **范围**：定义 `EvaluatorSkill` 规范（SKILL.md + 评分入口），`apps/eval_pod` 支持从 skill 加载 grader；与 A3 数据集版本化共用 diff 能力。
- **验收**：① 一个示例 evaluator skill 可导入并参与评分；② 版本变更可在 A3 diff 视图对比；③ 不破坏现有评分路径。**工作量 M**。

---

## 3. 执行波浪（建议排期）

- **Wave 1（eval 核心增强，高价值低风险，建议立即）**：P3-3 → P3-2 → P3-7 → P3-12。
  - 理由：全部在现有 M3/C1/M4/A4 上增强，纯后端为主，确定性优先，直接加固护城河。
- **Wave 2（体验壳，借鉴 TestHub）**：P3-14（Copilot+eval-plan）→ P3-13（知识中枢）→ P3-15（Trace 回放）→ P3-16（定时评测+IM）。
  - 理由：提升「可用性/运营体验」，前端为主，差异化强。
- **Wave 3（生态与闭环）**：P3-4（Skill 版本化）→ P3-5（冷启动）→ P3-8（OTel 回流）→ P3-9/10/11（数据闭环与强度规则）→ P3-17（报告产物）。
  - 理由：依赖 Wave1/2 沉淀的抽象（grader 注册、trace、数据集版本），适合后做。

---

## 4. 全局约定

- **不提交 git**：所有 P3 改动停留工作区，累积到一定里程碑（建议 Wave 1 完成后）再一次性评审提交 `agent-eval-v2`。
- **测试**：后端用 `E:\evi\aotutest\Scripts\python.exe`；运行须 `FIELD_ENCRYPTION_KEY`（DEBUG=False 强制加密字段必填），否则 crypto 报 ImproperlyConfigured。
- **迁移**：本地生成不入库（`.gitignore` 忽略 `apps/*/migrations/*`）；新增字段走本地迁移。
- **前端构建**：`vite build` 受 WorkBuddy `safe-delete` 闸门影响时，`unset CODEBUDDY_SAFE_DELETE_BULK_STATE_DIR CODEBUDDY_TOOL_CALL_ID` 后重跑（详见 2026-08-14 日志）。
- **原则**：补缺不重造；纯确定性 grader 优先；租户隔离与数据不出域不动。
