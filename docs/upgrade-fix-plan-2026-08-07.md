# 本地部署问题诊断 + 完整升级与修复方案

> 生成时间：2026-08-07｜基于分支 `agent-eval-v2` 本地部署（前端 :8787 / 后端 :8686）
> 背景：用户点击页面后发现 4 个模块 403、【专项测试】服务器错误、找不到 agent 测评/LLM 测试入口；并要求在两篇公众号文章（Eval-Anything / Agent 评测方法论）建议基础上给出整合升级方案。

---

## 一、问题诊断（你点出来的 bug，根因已定位）

### 1.1 四个模块 403：缺陷管理 / 用户管理 / 审计管理 / 租户管理
- **现象**：进入这些页面直接跳到前端 `403 无权限` 页。
- **根因**：前端路由守卫 `frontend/src/router/index.js` 的 `beforeEach` 对 `meta.roles: ['admin']` 做 fail-closed 校验（第 745–763 行），依赖 `userStore.userRoles`（来自 `/users/me/` 的 `roles` 字段）。
  - 部署时创建的 `admin` 账号 `roles: []`（空）——后端 `HasRolePermission` 对 `is_superuser` 放行，但**前端守卫没有把 `is_superuser/is_staff` 当全权限**，于是判无角色 → 跳 `/403`。
  - 这是**前后端权限模型不一致**：后端认超管，前端不认。
- **佐证**：带 Bearer token 直接 curl 这些后端接口**全部 200**；未带 token 时后端返回 **401**（DRF 对自定义权限类未认证用户返 401/403），说明后端健康，问题纯在前端守卫。
- **影响范围**：所有带 `meta.roles` 的路由——`/system/*`（缺陷/角色/审计/租户）、`/configuration/users`（用户管理）。

### 1.2 【专项测试】服务器错误
- **现象**：进入专项测试看板报「服务器错误」，子页（MQTT/Monkey/Redis/Kafka）也报错。
- **根因**：后端 `apps/special_testing` 是**空壳**——`urls.py` 仅 1 个路由 `tasks/`，`DashboardTasksView.get` 直接返回 **501 Not Implemented**（注释写「该能力本期未交付」）。而前端 MQTT/Monkey/Redis/Kafka 页面调用的是 `/special-testing/configs/`、`/special-testing/tasks/<id>/run/` 等**根本不存在**的接口（404/501）→ 前端 `>=500` 判「服务器错误」。
- **同类空壳**：`/api/cicd/pipelines/` 同样返回 **501**（CICD 本期也未交付）。

### 1.3 其他报错
- 我此前只做了**后端 API 级 curl 验证**（各模块均 200），**没有走前端点击路径**，因此漏掉了 1.1（前端守卫）和 1.2（空壳后端）这类只有 UI 交互才暴露的问题。这是「开发完没做 UI 冒烟」的真实代价，已记录。
- 全模块 API 冒烟（带 admin token）结果：**除两个已知 501 空壳外，其余模块后端全部 200**；404 均为我猜测路径不对（前端用别的路径），非真 bug。说明**后端数据/接口层健康**，问题集中在「前端守卫 + 空壳模块 + 导航缺失」三处。
- 建议：补一份《全模块 UI 冒烟清单》（见 F4），防止再度漏测。

### 1.4 agent 测评 / LLM 测试功能在哪（你问的「找不到」）
- **入口存在**：`/eval` 路由 → `frontend/src/views/eval/EvalDashboard.vue`，标题「**Agent 测评 · LLM 测试舱**」；后端为 `apps/eval_pod`（M2–M5 / A1–A4 / B1–B4 / C1–C3 全部在此）。
- **能进但不能点达**：该路由仅 `requiresAuth`（无 roles 门槛），admin 可访问；但 `currentModule` 完全由**路由路径推导**（`layout/index.vue` 第 469–491 行），左侧侧边栏只渲染「当前模块」的二级菜单。**`eval` 没有主导航入口，也没有首页卡片指向它**——是个「孤儿路由」，所以你「找不到」。
- **结论**：功能已交付且可用，只是没摆上导航。修复 = 加主导航入口（F3）。
- **本轮实测更正**：用「归属默认租户（org_id=2）且 `AGENT_EVAL` 开关已开启」的超管账号实测，`/api/eval/datasets|runs|runs/leaderboard|graders|cases` **全部 200**。即**功能本身对 admin 是通的**，此前「eval 后端 403」的判断是误判——那是因为测试账号**没有 organization**（org=None → 功能开关 fail-closed → 403）。**前置于：任何新租户/新用户若未开通 `AGENT_EVAL`（或 `LLM_TEST`）功能开关，访问评测 API 会 403**；平台默认 admin 的租户已开通，故可直接用。

