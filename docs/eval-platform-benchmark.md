# Agent 测评 / LLM 测试 开源平台对标分析（2026-08-06）

> 目的：为 aotutest 升级为「agent 测评 + LLM 测试全栈平台」（路线三）寻找可借鉴的开源方案。
> 对标对象：promptfoo、DeepEval、Langfuse、One-Eval（北大）、Giskard、Ragas。
> 配套：公众号《多Agent协作测试系统实战》单独评估（见 §3）。

---

## 1. 横向对比总表

| 项目 | 语言/技术栈 | 形态 | 核心能力 | 多租户/多项目 | Web UI | 协议 |
|---|---|---|---|---|---|---|
| **promptfoo** | TS / Node≥22 / React / Drizzle / libsql | CLI+库（测试/红队） | prompt/agent/RAG 测试、红队扫描、A/B 对比、CI | 否（文件/CLI） | React（view） | MIT |
| **DeepEval** | Python / Poetry / pytest 风 | 评估引擎（框架） | 30+ 指标（G-Eval/幻觉/偏见/毒性/RAG/Agentic/多轮/MCP/多模态）、合成数据、CI | 否 | 无（Confident AI 云面板） | Apache-2.0 |
| **Langfuse** | Next.js / Node24 / ClickHouse / Postgres / Redis / BullMQ | 全栈 Web 平台 | 可观测/Trace、eval（代码+LLM）、datasets、prompts、metrics、playground | 多项目（Cloud 区域隔离） | 是（完整） | MIT/Elastic |
| **One-Eval**（北大） | React+Vite / FastAPI / LangGraph+DataFlow / Py3.10-11 | 全栈评测编排 | NL2Eval（自然语言发起）、全链路追踪、人机协同、100+ 基准（含 C-Eval/CMMLU）、Docker 沙箱、HTML 报告 | 否（本地/仓库工具） | 是（React+Vite） | Apache-2.0 |
| **Giskard** | Python / uv monorepo / Pydantic / pytest | LLM Agent 测试/扫描库 | agent checks（judge/语义/groundedness）、红队扫描（garak/deepteam/lidar）、鲁棒性/偏见 | 否 | 否（CLI rich） | 待确认(permissive) |
| **Ragas** | Python | RAG 评估库 | 10+ RAG 指标（忠实度/相关性/上下文精度召回），无需标注 | 否 | 否 | Apache-2.0 |

---

## 2. 各项目详解与可借鉴点

### 2.1 promptfoo（★24k，测试/红队标杆）
- **技术栈**：TypeScript 主，React Web UI；Drizzle + libsql 本地库（数据隔离、隐私本地）；Vitest。
- **能力**：声明式 YAML 配置驱动 `promptfoo eval`；支持 prompt/agent/RAG；**红队/渗透/漏洞扫描**；多模型 A/B；CI 集成（`code-scan-action` 直接给 PR 出安全审查）；结果 100% 本地运行。
- **优点**：极快、本地隐私、MIT、被 OpenAI 收购仍开源、生产验证（千万级用户）。
- **缺点**：无数据集版本管理；无多租户；LLM-as-judge 细节未在前端暴露。
- **借鉴**：① **红队/安全测试**是一类独立能力，应作为评测舱的"安全维度"；② YAML/声明式配置可借鉴为 `GraderConfig` 的 schema；③ CI 门禁（PR 出安全报告）对应我们 Phase 4。

