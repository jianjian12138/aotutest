from django.db import models
from django.utils import timezone
from apps.users.models import User
from apps.projects.models import Project
from apps.executions.models import TestRun

class TestReport(models.Model):
    """测试报告"""
    TYPE_CHOICES = [
        ('execution', '执行报告'),
        ('summary', '汇总报告'),
        ('trend', '趋势报告'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='reports')
    name = models.CharField(max_length=200, verbose_name='报告名称')
    report_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='execution', verbose_name='报告类型')
    execution = models.OneToOneField(TestRun, on_delete=models.CASCADE, null=True, blank=True, related_name='report', verbose_name='关联执行')
    summary = models.JSONField(default=dict, verbose_name='报告摘要')
    content = models.JSONField(default=dict, verbose_name='报告内容')
    generated_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='生成者')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    
    class Meta:
        db_table = 'test_reports'
        verbose_name = '测试报告'
        verbose_name_plural = '测试报告'
        ordering = ['-created_at']

class ReportTemplate(models.Model):
    """报告模板"""
    name = models.CharField(max_length=200, verbose_name='模板名称')
    description = models.TextField(blank=True, verbose_name='模板描述')
    template_config = models.JSONField(default=dict, verbose_name='模板配置')
    is_default = models.BooleanField(default=False, verbose_name='是否默认')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='创建者')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    
    class Meta:
        db_table = 'report_templates'
        verbose_name = '报告模板'
        verbose_name_plural = '报告模板'