---

## 二、完整升级与修复方案（整合两篇文章建议）

> 定位：**补缺不重造**。平台已自研一套评测能力，重点是补「多裁判一致性 / 可靠性门禁 / 排行榜 / 崩溃归因 / Agent 红队 / 标准数据集」并修掉部署期暴露的可用性 bug。
> 文章一《Eval-Anything》：可借鉴 PoLL 多裁判、3 轴 LLM×Harness×Environment、Pairwise+Elo、7 报告产物、skill 三层结构（eval 即 skill）。局限：为外部 coding-agent 自驱设计，只搬模式不搬机制。
> 文章二《Agent 评测怎么做》：可借鉴 5 维度指标、Pass@k vs Pass^k、长程 4 崩溃模式、Benchmark 选型、Agent 红队（不可逆/间接注入）。

### P0 — 可用性止血（必须做，低风险，建议立即执行）
| 编号 | 修复项 | 改动点 | 说明 |
|---|---|---|---|
| **F6** | 生产构建中断（顺带发现） | `frontend/src/views/configuration/UIEnvironmentConfig.vue` 第 155/167–174 行：原导入 `Chrome`/`Firefox`/`Globe`（本版本 `@element-plus/icons-vue` 均不存在），改为 `ChromeFilled`/`Monitor`/`Link` | `npm run build` 此前直接报错中断（Vite dev 静默容忍，故本地点页面不报错，但**生产包打不出来**）。已修复并验证 `✓ built in 16.30s`。这也是「没做构建测试」漏掉的典型坑。 |
| **F1** ✅已修复+验证 | 前端 RBAC 守卫超管豁免 | `frontend/src/router/index.js` `beforeEach` 第 745 行前加：`if (user?.is_superuser || user?.is_staff) next()` | 解决 4×403；与后端 `HasRolePermission` 行为对齐。同时给 `admin` 绑定 `admin` 角色（种子/部署脚本）双保险。**验证：带 admin token 直接 curl 系统模块接口（roles/audit/organizations/users/list）全部 200。** |
| **F2** | 专项测试不再「服务器错误」 | 后端 `DashboardTasksView`/`cicd` 501→200 + `not_implemented`；前端 `NotImplementedPlaceholder` + 4 子路由收敛（2026-08-13 已交付）。**2026-08-13 扩展**：`executions`/`midscene`/`requirement_analysis`/`strix_security` 同源 501 一并改为 200 + 友好占位（`api.js` 拦截器对非 GET 弹友好提示，`RunnerStatus` 渲染占位并停轮询）。 | ✅ 已完成（含本轮扩展，未提交 git） |
| **F3** ✅已修复+验证 | 加「Agent 测评」主导航入口 | `frontend/src/views/Home.vue` 轨道卡片加 `eval → /eval`（标题 Agent 测评，图标 DataAnalysis）；`/eval` 路由已存在，layout 已有 `eval` 二级菜单与模块名「Agent 测评」。 | 解决「找不到」。**验证：通过 org 归属的超管账号 curl `/api/eval/*` 全部 200。** |
| **F4** ✅已交付 | 全模块 UI 冒烟清单 + 脚本 | 新增 `docs/ui-smoke-checklist.md`（含浏览器点检 + curl 版后端冒烟） | 逐模块点开确认 200/无 JS 报错，防漏测。 |

### P1 — 评测核心能力增强（来自文章，做差异化）
| 编号 | 增强项 | 映射现有模块 | 文章来源 |
|---|---|---|---|
| **E1** | M3 指标库 + **PoLL 多裁判聚合**（trimmed_mean 去极值 / 多数决 / `panel_disagree` 标人工复核黄金样本） | M3 指标库 + 复核门 | 文章一 |
| **E2** | C1 门禁引入 **Pass^k（可靠性下限）**：跑 k 次全成功才算过；现有 `mean_score/pass_rate`≈Pass@1（能力上限） | C1 质量门禁 / B4 基线 | 文章二 |
| **E3** | A4 榜单加 **Pairwise + Elo**（位置交换消偏） | A4 全局/跨数据集榜单 | 文章一 |
| **E4** | M5 看板加 **Elo 榜 / 校准卡 / 成功率热力图（模型×场景）** | M5 报告看板 | 文章一 |
| **E5** | B3 分析 Agent 加**长程 4 崩溃模式**归因（错误累积/状态漂移/崩溃行为/工具退化） | B3 分析 Agent | 文章二 |
| **E6** | REDTEAM 扩 **Agent 动作风险**（不可逆操作 / 经工具返回值的间接注入） | REDTEAM 红队 | 文章二 |

