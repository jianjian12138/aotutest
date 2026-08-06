# 项目长期记忆（aotutest）

## 产品定位（关键 · 2026-08-06 用户明确）
- **我们要打造的是「agent 测评 + LLM 测试的全栈平台」**，传统自动化（Selenium/API/性能/安全）退居辅舱。
- 升级路线已锁定为 **路线三：混合演进**（eval-native 评测舱 + 复用 aotutest 身份/多租户底座 + 租户功能开关解耦）。
- 演进分支：`agent-eval-v2`（基于 `new-main` 的 `8fbf5f6`）。

## 工程约定（踩坑沉淀，复用）
- 项目 `.gitignore` 忽略所有 `apps/*/migrations/*` → **迁移本地生成、不入库**；测试前需本地 `makemigrations`（否则 `no such table`）。
- CI 现有 `makemigrations --check` 在全新 clone 上潜在失效（迁移被忽略）——建议单独立项修复。
- **Windows git 分支名不能含斜杠**（否则引用静默不写），演进分支用无斜杠名 `agent-eval-v2`。
- 提交可靠路径（绕过 git 在特殊状态失败）：`read-tree` 基树 → `add` 仅交付文件 → `write-tree` → `commit-tree -p <base>` → `update-ref`。
- 远程 URL 用 PAT 推送后必须**剥除 PAT**、恢复 `http.sslVerify=true`。
- 当前栈：Django 4.2 + DRF；`AUTH_USER_MODEL='core_platform.User'`；前端 Vue；测试 `manage.py test`（pytest 仅跑非 Django 依赖测试）。

## 开源对标要点（2026-08-06 调研 + 同日增补）
- 全栈平台范：Langfuse（Next.js+ClickHouse，重）、One-Eval（React+Vite+FastAPI+LangGraph，NL2Eval+人机协同+中文基准）、**Opik**(Comet, Apache-2.0, 20k★, 观测+评估+Agent Tracing+Guardrails(PII/越狱/离题)+Agent Optimizer+CI)、**Arize Phoenix**(Python/TS/GraphQL/Postgres, Session→Trace→Span+过滤DSL, ELv2 常见)。
- 评估引擎范：DeepEval（Python，30+ 指标，pytest 风，需 LLM key 降级）、Ragas（RAG 专用）、**Inspect AI**(UK AISI, MIT, Solver/Scorer/200+ eval/红队=elicitation 扩展)。
- 测试/红队范：promptfoo（TS，CLI+React，prompt/agent/RAG 测试+红队+A/B，MIT，本地隐私）。
- Agent 测试库：Giskard（Python，agent checks + garak/deepteam 红队扫描，无 UI/RAG/HITL）。
- 公众号《多Agent协作测试系统实战》核心：**调度/用例生成/执行调度/结果分析** 四角色分工；结果分析=LLM-as-Judge；渐进四步落地；代价=中间格式设计/错误传播/调度单点。对 M3（裁判）与 Phase3（辅舱）高度借鉴。**结论：文章对升级高度有帮助**（已写入 benchmark §3）。
- 我方差距：数据集版本化、丰富指标库、Trace 可观测、红队测试(=Opik Guardrails：PII/越狱/离题扫描，须 offline 启发式)、人机协同复核门、多维报告/榜单、CI 门禁。

## 待建（路线图）
- Phase2 已落地：M2 数据集 / M3 指标库+复核门 / M4 Trace / M5 报告看板(后端) / 红队 REDTEAM。
- 待建：Phase3 智能体自动化辅舱（agent 生成用例 + 复用执行设施 + 确定性基线）；Phase4 门禁+可观测进 CI；横切：AIModelConfig 加 organization（租户自有模型，彻底出域隔离）；数据集版本化+Diff(§13-C)；M5 前端 Vue 看板接入。
