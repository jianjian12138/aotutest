"""
租户功能开关（路线三 · Phase 0 权限制高点）。

解决甲方核心关切：当某甲方（租户）不需要 Agent 测评 / LLM 测试 等能力时，
通过租户级开关使其"不可见、不可调用、不计费"，且不触发任何数据出域。

与现有 RBAC（角色/组织）正交：
- RBAC 管"谁能操作"（角色、组织归属）；
- TenantFeature 管"该租户是否拥有/开通此能力"（产品订阅维度）。
两者叠加生效。
"""
from django.db import models
from django.utils import timezone

from apps.core_platform.models import Organization


class FeatureCode:
    AGENT_EVAL = 'AGENT_EVAL'                  # Agent 测评（主）
    LLM_TEST = 'LLM_TEST'                      # LLM 测试（主）
    AGENTIC_AUTOMATION = 'AGENTIC_AUTOMATION'  # 智能体自动化测试（辅）


class TenantFeature(models.Model):
    FEATURE_CHOICES = [
        (FeatureCode.AGENT_EVAL, 'Agent 测评'),
        (FeatureCode.LLM_TEST, 'LLM 测试'),
        (FeatureCode.AGENTIC_AUTOMATION, '智能体自动化测试'),
    ]

    tenant = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='features',
        help_text='所属租户/组织',
    )
    feature_code = models.CharField(max_length=40, choices=FEATURE_CHOICES, db_index=True)
    enabled = models.BooleanField(default=False, help_text='是否对本租户开通')
    quota = models.IntegerField(
        null=True, blank=True, help_text='可选配额（如 LLM 调用次数/月），NULL 表示不限'
    )
    expires_at = models.DateTimeField(
        null=True, blank=True, help_text='能力有效期；NULL 表示长期有效'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tenant_features'
        unique_together = ('tenant', 'feature_code')
        verbose_name = '租户功能开关'
        verbose_name_plural = '租户功能开关'

    def __str__(self):
        return f'{self.tenant.code}:{self.feature_code}={self.enabled}'

    @property
    def feature_name(self):
        return dict(self.FEATURE_CHOICES).get(self.feature_code, self.feature_code)

    @property
    def is_active(self):
        """是否真正可用：已开通且未过期。"""
        if not self.enabled:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True
