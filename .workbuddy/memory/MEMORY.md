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
- 已落地（Phase0~2 + Phase A + Phase B + Phase C）：M2 数据集 / M3 指标库+复核门 / M4 Trace / M5 报告看板(后端+前端) / 红队 REDTEAM / **A2 租户自有模型** / **A3 数据集版本化+Diff** / **A4 全局+跨数据集榜单** / **A1 Vue 前端看板** / **B1 用例生成 Agent** / **B3 分析 Agent** / **B4 确定性基线** / **C1 质量门禁** / **C2 Trace 导出** / **C3 CI 门禁工作流**。
- 路线三全栈（Phase A/B/C）已于 2026-08-07 交付完毕；演进分支 `agent-eval-v2` 功能齐备，可进入主线合并评审。

## Phase B/C/A1 已落地明细（2026-08-07 交付，47 tests 全绿）
- B1 用例生成 Agent：`apps/eval_pod/agents.py:generate_cases`（离线启发式零外送 + 可选 LLM 升级 `default_llm_call` 复用 `AIModelService`，失败确定性降级）；`EvalDatasetViewSet.generate_cases` @action 批量写入 `EvalCase`，经 `EvalRunViewSet.run` 复用执行设施（B2）。
- **端到端演示/集成测试（2026-08-07 追加）**：
  - `apps/eval_pod/management/commands/demo_eval_flow.py`：离线零外送跑通「需求→生成(B1)→评测→基线(B4)→门禁(C1)→分析(B3)→Trace 导出(C2)」，幂等、支持 `--clean`；演示数据落在独立 `demo-eval` 租户，跑完可删。
  - `tests.py:EvalEndToEndTest`（2 项）：真实 API 链路验证「劣化版触发 C1 门禁精确指出 mean_score/pass_rate 掉点 / 等价候选过门禁且 B4 不判回归」。
- B3 分析 Agent：`agents.analyze_run` 按 judge 类型归类失败率≥0.5 系统性风险；`EvalRunViewSet.analyze`。
- B4 确定性基线：`EvalRun.is_baseline` + `set_baseline`/`compare` @action + `agents.compare_to_baseline`(mean_score/pass_rate/edge_pass_rate delta，regress_delta 阈值)。
- C1 质量门禁：`agents.eval_gate`(failed_thresholds + regressed_metrics 精确指出掉点指标) + `EvalRunViewSet.gate`；供 CI 调用。
- C2 Trace 导出：`EvalTraceViewSet.export` 返回 Langfuse/OTel 风格 JSON(trace + observations)，租户隔离经 Org 过滤。
- A1 Vue 前端：`frontend/src/views/eval/EvalDashboard.vue` + `src/api/eval.js` + 路由 `/eval` + 侧边菜单「Agent 测评」；报告概览 + A4 榜单 + B1 生成 + A3 Diff + 运行详情抽屉(B4/B3/C1/C2)。**注意：前端 `node_modules` 缺失时需 `npm install`（本机 .venv311 为后端正确环境：Django 4.2.7）**。
- C3 CI：` .github/workflows/eval-gate.yml` 监听 `agent-eval-v2` push/PR，跑 `apps.eval_pod` 测试套件（含 C1 门禁），任一失败阻断合并。
- 测试环境：后端用项目 `.venv311`（`Django 4.2.7`）；运行需 `FIELD_ENCRYPTION_KEY`/`SECRET_KEY`/`DEBUG=True` 环境变量；迁移 `0007_evalrun_is_baseline.py` 本地生成不入库。
- **端到端实跑提醒**：管理命令/演示连开发库 `db.sqlite3`，首次需 `manage.py migrate` 建表（迁移本地生成）；演示后删 `Organization(code='demo-eval')` 即可级联清理（eval 所有外键 on_delete=CASCADE）。

## Phase A 已落地明细（2026-08-07 提交 e22de8f，已推 origin/agent-eval-v2）
- A2 数据不出域：修复了 `EvalRunViewSet.run` 原 `AIModelConfig.objects.filter(is_active=True).first()` 跨租户取首个激活配置的出域漏洞；改为 `AIModelConfig.for_tenant(org)`，平台级(organization=None)配置不被评测舱取用，无自有模型租户确定性降级 HEURISTIC（零外送）。
- A4 榜单：`EvalRun.model_config`(FK→requirement_analysis.AIModelConfig) 溯源 + `EvalRunViewSet.leaderboard`(模型排名/数据集排名，严格租户隔离)。
- 注意：`AIModelConfig` 真身在 `apps/requirement_analysis/models.py`（非 `ai_models.py` 历史重复副本）；改动务必落在该文件。
- A3 数据集版本化+Diff：给 `EvalCase` 加 `code` 业务键（跨版本对应，空时 clone 派生 `case-<id>` 兼容历史数据）；`EvalDatasetViewSet.clone_version`(v1→v2 自动 bump 复制用例) + `EvalDatasetViewSet.diff`(按 code 对应返回 added/removed/changed/unchanged + 字段级差异)；严格租户隔离（他租户 diff 404）。提交 b712bcb。
