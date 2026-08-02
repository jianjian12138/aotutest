"""阶段1.4 缺陷跟踪模型。

状态机（显式定义，见 TRANSITIONS）：
    NEW → OPEN → FIXING → VERIFIED → CLOSED
                   ↘ REJECTED          ↘ REOPENED → OPEN
缺陷可关联：测试执行用例(TestRunCase) / API 执行(ApiTestCaseExecution) / 项目。
租户隔离继承 TenantScopedModel；关联 TestRunCase.defects(JSON 列表) 以
保持 reports 模块的向后兼容读取。
"""
from django.db import models
from django.utils import timezone
from django.conf import settings
from apps.core_platform.models import BaseModel, TenantScopedModel

# ============================================================
# 缺陷状态机
# ============================================================
STATUS_NEW = 'NEW'
STATUS_OPEN = 'OPEN'
STATUS_FIXING = 'FIXING'
STATUS_VERIFIED = 'VERIFIED'
STATUS_CLOSED = 'CLOSED'
STATUS_REJECTED = 'REJECTED'
STATUS_REOPENED = 'REOPENED'

DEFECT_STATUS_CHOICES = [
    (STATUS_NEW, '新建'),
    (STATUS_OPEN, '待修复'),
    (STATUS_FIXING, '修复中'),
    (STATUS_VERIFIED, '待验证'),
    (STATUS_CLOSED, '已关闭'),
    (STATUS_REJECTED, '已拒绝'),
    (STATUS_REOPENED, '重新打开'),
]

# 状态流转白名单：from_status -> {允许到达的 to_status}
TRANSITIONS = {
    STATUS_NEW: {STATUS_OPEN, STATUS_REJECTED, STATUS_FIXING},
    STATUS_OPEN: {STATUS_FIXING, STATUS_REJECTED, STATUS_REOPENED},
    STATUS_FIXING: {STATUS_VERIFIED, STATUS_OPEN, STATUS_REOPENED},
    STATUS_VERIFIED: {STATUS_CLOSED, STATUS_REOPENED},
    STATUS_CLOSED: {STATUS_REOPENED},
    STATUS_REJECTED: {STATUS_OPEN, STATUS_REOPENED},
    STATUS_REOPENED: {STATUS_OPEN, STATUS_FIXING},
}

SEVERITY_CHOICES = [
    ('critical', '致命'),
    ('major', '严重'),
    ('minor', '一般'),
    ('trivial', '轻微'),
]

PRIORITY_CHOICES = [
    ('P0', 'P0-最高'),
    ('P1', 'P1-高'),
    ('P2', 'P2-中'),
    ('P3', 'P3-低'),
]


class Defect(TenantScopedModel):
    title = models.CharField(max_length=255, verbose_name='缺陷标题')
    description = models.TextField(blank=True, verbose_name='缺陷描述')
    steps = models.TextField(blank=True, verbose_name='复现步骤')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='major', verbose_name='严重程度')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='P2', verbose_name='优先级')
    status = models.CharField(max_length=20, choices=DEFECT_STATUS_CHOICES, default=STATUS_NEW, verbose_name='状态', db_index=True)

    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reported_defects', verbose_name='报告人')
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_defects', verbose_name='指派给')

    project = models.ForeignKey('core_platform.Project', on_delete=models.SET_NULL, null=True, blank=True, related_name='defects', verbose_name='所属项目')
    related_execution = models.ForeignKey('executions.TestRunCase', on_delete=models.SET_NULL, null=True, blank=True, related_name='defect_links', verbose_name='关联测试执行')
    related_api_execution = models.ForeignKey('api_testing.ApiTestCaseExecution', on_delete=models.SET_NULL, null=True, blank=True, related_name='defect_links', verbose_name='关联API执行')
    related_case_info = models.CharField(max_length=255, blank=True, verbose_name='关联用例标识(文本)')

    environment = models.CharField(max_length=100, blank=True, verbose_name='环境')
    attachments = models.JSONField(default=list, blank=True, verbose_name='附件')
    extra = models.JSONField(default=dict, blank=True, verbose_name='扩展信息')

    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'defects_defect'
        verbose_name = '缺陷'
        verbose_name_plural = '缺陷'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['severity', '-created_at']),
            models.Index(fields=['assignee', 'status']),
        ]

    def __str__(self):
        return f"#{self.id} {self.title} [{self.status}]"

    # ---------- 状态机 ----------
    def can_transition(self, to_status):
        if to_status == self.status:
            return True
        allowed = TRANSITIONS.get(self.status, set())
        return to_status in allowed

    def apply_transition(self, to_status, user=None, comment=''):
        """
        执行状态流转。非法流转抛出 ValueError。
        同步写 DefectHistory；并维护关联 TestRunCase.defects 列表的向后兼容。
        """
        if not self.can_transition(to_status):
            raise ValueError(
                f"非法状态流转：{self.status} → {to_status}（允许：{sorted(TRANSITIONS.get(self.status, set()))}）"
            )
        from_status = self.status
        self.status = to_status
        self.save(update_fields=['status', 'updated_at'])

        DefectHistory.objects.create(
            defect=self, from_status=from_status, to_status=to_status,
            actor=user, comment=comment,
        )

        # 向后兼容：维护 TestRunCase.defects JSON 列表
        if self.related_execution_id:
            from django.apps import apps
            TestRunCase = apps.get_model('executions', 'TestRunCase')
            try:
                trc = TestRunCase.objects.get(pk=self.related_execution_id)
                ids = list(trc.defects or [])
                did = str(self.id)
                if to_status == STATUS_CLOSED and did in ids:
                    ids.remove(did)
                elif to_status != STATUS_CLOSED and did not in ids:
                    ids.append(did)
                trc.defects = ids
                trc.save(update_fields=['defects'])
            except TestRunCase.DoesNotExist:
                pass

        return self


class DefectHistory(models.Model):
    """缺陷状态流转历史（审计 + 通知依据）。"""
    defect = models.ForeignKey(Defect, on_delete=models.CASCADE, related_name='history', verbose_name='缺陷')
    from_status = models.CharField(max_length=20, choices=DEFECT_STATUS_CHOICES, blank=True, verbose_name='原状态')
    to_status = models.CharField(max_length=20, choices=DEFECT_STATUS_CHOICES, verbose_name='目标状态')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='操作人')
    comment = models.TextField(blank=True, verbose_name='流转说明')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='时间')

    class Meta:
        db_table = 'defects_history'
        verbose_name = '缺陷流转历史'
        verbose_name_plural = '缺陷流转历史'
        ordering = ['-created_at']

    def __str__(self):
        return f"#{self.defect_id} {self.from_status}→{self.to_status}"
