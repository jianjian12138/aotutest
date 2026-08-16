"""
评测舱数据模型（路线三 · Phase 2 · M2 数据集管理）。

设计原则（对应评审报告 / 路线图）：
- 与现有传统自动化模型（testcase / testsuite / 执行记录）**完全解耦**，
  不污染存量客户数据与语义。
- 所有核心模型均带 organization（租户）外键，配合 TenantAwareViewSetMixin
  实现严格租户隔离（无平台"超级读者"）。
- EvalCase.is_edge 标记边缘用例，强制数据集质量（路线图要求 ≥30% 边缘用例）。
"""
import os

from django.db import models
from django.utils import timezone

from apps.core_platform.models import Organization


class EvalDataset(models.Model):
    """评测数据集（tenant 级）。"""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='eval_datasets'
    )
    name = models.CharField(max_length=200, help_text='数据集名称')
    description = models.TextField(blank=True)
    version = models.CharField(max_length=40, default='v1')
    created_by = models.ForeignKey(
        'core_platform.User', on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'eval_datasets'
        unique_together = ('organization', 'name', 'version')
        ordering = ('-created_at',)
        verbose_name = '评测数据集'
        verbose_name_plural = '评测数据集'

    def __str__(self):
        return f'{self.organization.code}/{self.name}@{self.version}'

    @property
    def case_count(self):
        return self.cases.count()

    @property
    def edge_count(self):
        return self.cases.filter(is_edge=True).count()

    @property
    def edge_ratio(self):
        """边缘用例占比（路线图要求 ≥0.3）。"""
        total = self.case_count
        if not total:
            return 0.0
        return round(self.edge_count / total, 3)


class EvalCase(models.Model):
    """评测用例：输入 + 期望（含边缘用例标记）。

    code 为可选业务键，用于跨数据集版本 diff 对应（A3 数据集版本化）。
    为空时由 clone_version 派生为 case-<id>，保证历史数据也能正确比对。
    """

    dataset = models.ForeignKey(
        EvalDataset, on_delete=models.CASCADE, related_name='cases'
    )
    code = models.CharField(
        max_length=120, blank=True, null=True, db_index=True,
        help_text='用例业务键（可选），跨版本 diff 对应键；为空时系统派生 case-<id>',
    )
    input_text = models.TextField(help_text='被测模型/智能体的输入或提示')
    expected = models.TextField(blank=True, help_text='期望输出 / 参考答案')
    is_edge = models.BooleanField(
        default=False, help_text='是否为边缘用例（异常输入、对抗样本、长尾场景等）'
    )
    CASE_ROLES = [
        ('CAPABILITY', '能力'),
        ('REGRESSION', '回归'),
    ]
    case_role = models.CharField(
        max_length=20, choices=CASE_ROLES, default='CAPABILITY', db_index=True,
        help_text='用例角色：CAPABILITY=能力验证（新功能/新指标覆盖），'
                  'REGRESSION=回归验证（防劣化）；用于报告按角色拆分通过率',
    )
    meta = models.JSONField(default=dict, blank=True, help_text='额外元数据')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'eval_cases'
        verbose_name = '评测用例'
        verbose_name_plural = '评测用例'

    def __str__(self):
        return f'#{self.id} edge={self.is_edge}'


class EdgeCaseRule(models.Model):
    """P3-9 边缘用例规则：可复用的输入变异 / 输出约束模板。

    用于把数据集中的「普通用例」按规则派生为「边缘用例」（对抗样本、异常输入、
    长尾场景等），派生出的用例标记 is_edge=True，从而让 grade_run 的 edge_pass_rate
    （已在冷启动门禁 aux_thresholds 预留 edge_pass_rate≥0.6）真正有数据可算。

    - 平台默认规则由 edge_cases.ensure_default_edge_rules 按租户幂等播种；
    - 租户也可自建私有规则（code 在租户内唯一）。
    """

    CATEGORIES = [
        ('INPUT_MUTATION', '输入变异'),
        ('OUTPUT_CONSTRAINT', '输出约束'),
    ]

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='edge_rules'
    )
    name = models.CharField(max_length=200, help_text='规则展示名')
    code = models.CharField(
        max_length=40, help_text='规则代码（如 EMPTY_INPUT / LONG_REPEAT），同租户唯一'
    )
    category = models.CharField(
        max_length=20, choices=CATEGORIES, default='INPUT_MUTATION'
    )
    description = models.TextField(blank=True, help_text='规则说明 / 触发场景')
    enabled = models.BooleanField(
        default=True, help_text='是否启用（apply 时仅对启用规则生成变体）'
    )
    params = models.JSONField(
        default=dict, blank=True,
        help_text='规则参数，如 {"repeat": 20} / {"prefix": "..."} / {"replacement": "..."}',
    )
    created_by = models.ForeignKey(
        'core_platform.User', on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'eval_edge_rules'
        unique_together = ('organization', 'code')
        verbose_name = '边缘用例规则'
        verbose_name_plural = '边缘用例规则'

    def __str__(self):
        return f'{self.organization.code}/{self.code}({self.category})'


class GraderConfig(models.Model):
    """评分器配置：规则匹配 / LLM-as-Judge。"""

    GRADE_TYPES = [
        ('RULE', '规则匹配'),
        ('LLM_JUDGE', 'LLM 裁判（通用）'),
        ('FAITHFULNESS', '忠实度'),
        ('ANSWER_RELEVANCY', '答案相关性'),
        ('BIAS', '偏见检测'),
        ('TOXICITY', '毒性/有害性'),
        ('TOOL_CORRECTNESS', '工具调用正确性'),
        ('PLAN_ADHERENCE', '计划遵循度'),
        ('GOAL_COMPLETION', '目标达成度'),
        ('REDTEAM', '红队/安全扫描'),
    ]

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='graders'
    )
    name = models.CharField(max_length=200)
    grader_type = models.CharField(
        max_length=20, choices=GRADE_TYPES, default='RULE'
    )
    rubric = models.JSONField(
        default=dict, blank=True,
        help_text='评分细则：规则模式用 {"mode":"exact|contains|regex"}；'
                  'LLM 裁判用 {"prompt":"...","pass_threshold":0.6}',
    )
    pass_threshold = models.FloatField(default=0.6, help_text='判定通过的分阈值（0-1）')
    created_by = models.ForeignKey(
        'core_platform.User', on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'eval_graders'
        unique_together = ('organization', 'name')
        verbose_name = '评分器配置'
        verbose_name_plural = '评分器配置'

    def __str__(self):
        return f'{self.organization.code}/{self.name}({self.grader_type})'


class EvalRun(models.Model):
    """一次评测运行（数据集 × 评分器）。

    扩展（路线三升级 · E1/E2）：支持多裁判聚合（judge_configs）+ 可靠性重复（repeat_k）。
    - repeat_k>1：每个用例执行 k 次，pass_k_rate 为「全成功比例」（Pass^k 可靠性下限，
      对标文章二：Pass@k 衡量能力上限，Pass^k 衡量可靠性下限）。
    - judge_configs（运行时传入的评分器列表）：对同一输出并行多裁判，按 agg_method 聚合。
    """

    STATUS = [
        ('PENDING', '待执行'),
        ('RUNNING', '执行中'),
        ('DONE', '完成'),
        ('FAILED', '失败'),
    ]

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='eval_runs'
    )
    dataset = models.ForeignKey(EvalDataset, on_delete=models.CASCADE)
    grader = models.ForeignKey(GraderConfig, on_delete=models.CASCADE)
    model_config = models.ForeignKey(
        'requirement_analysis.AIModelConfig', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='eval_runs',
        help_text='本次运行实际使用的 LLM 模型配置（仅 LLM 类评分器有）；'
                  '用于跨数据集模型榜单 / 溯源。为 None 表示离线启发式降级（零外送）',
    )
    status = models.CharField(max_length=20, choices=STATUS, default='PENDING')
    is_baseline = models.BooleanField(
        default=False, db_index=True,
        help_text='是否为所属数据集的确定性基线运行（Phase B·B4 基线对比用）',
    )
    # —— E2：可靠性重复 ——
    repeat_k = models.IntegerField(
        default=1, help_text='可靠性重复次数（Pass^k）：每用例执行 k 次，全成功才算通过'
    )
    mean_score = models.FloatField(null=True, blank=True)
    pass_rate = models.FloatField(null=True, blank=True)
    edge_pass_rate = models.FloatField(null=True, blank=True)
    # —— P3-10：能力/回归集分离 ——
    # 按用例角色(case_role)拆分的通过率，类比 edge_pass_rate，仅按角色聚合。
    # None 表示该角色在本运行无用例（不计入门禁分母，避免空角色误判）。
    capability_pass_rate = models.FloatField(
        null=True, blank=True,
        help_text='能力用例(role=CAPABILITY)通过率，按角色拆分；None=无能力用例',
    )
    regression_pass_rate = models.FloatField(
        null=True, blank=True,
        help_text='回归用例(role=REGRESSION)通过率，按角色拆分；None=无回归用例',
    )
    # —— E2：Pass^k 可靠性下限指标 ——
    pass_k_rate = models.FloatField(
        null=True, blank=True,
        help_text='Pass^k 可靠性下限 = 所有用例「k 次全通过」的比例',
    )
    # —— P3-3：Agent-as-Judge 置信度门 ——
    min_confidence = models.FloatField(
        null=True, blank=True, default=None,
        help_text='置信度门阈值；置信度低于此值的用例标记为需人工复核且门禁不通过；None=关闭（向后兼容）',
    )
    # —— P3-2：运行级成本/性能聚合（由 grade_run 汇总各用例，零外送）——
    cost_tokens_total = models.FloatField(
        null=True, blank=True, help_text='运行级 Token 总消耗（各用例 cost_tokens 之和）'
    )
    cost_calls_total = models.IntegerField(
        null=True, blank=True, help_text='运行级工具调用总次数（各用例 cost_calls 之和）'
    )
    latency_avg = models.FloatField(
        null=True, blank=True, help_text='运行级平均端到端时延(秒)'
    )
    latency_max = models.FloatField(
        null=True, blank=True, help_text='运行级最大端到端时延(秒)'
    )
    created_by = models.ForeignKey(
        'core_platform.User', on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    # —— P3-4：评测技能版本（可复现/审计）——
    skill_version = models.ForeignKey(
        'SkillVersion', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='runs',
        help_text='本次运行所使用的评测技能版本快照（eval-flow 等）；None=未绑定',
    )

    class Meta:
        db_table = 'eval_runs'
        verbose_name = '评测运行'
        verbose_name_plural = '评测运行'

    def __str__(self):
        return f'run#{self.id} {self.status}'

    def role_breakdown(self):
        """P3-10：按用例角色（CAPABILITY / REGRESSION）实时拆分通过率。

        供报告（P3-17 分层）与门禁使用；优先读结果表（零外送、与落库一致），
        空角色返回 None（不计入分母）。返回 {capability:{count,pass_rate}, regression:{...}}。
        """
        rows = self.results.select_related('case').all()
        cap = [r for r in rows if getattr(r.case, 'case_role', 'CAPABILITY') == 'CAPABILITY']
        reg = [r for r in rows if getattr(r.case, 'case_role', 'CAPABILITY') == 'REGRESSION']

        def _rate(group):
            if not group:
                return None
            return round(sum(1 for r in group if r.passed) / len(group), 3)

        return {
            'capability': {'count': len(cap), 'pass_rate': _rate(cap)},
            'regression': {'count': len(reg), 'pass_rate': _rate(reg)},
        }


class EvalResult(models.Model):
    """单条用例的评分结果。

    借鉴 One-Eval / Giskard：引入**人机协同复核门**（review_status）。
    LLM 裁判类结果默认待复核，误报/漏报经人工确认后才能作为可信结论，
    阻断"用例预期错误 → 分析误报"的静默传播（见公众号《多Agent协作测试系统实战》）。

    升级扩展（E1 PoLL 多裁判 / E2 Pass^k）：
    - `judges`：多裁判逐裁决（每裁判 {judge,score,passed,reason}）；单裁判时长度为 1。
    - `agg_method` / `agg_score` / `agg_passed`：PoLL 聚合方法与结果（截尾均值/多数决/分歧送审）。
    - `repeat_results` / `pass_k`：可靠性重复的逐次裁决与「k 次全通过」结论。
    `score`/`passed`/`judge`/`reason` 保留为「主裁决」（=聚合/PoLL 结果），
    以保证既有分析/门禁/榜单逻辑（mean_score 等）向后兼容。
    """

    JUDGE_TYPES = [
        ('RULE', '规则匹配'),
        ('LLM_JUDGE', 'LLM 裁判'),
        ('HEURISTIC', '启发式降级'),
        ('POLL', '多裁判聚合'),
    ]

    REVIEW_STATUS = [
        ('PENDING', '待复核'),
        ('APPROVED', '已通过复核'),
        ('REJECTED', '已驳回'),
        ('NEEDS_REVIEW', '需人工复核（多裁判分歧）'),
    ]

    # E1 PoLL 聚合方法
    AGG_METHODS = [
        ('TRIMMED_MEAN', '截尾均值（去极值）'),
        ('MAJORITY', '多数决'),
        ('PANEL_DISAGREE', '分歧送审（黄金样本）'),
    ]

    run = models.ForeignKey(EvalRun, on_delete=models.CASCADE, related_name='results')
    case = models.ForeignKey(EvalCase, on_delete=models.CASCADE)
    score = models.FloatField(help_text='0-1 聚合分数（=agg_score）')
    passed = models.BooleanField(help_text='是否通过（E2 下=Pass^k 结论）')
    judge = models.CharField(max_length=20, choices=JUDGE_TYPES, default='RULE')
    reason = models.TextField(blank=True, help_text='评分理由（强制非空，防静默通过）')

    # —— E1 PoLL 多裁判 ——
    judges = models.JSONField(
        default=list, blank=True,
        help_text='多裁判逐裁决列表：[{judge,score,passed,reason}]；单裁判长度为 1',
    )
    agg_method = models.CharField(
        max_length=20, choices=AGG_METHODS, default='TRIMMED_MEAN',
        help_text='多裁判聚合方法（PoLL：trimmed_mean/majority/panel_disagree）',
    )
    agg_score = models.FloatField(null=True, blank=True, help_text='PoLL 聚合分')
    agg_passed = models.BooleanField(null=True, blank=True, help_text='PoLL 聚合通过')

    # —— E2 Pass^k 可靠性 ——
    repeat_results = models.JSONField(
        default=list, blank=True,
        help_text='可靠性重复的逐次裁决 [{score,passed,judge,reason}]',
    )
    pass_k = models.BooleanField(
        null=True, blank=True, help_text='Pass^k 结论：k 次是否全部通过',
    )

    # —— P3-1 忠实度 + 红线（死循环/幻觉，零容忍硬门）——
    faithfulness_score = models.FloatField(
        null=True, blank=True,
        help_text='忠实度分（P3-1）：0-1；红线命中强制 0',
    )
    red_flags = models.JSONField(
        default=list, blank=True,
        help_text='红线标记列表：dead_loop / hallucination（零容忍，C1 硬门拦截）',
    )
    # —— P3-3：Agent-as-Judge 置信度 ——
    confidence = models.FloatField(
        null=True, blank=True,
        help_text='裁判置信度 0-1（LLM 裁判提供；启发式/规则为 None，不触发门禁）',
    )
    # —— P3-2：成本/性能维度（零外送，从 tool_outputs / trace 提取，不新增外呼）——
    cost_tokens = models.FloatField(
        null=True, blank=True,
        help_text='被测 agent 的 Token 消耗（工具返回值 token_usage 之和）；无可提取为 None',
    )
    cost_calls = models.IntegerField(
        null=True, blank=True,
        help_text='工具调用次数（tool_outputs 长度）；无工具调用为 0',
    )
    latency_first = models.FloatField(
        null=True, blank=True,
        help_text='首 Token 时延(秒)；trace 首个 TOOL 步骤 latency_ms / 1000',
    )
    latency_total = models.FloatField(
        null=True, blank=True,
        help_text='端到端时延(秒)；trace.total_latency_ms / 1000',
    )

    review_status = models.CharField(
        max_length=20, choices=REVIEW_STATUS, default='PENDING',
        help_text='人机协同复核状态；LLM 裁判/多裁判分歧结果默认待复核',
    )
    reviewer = models.ForeignKey(
        'core_platform.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_eval_results',
    )
    review_note = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'eval_results'
        verbose_name = '评测结果'
        verbose_name_plural = '评测结果'
        unique_together = ('run', 'case')


class EvalTrace(models.Model):
    """一次用例执行的步骤级 Trace（M4，路线三 · Phase 2）。

    对齐 Langfuse / One-Eval 的「Trace 观测」概念，但用 Django+Postgres 实现
    （不引 ClickHouse）。一条 Trace 对应一次 (run, case) 的执行过程，用于：
    ① 回放（前端按 step 顺序渲染规划/工具/观察/输出）；
    ② 失败归因——区分「规划弱」与「工具错」（公众号文章关注的错误传播防护）。
    租户隔离经 run__organization 实现（无自有 organization 字段）。
    """

    STATUS = [
        ('OK', '正常完成'),
        ('ERROR', '执行出错'),
    ]

    run = models.ForeignKey(EvalRun, on_delete=models.CASCADE, related_name='traces')
    case = models.ForeignKey(EvalCase, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS, default='OK')
    total_latency_ms = models.IntegerField(null=True, blank=True, help_text='全流程耗时(ms)')
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'eval_traces'
        verbose_name = '评测轨迹'
        verbose_name_plural = '评测轨迹'
        ordering = ('-created_at',)

    def __str__(self):
        return f'trace#{self.id} run={self.run_id} case={self.case_id} {self.status}'


class EvalTraceStep(models.Model):
    """Trace 中的单个步骤观测（规划 / 工具调用 / 观察 / 最终输出 / 错误）。"""

    STEP_TYPES = [
        ('PLAN', '规划'),
        ('TOOL', '工具调用'),
        ('OBSERVE', '观察'),
        ('OUTPUT', '最终输出'),
        ('ERROR', '错误'),
    ]

    trace = models.ForeignKey(EvalTrace, on_delete=models.CASCADE, related_name='steps')
    step_index = models.IntegerField(help_text='步骤序号（从 0 开始）')
    step_type = models.CharField(max_length=20, choices=STEP_TYPES, default='OBSERVE')
    name = models.CharField(max_length=200, blank=True, help_text='步骤名（如工具名/计划标题）')
    input_data = models.JSONField(default=dict, blank=True)
    output_data = models.JSONField(default=dict, blank=True)
    latency_ms = models.IntegerField(null=True, blank=True)
    error = models.TextField(blank=True, help_text='该步骤的错误信息（若有）')

    class Meta:
        db_table = 'eval_trace_steps'
        verbose_name = '轨迹步骤'
        verbose_name_plural = '轨迹步骤'
        ordering = ('step_index',)

    def __str__(self):
        return f'#{self.step_index} {self.step_type} {self.name}'


class EvalEloRating(models.Model):
    """模型竞技 Elo 评分（E3 Pairwise + Elo，文章一）。

    按 (organization, model_name, dataset) 唯一；dataset 为 None 表示跨数据集组织级聚合。
    由 `apps.eval_pod.agents.recompute_elo` 幂等重算（round-robin 同数据集 runs 两两比较，
    按 mean_score 定胜负，标准 Elo 公式更新）。
    """

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='elo_ratings'
    )
    model_name = models.CharField(max_length=200)
    dataset = models.ForeignKey(
        EvalDataset, on_delete=models.SET_NULL, null=True, blank=True,
        help_text='None = 跨数据集组织级聚合',
    )
    rating = models.FloatField(default=1500.0)
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    draws = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'eval_elo_ratings'
        unique_together = ('organization', 'model_name', 'dataset')
        verbose_name = 'Elo 评分'
        verbose_name_plural = 'Elo 评分'

    def __str__(self):
        scope = self.dataset.name if self.dataset else '组织级'
        return f'{self.model_name}@{scope} Elo={self.rating:.0f}'