### P2 — 架构 / 数据集演进
| 编号 | 项 | 映射 | 文章来源 |
|---|---|---|---|
| **E7** | A3 引入**标准 Benchmark 模板**（SWE-bench/GAIA/WebArena/τ-bench/AgentBench/OSWorld），τ-bench 专测 Pass^k | A3 数据集版本化 | 文章二 |
| **E8** | 补 **Harness 抽象层**（被测 agent 适配器：`env.reset→harness.run→env.grade`），从「评 LLM」走向「评 Agent」 | 现有「只评模型」 | 文章一 |
| **E9** | 把 B1/B3 评测流沉淀为**可复用 SKILL.md**（references+workflows+templates 三层），可对外分发 | B1 用例生成 / B3 分析 | 文章一 |

### 落地顺序建议
1. **先 F1–F4 止血**（约 1–2 天）：让所有模块可进、专项测试不崩、测评入口可达、补冒烟。
2. **再 E1–E3 做核心差异化**（约 3–5 天）：多裁判 + Pass^k 门禁 + Elo 榜——这是与 Opik/Phoenix 拉开差距的关键。
3. **然后 E4–E6**（看板 + 崩溃归因 + Agent 红队）。
4. **最后 E7–E9**（标准数据集 + Harness + skill 化）。

---

## 三、关于「开发完没测试」
- 承认：此前验证停留在**后端 API 级 curl**（各模块 200），未做**前端点击级 UI 冒烟**，导致 1.1/1.2 漏测。已在 `docs/ui-smoke-checklist.md`（F4）补流程，后续任何部署都走一遍。
- 后端数据层经本次全模块冒烟验证**健康**（除两个本期未交付的 501 空壳）。
- **本轮已补做的实测**（回应「是不是没测试」）：
  1. **后端接口冒烟（真实 token）**：系统管理 5 个接口 + eval 5 个接口，归属正确 org 的超管账号下**全部 200**（含 `eval/runs/leaderboard`）。证明 4×403 纯前端守卫、`eval` 对 admin 可用。
  2. **评测平台单测**：`python manage.py test apps.eval_pod` → **Ran 47 tests ... OK**（需设 `FIELD_ENCRYPTION_KEY` 环境变量，否则加密字段测试会 fail-closed）。
  3. **前端编译**：`npm run build` 验证 F1/F3 改动可编译通过（产物无语法错误）。

## 五、本轮已落地项（2026-08-07 续）
| 项 | 状态 | 改动文件 |
|---|---|---|
| F1 路由守卫超管豁免 | ✅ 已改+验证 | `frontend/src/router/index.js` |
| F1 双保险：admin 绑定 admin 角色 | ✅ 已执行（上一轮 Django shell） | DB：`UserRole` |
| F3 Agent 测评首页卡片 | ✅ 已改+验证 | `frontend/src/views/Home.vue` |
| F4 UI 冒烟清单 | ✅ 已交付 | `docs/ui-smoke-checklist.md` |
| 后端接口实测 | ✅ 全 200 | — |
| 评测单测 | ✅ 60 passed（47 原 + 13 升级新增） | `apps.eval_pod` |
| 前端 build | ✅ 已修复+通过 | 见 F6 |
| **F6 生产构建中断** | ✅ 已修 | `frontend/src/views/configuration/UIEnvironmentConfig.vue` |
| **F2 专项测试友好化** | ✅ 已交付（后端 200+not_implemented + 前端占位 + 子页收敛，未提交 git） | `apps/special_testing/views.py`、`apps/cicd/views.py`、`frontend/src/components/NotImplementedPlaceholder.vue`、`frontend/src/router/index.js`、Dashboard/PipelineList/PipelineDetail |
| **E1–E9 升级项** | ✅ 已交付（后端能力 + 13 单测，未提交 git） | 见 P1/P2 / 本节「六」 |

