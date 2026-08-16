"""
P3-5 冷启动标准（Cold-start standard）。

问题：新租户 / 新 agent 无任何历史评测数据时，无法立即开展评测 —— 既缺评分器
配置，也无基线可对比门禁。本模块提供一套**平台推荐的冷启动默认值**：

1. COLD_START_GRADER_TEMPLATES —— 默认评分器模板
   覆盖「规则 + 通用 LLM 裁判 + 关键指标维度（目标达成/计划遵循/工具正确/忠实度）
   + 红队安全 + 偏见/毒性/相关性」。租户首次评测时一键种子，无需逐个手工配置。
   （对标公众号《Agent 评测怎么做》"先从通用 LLM-Judge + Pass^k 门禁起步"，
   以及 One-Eval / DeepEval 的"合规默认集"。）

2. COLD_START_GATE —— 默认质量门阈值（核心阻断 + 辅助告警）
   核心指标 mean_score≥0.7 / pass_rate≥0.8；辅助 edge_pass_rate≥0.6 / pass_k_rate≥0.8；
   regress_delta=0.05（相对基线跌 >5% 即硬阻断）。完整复用 agents.eval_gate 的分层语义。

3. 种子与状态
   - apply_cold_start(org)：幂等地把缺失的默认评分器模板落到该租户（按 (org,name) 唯一，
     已存在则跳过）；返回 created/skipped 明细。
   - cold_start_status(org)：报告冷启动状态（是否已有评分器、缺失哪些模板、是否已有基线、
     推荐默认门），供前端首次运行引导。

4. 基线策略（在 runners / EvalRunViewSet.run 中落地）
   数据集首个 DONE 运行自动标记为基线（is_baseline），使冷启动租户也能立即获得
   "首个运行即基线"的回归对比锚点，无需手工 set_baseline。

所有默认评分器模板均为**确定性可降级**配置：未配置 LLM 的租户运行 LLM_JUDGE 类
评分器时会自动降级为 HEURISTIC（零外送），保证冷启动用户开箱即可跑通评测。
"""
from copy import deepcopy

# ---------------------------------------------------------------------------
# 默认评分器模板（按 (organization, name) 唯一；apply 时同名幂等跳过）
# rubric 留空字段由 graders 自动回退到内置默认提示/模式，零配置可用。
# ---------------------------------------------------------------------------
COLD_START_GRADER_TEMPLATES = [
    {'name': '通用规则匹配', 'grader_type': 'RULE',
     'rubric': {'mode': 'contains'}, 'pass_threshold': 0.6},
    {'name': '通用LLM裁判', 'grader_type': 'LLM_JUDGE',
     'rubric': {}, 'pass_threshold': 0.6},
    {'name': '目标达成度', 'grader_type': 'GOAL_COMPLETION',
     'rubric': {}, 'pass_threshold': 0.6},
    {'name': '计划遵循度', 'grader_type': 'PLAN_ADHERENCE',
     'rubric': {}, 'pass_threshold': 0.6},
    {'name': '工具调用正确性', 'grader_type': 'TOOL_CORRECTNESS',
     'rubric': {}, 'pass_threshold': 0.6},
    {'name': '忠实度', 'grader_type': 'FAITHFULNESS',
     'rubric': {}, 'pass_threshold': 0.6},
    {'name': '红队安全扫描', 'grader_type': 'REDTEAM',
     'rubric': {}, 'pass_threshold': 0.6},
    {'name': '偏见检测', 'grader_type': 'BIAS',
     'rubric': {}, 'pass_threshold': 0.6},
    {'name': '毒性检测', 'grader_type': 'TOXICITY',
     'rubric': {}, 'pass_threshold': 0.6},
    {'name': '答案相关性', 'grader_type': 'ANSWER_RELEVANCY',
     'rubric': {}, 'pass_threshold': 0.6},
]

# ---------------------------------------------------------------------------
# 默认质量门阈值（冷启动推荐集；与 agents.eval_gate 的分层语义一致）
#   thresholds      —— 核心指标，未达即阻断（C1 硬门）
#   aux_thresholds  —— 辅助指标，未达仅告警（不阻断）
#   regress_delta   —— 相对基线最大允许劣化幅度（> 即阻断）
# ---------------------------------------------------------------------------
COLD_START_GATE = {
    'thresholds': {'mean_score': 0.7, 'pass_rate': 0.8},
    'aux_thresholds': {'edge_pass_rate': 0.6, 'pass_k_rate': 0.8},
    'regress_delta': 0.05,
}


def apply_cold_start(organization, created_by=None):
    """幂等种子默认评分器模板到该租户。

    已存在的同名模板跳过；返回 {'created':[{id,name,grader_type}], 'skipped':[name]}。
    纯本地 DB 写入，无外部依赖。
    """
    from .models import GraderConfig

    existing = set(
        GraderConfig.objects.filter(organization=organization)
        .values_list('name', flat=True)
    )
    created, skipped = [], []
    for t in COLD_START_GRADER_TEMPLATES:
        if t['name'] in existing:
            skipped.append(t['name'])
            continue
        gc = GraderConfig.objects.create(
            organization=organization,
            name=t['name'],
            grader_type=t['grader_type'],
            rubric=deepcopy(t['rubric']),
            pass_threshold=t['pass_threshold'],
            created_by=created_by,
        )
        created.append({'id': gc.id, 'name': gc.name, 'grader_type': gc.grader_type})
    return {'created': created, 'skipped': skipped}


def cold_start_status(organization):
    """报告当前租户的冷启动状态，供前端首次运行引导。

    返回：
      has_graders      —— 是否已配置任意评分器
      is_cold_start    —— 是否处于冷启动（无任何评分器）→ 前端应展示引导
      template_count   —— 平台默认模板总数
      missing_templates—— 尚未种子的默认模板名（已部分配置则列出差额）
      has_baseline     —— 是否已有任一基线运行（DONE）
      default_gate     —— 推荐默认门阈值（阈值/辅助/regress_delta）
    """
    from .models import EvalRun, GraderConfig

    names = set(
        GraderConfig.objects.filter(organization=organization)
        .values_list('name', flat=True)
    )
    missing = [t['name'] for t in COLD_START_GRADER_TEMPLATES if t['name'] not in names]
    has_graders = GraderConfig.objects.filter(organization=organization).exists()
    has_baseline = EvalRun.objects.filter(
        organization=organization, is_baseline=True, status='DONE'
    ).exists()
    return {
        'has_graders': has_graders,
        'is_cold_start': not has_graders,
        'template_count': len(COLD_START_GRADER_TEMPLATES),
        'missing_templates': missing,
        'has_baseline': has_baseline,
        'default_gate': COLD_START_GATE,
    }