class BenchmarkTemplate(models.Model):
    """标准 Benchmark 模板（E7，文章二 Benchmark 选型）。

    organization 为 None 表示平台级目录（所有租户可见），租户亦可自建私有模板。
    专测 Pass^k 的基准（如 τ-bench）由 measures_pass_k=True 标记，引导用户在门禁里用
    pass_k_rate 而非 pass_rate。
    """

    SOURCES = [
        ('SWE-BENCH', 'SWE-bench'),
        ('GAIA', 'GAIA'),
        ('WEBARENA', 'WebArena'),
        ('TAU-BENCH', 'τ-bench'),
        ('AGENTBENCH', 'AgentBench'),
        ('OSWORLD', 'OSWorld'),
        ('CUSTOM', '自定义'),
    ]

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='benchmark_templates',
        null=True, blank=True,
        help_text='None = 平台级目录（所有租户可见）',
    )
    key = models.CharField(max_length=60, help_text='模板唯一键，如 swe-bench')
    name = models.CharField(max_length=200)
    source = models.CharField(max_length=30, choices=SOURCES, default='CUSTOM')
    description = models.TextField(blank=True)
    dimensions = models.JSONField(
        default=list, blank=True,
        help_text='评估维度列表，如 ["完成率","工具准确率","规划质量"]',
    )
    measures_pass_k = models.BooleanField(
        default=False, help_text='是否专测 Pass^k（如 τ-bench 的可靠性下限）',
    )
    # 用例骨架：生成数据集时按此模板填充
    case_skeleton = models.JSONField(
        default=list, blank=True,
        help_text='用例骨架 [{input_text, expected, is_edge, meta}]，生成数据集时复制',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'eval_benchmark_templates'
        unique_together = ('organization', 'key')
        verbose_name = 'Benchmark 模板'
        verbose_name_plural = 'Benchmark 模板'

    def __str__(self):
        return f'{self.name}({self.source})'


class EvalPlan(models.Model):
    """P3-14 Copilot 评测方案草稿：自然语言需求 → 结构化方案（存草稿，确认后落地为运行）。

    结构化方案存于 plan_json：{dataset_ids, metrics, gate_thresholds,
    baseline_run_id, repeat_k, mode, llm_used, resolved_grader_ids}。
    确认（confirm）后为每个 dataset 创建 EvalRun（复用 run 设施），run 进入 PENDING，
    由用户经现有执行流程喂入 outputs 完成评分。
    """

    STATUS = [
        ('DRAFT', '草稿'),
        ('CONFIRMED', '已确认'),
        ('CANCELLED', '已取消'),
    ]

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='eval_plans'
    )
    title = models.CharField(max_length=200, help_text='方案标题')
    req_text = models.TextField(help_text='自然语言需求（Copilot 入口输入）')
    plan_json = models.JSONField(
        default=dict, blank=True,
        help_text='结构化方案：dataset_ids/metrics/gate_thresholds/baseline_run_id/repeat_k',
    )
    status = models.CharField(max_length=20, choices=STATUS, default='DRAFT')
    resolved_run_ids = models.JSONField(
        default=list, blank=True,
        help_text='确认后创建的 EvalRun id 列表（复用 run 设施）',
    )
    created_by = models.ForeignKey(
        'core_platform.User', on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'eval_plans'
        ordering = ('-created_at',)
        verbose_name = '评测方案'
        verbose_name_plural = '评测方案'

    def __str__(self):
        return f'plan#{self.id} {self.status} {self.title}'


class KnowledgeDoc(models.Model):
    """P3-13 知识中枢：租户内知识库（需求文档/Confluence/飞书/上传/笔记）。

    用于 RAG 检索辅助 B1 用例生成。纯离线词法检索，零外送、确定性。
    - content 保存时自动分块（agents.build_chunks），chunks 存 [{idx,text,tokens}]；
    - 检索 agents.retrieve_knowledge 在租户 READY 文档的 chunks 上做词法重叠排序，
      无外部 embedding 服务依赖。
    """

    SOURCE_TYPES = [
        ('REQUIREMENT', '需求文档'),
        ('CONFLUENCE', 'Confluence'),
        ('FEISHU', '飞书文档'),
        ('UPLOAD', '上传文件'),
        ('NOTE', '笔记/手动'),
    ]
    STATUS = [
        ('READY', '就绪'),
        ('PROCESSING', '处理中'),
    ]

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='knowledge_docs'
    )
    title = models.CharField(max_length=200, help_text='知识文档标题')
    source_type = models.CharField(
        max_length=20, choices=SOURCE_TYPES, default='NOTE', help_text='来源类型'
    )
    content = models.TextField(help_text='原始知识文本（需求/接口/产品文档正文）')
    chunks = models.JSONField(
        default=list, blank=True, help_text='分块结果 [{idx,text,tokens}]（save 时自动生成）'
    )
    status = models.CharField(max_length=20, choices=STATUS, default='READY')
    created_by = models.ForeignKey(
        'core_platform.User', on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'eval_knowledge_docs'
        ordering = ('-created_at',)
        verbose_name = '知识文档'
        verbose_name_plural = '知识文档'

    def __str__(self):
        return f'kb#{self.id} {self.title}({self.source_type})'

    @property
    def chunk_count(self):
        return len(self.chunks or [])

    def save(self, *args, **kwargs):
        # 内容变化时重算分块（确定性、零外送）
        if self.content:
            from . import agents
            self.chunks = agents.build_chunks(self.content)
            self.status = 'READY'
        super().save(*args, **kwargs)


class EvalSchedule(models.Model):
    """P3-16 定时评测调度（平台内部调度模型）+ IM 通知配置。

    调度定义完全数据化（DB 模型），由 apps/eval_pod/scheduler.tick() 内部守护进程
    周期性扫描到期调度并触发评测运行，不依赖外部 crontab / Celery beat。
    - trigger_type: cron(5 字段) / interval(分钟) / daily(每日 HH:MM)
    - agent_config: 可选，被评测的 agent/模型配置（自动产出 outputs 用；生产经 agent_fn 注入真实调用）
    - notify_channels: [{type:'feishu'|'wecom'|'dingtalk', webhook, secret?, at?}]
    """

    TRIGGER_TYPES = [
        ('cron', 'Cron 表达式'),
        ('interval', '间隔(分钟)'),
        ('daily', '每日定时'),
    ]
    STATUS = [
        ('IDLE', '未运行'),
        ('OK', '成功'),
        ('ERROR', '失败'),
    ]

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='eval_schedules'
    )
    name = models.CharField(max_length=120)
    dataset = models.ForeignKey(EvalDataset, on_delete=models.CASCADE)
    grader = models.ForeignKey(GraderConfig, on_delete=models.CASCADE)
    agent_config = models.ForeignKey(
        'requirement_analysis.AIModelConfig', on_delete=models.SET_NULL, null=True,
        blank=True, related_name='eval_schedules',
        help_text='被评测的 agent/模型配置（可选，用于自动产出 outputs）',
    )
    trigger_type = models.CharField(max_length=20, choices=TRIGGER_TYPES, default='interval')
    cron = models.CharField(
        max_length=120, blank=True, help_text='5 字段 cron 表达式（trigger_type=cron）'
    )
    interval_minutes = models.IntegerField(
        null=True, blank=True, help_text='间隔分钟数（trigger_type=interval）'
    )
    daily_at = models.CharField(
        max_length=8, blank=True, help_text='每日触发时间 HH:MM（trigger_type=daily）'
    )
    timezone_name = models.CharField(max_length=40, default='Asia/Shanghai', blank=True)
    notify_channels = models.JSONField(
        default=list, blank=True,
        help_text='IM 通知渠道列表 [{type, webhook, secret?, at?}]',
    )
    enabled = models.BooleanField(default=True, db_index=True)
    repeat_k = models.IntegerField(default=1)
    min_confidence = models.FloatField(null=True, blank=True, default=None)
    last_run_at = models.DateTimeField(null=True, blank=True)
    last_run_id = models.IntegerField(null=True, blank=True)
    last_status = models.CharField(max_length=20, choices=STATUS, default='IDLE', blank=True)
    last_error = models.TextField(blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_by = models.ForeignKey(
        'core_platform.User', on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'eval_schedules'
        ordering = ('-created_at',)
        verbose_name = '定时评测调度'
        verbose_name_plural = '定时评测调度'

    def __str__(self):
        return f'sched#{self.id} {self.name}'

    def compute_next_run(self, from_time):
        """根据触发类型计算下一次运行时间（from_time 为 aware datetime）。"""
        from datetime import timedelta
        if self.trigger_type == 'interval':
            minutes = self.interval_minutes or 60
            return from_time + timedelta(minutes=minutes)
        if self.trigger_type == 'daily':
            if not self.daily_at:
                return None
            hh, mm = (int(x) for x in self.daily_at.split(':'))
            cand = from_time.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if cand <= from_time:
                cand = cand + timedelta(days=1)
            return cand
        if self.trigger_type == 'cron':
            if not self.cron:
                return None
            try:
                from croniter import croniter
                return croniter(self.cron, from_time).get_next(type(from_time))
            except Exception:
                return None
        return None

    def save(self, *args, **kwargs):
        if self.next_run_at is None:
            self.next_run_at = self.compute_next_run(timezone.now())
        super().save(*args, **kwargs)


class SkillVersion(models.Model):
    """评测技能版本快照（P3-4 Skill版本化）。

    平台把评测流封装为可复用 skill（对标《Eval-Anything：评测即 skill》——
    SKILL.md + references + workflows + templates 三层结构）。为保证评测的
    **可复现性与可审计性**，每次运行绑定其所使用的技能版本快照：
    - publish：把磁盘 SKILL.md（或自定义 content）固化为一个不可变版本；
    - active_for(org, key)：取当前生效版本（租户优先，回退平台级）；
    - EvalRun.skill_version 记录运行时刻实际使用的版本。
    """

    SKILL_DIR = os.path.join(os.path.dirname(__file__), 'skills')

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, null=True, blank=True,
        related_name='skill_versions',
        help_text='所属租户；None 表示平台级（全局）技能',
    )
    skill_key = models.CharField(max_length=80, db_index=True, help_text='技能标识，如 eval-flow')
    version = models.CharField(max_length=40, help_text='版本号，如 1.0 / 1.1')
    content = models.TextField(help_text='技能内容快照（SKILL.md 原始文本）')
    content_hash = models.CharField(max_length=64, db_index=True,
                                    help_text='content 的 sha256，用于去重/差异')
    is_active = models.BooleanField(default=False, db_index=True,
                                    help_text='是否为当前生效版本')
    note = models.CharField(max_length=255, blank=True, default='', help_text='发布说明')
    created_by = models.ForeignKey(
        'core_platform.User', on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'eval_skill_versions'
        verbose_name = '评测技能版本'
        verbose_name_plural = '评测技能版本'
        unique_together = (('organization', 'skill_key', 'version'),)
        ordering = ('-created_at',)

    def __str__(self):
        scope = self.organization.code if self.organization else 'global'
        return f'{self.skill_key}@{self.version} ({scope})'

    @staticmethod
    def _hash(content):
        import hashlib
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    @classmethod
    def disk_content(cls, skill_key):
        """读取磁盘 skills/<skill_key>/SKILL.md 当前内容；不存在返回 None。"""
        path = os.path.join(cls.SKILL_DIR, skill_key, 'SKILL.md')
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    @classmethod
    def suggest_version(cls, organization, skill_key):
        """建议下一版本号：取同 scope+key 的最大语义版本 +0.1。"""
        qs = cls.objects.filter(skill_key=skill_key)
        if organization is not None:
            qs = qs.filter(
                models.Q(organization=organization) | models.Q(organization__isnull=True)
            )
        latest = qs.exclude(version__isnull=True).order_by('-created_at').first()
        if not latest:
            return '1.0'
        try:
            base = float(latest.version)
            return f'{base + 0.1:.1f}'
        except ValueError:
            return '1.0'

    @classmethod
    def active_for(cls, organization, skill_key):
        """当前生效版本：优先租户级，回退平台级（organization=None）。"""
        v = cls.objects.filter(
            skill_key=skill_key, is_active=True, organization=organization
        ).first()
        if v:
            return v
        return cls.objects.filter(
            skill_key=skill_key, is_active=True, organization__isnull=True
        ).first()

    def set_active(self):
        """原子地将该版本设为生效，并取消同 scope+key 下其他版本的 active。"""
        type(self).objects.filter(
            skill_key=self.skill_key, organization=self.organization, is_active=True
        ).update(is_active=False)
        self.is_active = True
        self.save(update_fields=['is_active'])


class JudgeStrengthRecord(models.Model):
    """P3-11 评判模型强度校准记录：被评估裁判模型与金标准的一致性快照。

    由 JudgeStrengthViewSet.assess 触发（走本租户 AIModelConfig，数据不出域），
    每次评估落一条记录，供前端展示「裁判可信度」趋势，并作为门禁/复核的可选依据
    （弱裁判 → 评级降权、建议人工复核）。
    """

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='judge_strengths'
    )
    model_name = models.CharField(
        max_length=200, help_text='被评估的评判模型名（AIModelConfig.model_name）'
    )
    strength_score = models.FloatField(
        help_text='与金标准一致性 0-1；越高代表裁判越可信'
    )
    agreement = models.IntegerField(help_text='与金标准一致的样本数')
    sample_size = models.IntegerField(help_text='校准样本总数（金标准集大小）')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'eval_judge_strengths'
        ordering = ('-created_at',)
        verbose_name = '评判模型强度记录'
        verbose_name_plural = '评判模型强度记录'

    def __str__(self):
        return f'{self.organization.code}/{self.model_name} strength={self.strength_score}'