### 2.2 DeepEval（★17k，评估引擎标杆）
- **技术栈**：Python，pytest 风（`deepeval test run` + `assert_test`）；Poetry；TS 集成；Confident AI 云。
- **能力**：**30+ 指标**——G-Eval（研究背书的 LLM-as-judge 自定义标准）、幻觉/偏见/毒性、RAG（忠实度/相关性/上下文）、Agentic（任务完成/工具正确/计划遵循/步骤效率）、多轮、MCP、多模态；合成数据；CI/CD；端到端 trace。
- **优点**：指标广度第一、本地可跑、pytest 易上手、任意 LLM 适配。
- **缺点**：高级 judge 需第三方 LLM key（无网/无 key 部分不可用）；云同步默认开启（隐私）；红队在 roadmap 未交付。
- **借鉴**：① **指标库是评测引擎的核心资产**——我们当前只有 rule+LLM-judge+heuristic，应补 faithfulness/answer_relevancy/bias/toxicity/tool_correctness/plan_adherence 等；② 每个指标都要有 **offline/HEURISTIC 降级**（契合我们数据不出域约束）；③ `evaluate()` 与 `metric.measure()` 双模式可借鉴。

### 2.3 Langfuse（全栈可观测平台标杆）
- **技术栈**：Next.js + Node24 前端；worker（BullMQ 队列）+ packages/shared 后端；**ClickHouse**（事件主存）+ Postgres + Redis。
- **能力**：observability/tracing、eval（代码+LLM 模板）、datasets、prompts 管理、metrics、playground；集成 OTel/LangChain/OpenAI/LiteLLM。
- **优点**：真正全栈、自托管、集成广、活跃。
- **缺点**：**基础设施重**（ClickHouse 最低 25.12、Node24，运维门槛高）；v4 仍 preview；非 ClickHouse 环境性能打折。
- **借鉴**：① **Trace/可观测是评测舱的必需层**（对应我们 M4）；② 数据集/提示/评测统一在一个平台的产品形态；③ 但**不要照搬其重基建**——我们 Django+Postgres 足够，避免引入 ClickHouse。

### 2.4 One-Eval（北大，全栈中文评测编排）
- **技术栈**：React+Vite 前端；FastAPI 后端；**LangGraph**（可中断/恢复状态图）+ **DataFlow**（算子工作流）；Py3.10-11；Docker 沙箱。
- **能力**：**NL2Eval**（一句话自然语言发起评测）；全链路追踪 + `--resume` 断点续跑；**人机协同**（关键节点人工中断/审查）；100+ 基准含 C-Eval/CMMLU；多模态+代码沙箱；自包含 HTML 报告（14 指标/6 维度）。
- **优点**：零代码 NL2Eval、可追溯可恢复、中文基准原生、人机协同、Apache-2.0。
- **缺点**：Python 锁 3.10-11；无在线社区平台；Agentic 长程评测早期。
- **借鉴**：① **人机协同复核门**（human-in-the-loop）应作为评测结果的可信度闸门（对应我们缺的 HITL）；② **NL2Eval / 自然语言发起**可作为高层入口（Phase 3 辅舱的"调度 Agent"雏形）；③ 断点续跑=长任务可靠性。

### 2.5 Giskard（LLM Agent 测试库）
- **技术栈**：Python uv monorepo（core/agents/checks/scan）；Pydantic；pytest；第三方扫描器 lazy import。
- **能力**：agent checks（string/conformity/groundedness/judge/semantic/equality）；红队扫描（garak/deepteam/lidar）；结果强制非空 reason（防静默通过）。
- **优点**：专注 Agent 测试、可扩展扫描架构、工程质量高（pyright/ruff/pip-audit）。
- **缺点**：无 RAG/Hub/HITL；第三方扫描器多为 optional；无 UI。
- **借鉴**：① **结果必须带 reason**（防"静默通过"）——我们的 `EvalResult.reason` 应强制非空；② 红队/鲁棒性扫描的"攻击→CheckResult→severity"模型可借鉴为安全维度。

### 2.6 Ragas（RAG 评估库，补充）
- 仅做 RAG：faithfulness/answer_relevancy/context_precision/recall；无需 ground truth。若我们未来评测 RAG 类 agent，直接复用其指标思路。

---

## 3. 公众号《多Agent协作测试系统实战》评估

