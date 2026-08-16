---
name: eval-flow
description: 在 aotutest 评测舱内执行「用例生成(B1) → 评测(exec) → 可靠性门禁(C1) → 分析归因(B3) → Trace 导出(C2)」的标准评测流。当用户要评测一个 Agent/LLM、做回归门禁或生成评测报告时使用。
type: eval
version: "1.0"
---

# eval-flow · Agent/LLM 评测标准流

把评测当作可复用的 skill（对标文章一：评测即 skill，SKILL.md + references + workflows + templates 三层结构）。
本 skill 封装评测舱 B1/B3/C1/C2 的标准工作流，供人类或上层智能体调用。

## 何时用
- 需要对某个模型/智能体做系统化评测（而非一次性脚本）。
- 需要在 CI 中做质量门禁（C3 eval-gate.yml 调用 C1）。
- 需要生成可追溯的评测报告（M5 看板）。

## 工作流（workflows）
1. **生成用例（B1）** `POST /api/eval/datasets/<id>/generate_cases/`
   body: `{ "req_text": "...", "mode": "offline|llm" }`
   - offline：零外送确定性启发式；llm：调用本租户 AIModelConfig，失败降级 offline。
2. **执行评测（exec/run）** `POST /api/eval/runs/<id>/run/`
   body: `{ "outputs": {case_id: output}, "repeat_k": 3, "judge_configs": [id,...], "agg_method": "TRIMMED_MEAN" }`
   - `repeat_k>1` → 计算 Pass^k（pass_k_rate，可靠性下限）。
   - `judge_configs` 多裁判 → PoLL 聚合（trimmed_mean/majority/panel_disagree）。
3. **质量门禁（C1）** `POST /api/eval/runs/<id>/gate/`
   body: `{ "thresholds": {"mean_score":0.7,"pass_k_rate":0.8}, "regress_delta":0.05 }`
   - 返回 passed / failed_thresholds / regressed_metrics；可接入 CI 阻断合并。
4. **分析归因（B3）** `GET /api/eval/runs/<id>/analyze/`
   - 返回 patterns（按裁判的系统性失败）+ crash_modes（长程 4 崩溃模式）。
5. **Trace 导出（C2）** `GET /api/eval/traces/export/?run=<id>`
   - Langfuse/OTel 风格 JSON，供可观测平台导入。

## 关键约定（references）
- **数据不出域**：所有 LLM 调用经 `AIModelConfig.for_tenant(org)`；无配置确定性降级启发式，未订阅租户零外送。
- **reason 强制非空**：任何评分结果必须带理由，防「静默通过」。
- **多裁判分歧送审**：PANEL_DISAGREE 且裁判结论不一致 → review_status=NEEDS_REVIEW（黄金样本人工复核）。
- **Pass^k vs Pass@1**：pass_rate≈Pass@1（能力上限），pass_k_rate=Pass^k（可靠性下限，专测 τ-bench 类）。
- **红队（E6）**：outputs 可传 `{output, tool_outputs}` 以检测「经工具返回值的间接注入」与「不可逆动作风险」。

## 模板（templates，Jinja 落盘）
见 `templates/case_skeleton.j2`：从需求文本生成 EvalCase 稳定中间格式
`{code, input_text, expected, is_edge, meta}`。

## 反模式
- 不要直连 `EvalResult.objects` 绕过租户隔离（用 ViewSet action / scoped_*）。
- 不要在无 `FIELD_ENCRYPTION_KEY` 环境跑测试（加密字段 fail-closed）。
- 不要把平台级(organization=None)模型配置用于评测舱取数（A2 出域漏洞）。
