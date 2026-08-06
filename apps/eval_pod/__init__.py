"""eval-native 评测舱（路线三 · Phase 2 核心）。

与现有传统自动化（testcase/testsuite）完全隔离的独立模块群：
- 数据集管理（M2）
- 评估引擎：规则 / LLM-as-Judge（M3）
- 后续：Trace 回放（M4）、报告看板（M5）

所有能力以 TenantFeature(AGENT_EVAL) 为闸门，且严格按租户隔离（无超级读者）。
"""