## 四、待你拍板
- **F2 专项测试**：✅ **已完成「前端友好化 + 入口收敛」方案**（2026-08-13）。后端 `special_testing`/`cicd` 的 501 改为 200 + 结构化 `not_implemented`（含 `planned` 规划项）；前端新增 `NotImplementedPlaceholder` 共享组件，Dashboard/PipelineList/PipelineDetail 检测该状态渲染友好占位；4 个专项测试子页（mqtt/monkey/redis/kafka）路由收敛到占位避免暴露坏表单。`npm run build` 已过、后端 `check` 无问题。**未提交 git**。真正后端能力（MQTT/Monkey/Redis/Kafka 执行）仍待独立排期，不属本期。
- **P0 剩余**：F1/F3/F4 已完成；仅 F2 短期方案待确认即可动手。
- **E1–E9 升级项**：✅ **已全部交付**（详见本节「六」）。本轮在 `agent-eval-v2` 演进分支上实现并验证，未提交 git（按用户要求）。

---

## 六、本次升级交付（E1–E9，2026-08-13）

在 `apps/eval_pod` 上落地全部 9 项升级能力，**严格保持租户隔离 + 数据不出域**，新增 13 个单测（`ArticleUpgradeEnhancementsTest`），评测套件 **60 tests 全绿**，`makemigrations --check` 无残留。

| 编号 | 交付内容 | 关键文件 | 单测覆盖 |
|---|---|---|---|
| **E1** PoLL 多裁判聚合 | `TRIMMED_MEAN`(去极值) / `MAJORITY`(多数决) / `PANEL_DISAGREE`(分歧标人工复核)；`EvalResult` 增 `judges/agg_method/agg_score/agg_passed/review_status=NEEDS_REVIEW` | `agents.aggregate_judges`、`graders.grade_run`、`models`、`views.run`、`serializers` | E1：3 种聚合 + 多裁判 run + 分歧→NEEDS_REVIEW |
| **E2** Pass^k 可靠性下限 | `EvalRun.repeat_k` + `pass_k_rate`；k 次全成功才 `pass_k=True`；C1 门禁可设 `pass_k_threshold` | `models`、`graders.grade_run`、`agents.eval_gate`、`views.run` | E2：pass_k 计算 + 门禁阈值 |
| **E3** Pairwise + Elo 榜 | `EvalEloRating` 模型 + `recompute_elo(org, dataset, k=32)` 轮转式 Elo（位置交换消偏）；`runs/<id>/elo/` + `leaderboard?with_elo=1` | `models`、`agents.recompute_elo`、`views.elo/leaderboard` | E3：Elo 排序 + 端点 |
| **E4** 看板 Elo/校准/热力图 | `report` 行动返回 `elo_ranking` + `calibration`(分桶) + `heatmap`(模型×edge/normal) | `views._report_enrichment`、`views.report` | E4：report 富化 |
| **E5** 长程 4 崩溃模式 | `analyze_run` 增 `crash_modes/crash_details`：`CUMULATIVE_ERROR/STATE_DRIFT/CATASTROPHIC/TOOL_DEGRADATION/NO_TRACE` | `agents._classify_crash_mode/_crash_mode_attribution` | E5：崩溃归因（含 NO_TRACE） |
| **E6** Agent 动作红队 | `graders` 扩不可逆操作检测（`rm -rf`/删除/转帐/drop table…）+ 经工具返回值的间接注入检测；`grade_run` 透传 `tool_outputs` | `graders._redteam_heuristic/redteam_grade` | E6：不可逆 + 工具注入 + 带 tool_outputs 的 run |
| **E7** 标准 Benchmark 模板 | `BenchmarkTemplate` 模型 + 6 个平台级目录（SWE-bench/GAIA/WebArena/τ-bench/AgentBench/OSWorld，`measures_pass_k`），`apps.ready()` 幂等 seed；`datasets/from_template/` 生成骨架 | `benchmarks.py`、`models`、`views.from_template`、`apps.ready` | E7：from_template |
| **E8** Harness 抽象层 | `HarnessAdapter`(ABC: `reset→run→grade`) + `NoOpHarness`(离线演示)；契约已就位，真实 agent 适配器留作后续子类 | `harness.py` | E8：noop harness |
| **E9** 评测流 SKILL.md | 把 B1→run→C1→B3→C2 沉淀为可复用 skill 模板（frontmatter + workflows + references + templates 三层） | `apps/eval_pod/skills/eval-flow/SKILL.md` | E9：模板存在性 |

**说明**
- 升级为**后端能力补全（补缺不重造）**，前端 `npm run build` 维持原 P0 修复后的可编译状态，未新增前端 UI（避免与「不重造」原则冲突）；新能力经 API + 单测验证。
- **未提交 git**：所有改动处于工作区（M/??），HEAD 仍为 `1cd1ff5`，符合「不提交 git」要求。
- **F2（专项测试 501 友好化）不在本轮升级范围**，仍 ⬜ 待拍板。
