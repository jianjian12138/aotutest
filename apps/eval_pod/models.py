"""
评测舱数据模型（路线三 · Phase 2 · M2 数据集管理）。

设计原则（对应评审报告 / 路线图）：
- 与现有传统自动化模型（testcase / testsuite / 执行记录）**完全解耦**，
  不污染存量客户数据与语义。
- 所有核心模型均带 organization（租户）外键，配合 TenantAwareViewSetMixin
  实现严格租户隔离（无平台"超级读者"）。
- EvalCase.is_edge 标记边缘用例，强制数据集质量（路线图要求 ≥30% 边缘用例）。
"""
from django.db import models

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
    """评测用例：输入 + 期望（含边缘用例标记）。"""

    dataset = models.ForeignKey(
        EvalDataset, on_delete=models.CASCADE, related_name='cases'
    )
    input_text = models.TextField(help_text='被测模型/智能体的输入或提示')
    expected = models.TextField(blank=True, help_text='期望输出 / 参考答案')
    is_edge = models.BooleanField(
        default=False, help_text='是否为边缘用例（异常输入、对抗样本、长尾场景等）'
    )
    meta = models.JSONField(default=dict, blank=True, help_text='额外元数据')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'eval_cases'
        verbose_name = '评测用例'
        verbose_name_plural = '评测用例'

    def __str__(self):
        return f'#{self.id} edge={self.is_edge}'


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
    """一次评测运行（数据集 × 评分器）。"""

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
    status = models.CharField(max_length=20, choices=STATUS, default='PENDING')
    mean_score = models.FloatField(null=True, blank=True)
    pass_rate = models.FloatField(null=True, blank=True)
    edge_pass_rate = models.FloatField(null=True, blank=True)
    created_by = models.ForeignKey(
        'core_platform.User', on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'eval_runs'
        verbose_name = '评测运行'
        verbose_name_plural = '评测运行'

    def __str__(self):
        return f'run#{self.id} {self.status}'


class EvalResult(models.Model):
    """单条用例的评分结果。

    借鉴 One-Eval / Giskard：引入**人机协同复核门**（review_status）。
    LLM 裁判类结果默认待复核，误报/漏报经人工确认后才能作为可信结论，
    阻断"用例预期错误 → 分析误报"的静默传播（见公众号《多Agent协作测试系统实战》）。
    """

    JUDGE_TYPES = [
        ('RULE', '规则匹配'),
        ('LLM_JUDGE', 'LLM 裁判'),
        ('HEURISTIC', '启发式降级'),
    ]

    REVIEW_STATUS = [
        ('PENDING', '待复核'),
        ('APPROVED', '已通过复核'),
        ('REJECTED', '已驳回'),
    ]

    run = models.ForeignKey(EvalRun, on_delete=models.CASCADE, related_name='results')
    case = models.ForeignKey(EvalCase, on_delete=models.CASCADE)
    score = models.FloatField(help_text='0-1 分数')
    passed = models.BooleanField()
    judge = models.CharField(max_length=20, choices=JUDGE_TYPES, default='RULE')
    reason = models.TextField(blank=True, help_text='评分理由（强制非空，防静默通过）')

    review_status = models.CharField(
        max_length=20, choices=REVIEW_STATUS, default='PENDING',
        help_text='人机协同复核状态；LLM 裁判类结果默认待复核',
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