### 3.1 核心观点
- **四角色分工**：调度 Agent（拆解/分配/汇总）、用例生成 Agent（需求→结构化用例集 JSON）、执行调度 Agent（按依赖注入+并发执行，只记录不判断）、结果分析 Agent（机械断言+**语义判断用 LLM-as-Judge**+跨用例模式识别）。
- **关键洞见**：一个 Agent 同时做"创造+执行+分析"会稀释注意力→**分工**提升每角色质量。
- **渐进四步**：① 先用例生成 Agent；② +执行 Agent（验证依赖注入/并发）；③ +分析 Agent（看误报率/漏报率）；④ +调度 Agent（此前人工代调度）。
- **代价**：中间格式（用例 JSON）设计成本；**错误传播**（用例预期写错→分析误报，需在分析端加合理性校验）；调度 Agent 单点压力。

### 3.2 对我们的帮助度：**高，直接相关**
- 直接验证并细化我们的 **M3（评估引擎）**：结果分析 Agent = LLM-as-Judge；且强调"机械断言 + 语义判断 + 模式识别"三层，对应我们应同时有 rule 与 LLM-judge。
- 为 **Phase 3（智能体自动化辅舱）** 提供现成架构蓝图：把"生成/执行/分析"拆成独立 Agent，避免单 Agent 上下文稀释。我们 eval_pod 的 `EvalCase` schema 就是文章里的"中间格式"，必须稳定。
- **警示直接可用**：① 用例/预期错误会静默传播→我们需"分析端合理性校验"+**人机协同复核门**（借鉴 One-Eval/Giskard）；② 调度单点→Phase 3 的调度 Agent 提示词需重点打磨。

---

## 4. 我方原型差距与借鉴清单

| 维度 | 我方现状（eval_pod） | 对标差距 | 借鉴来源 | 优先级 |
|---|---|---|---|---|
| 数据集版本化 | 仅 `version` 字符串 | 无快照/Diff | promptfoo/DeepEval/One-Eval | 高 |
| 指标库广度 | rule+LLM-judge+heuristic | 缺 faithfulness/relevancy/bias/toxicity/tool_correctness/plan_adherence | DeepEval | 高 |
| 结果 reason 强制 | 有 reason 字段但未强制 | 允许空→静默通过风险 | Giskard | 中 |
| 人机协同复核 | 无 | 缺复核门（误报阻断） | One-Eval/Giskard | 高 |
| 红队/安全测试 | 无 | 缺越狱/泄漏扫描 | promptfoo/Giskard | 中 |
| Trace 可观测 | 无（M4 待建） | 缺步骤级追踪/回放 | Langfuse/One-Eval | 高 |
| 多维报告/榜单 | 仅 run 汇总 | 缺趋势/模型排名 | One-Eval/Langfuse | 中 |
| 多 Agent 编排 | 同步 @action | 缺生成/执行/分析 Agent 拆分 | 公众号文章 | 中 |
| CI 门禁 | 无（Phase4） | 缺分数阈值拦截 | promptfoo/DeepEval | 中 |

---

## 5. 结论与升级建议
1. **不重造轮子、不照搬重基建**：评估引擎指标库借鉴 DeepEval 思路（但自研、保持 offline 降级）；可观测借鉴 Langfuse 的"层"概念但**用 Django+Postgres 实现，不引 ClickHouse**。
2. **最该补的四件事（按性价比）**：
   - (A) 丰富 grader 指标库（faithfulness/relevancy/bias/toxicity/tool_correctness/plan_adherence）+ 强制 reason；
   - (B) 人机协同复核门（EvalResult.review_status，阻断误报）；
   - (C) 数据集版本化 + Diff；
   - (D) Trace 模型（步骤级观测，M4）。
3. **红队/安全维度**作为独立评测类型（kind=REDTEAM）单独立项，借鉴 promptfoo/Giskard。
4. **多 Agent 编排**按公众号四步法渐进：先把"分析=LLM-as-Judge"做稳，再演进"生成/执行/分析"Agent 拆分。
5. **文章高度相关**，其"分工 + 渐进 + 错误传播防护"应写入 Phase 3 设计原则。
