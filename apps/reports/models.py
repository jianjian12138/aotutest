from django.db import models
from django.utils import timezone
from apps.core_platform.models import User
from apps.core_platform.models import Project
from apps.executions.models import TestRun
from apps.api_testing.models import ApiTestCaseExecution

class TestReport(models.Model):
    """测试报告"""
    TYPE_CHOICES = [
        ('execution', '执行报告'),
        ('summary', '汇总报告'),
        ('trend', '趋势报告'),
        ('api_execution', 'API测试报告'),
        ('ui_execution', 'UI自动化报告'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='reports', db_index=True)
    name = models.CharField(max_length=200, verbose_name='报告名称')
    report_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='execution', verbose_name='报告类型')
    execution = models.OneToOneField(TestRun, on_delete=models.CASCADE, null=True, blank=True, related_name='report', verbose_name='关联执行', db_index=True)
    api_test_execution = models.ForeignKey(ApiTestCaseExecution, on_delete=models.CASCADE, null=True, blank=True, related_name='reports', verbose_name='关联API测试执行', db_index=True)
    api_test_suite_execution = models.ForeignKey('api_testing.TestExecution', on_delete=models.CASCADE, null=True, blank=True, related_name='reports', verbose_name='关联API套件执行', db_index=True)
    ui_test_execution = models.ForeignKey('ui_automation.TestExecution', on_delete=models.CASCADE, null=True, blank=True, related_name='reports', verbose_name='关联UI测试执行', db_index=True)
    allure_url = models.CharField(max_length=500, null=True, blank=True, verbose_name='Allure报告链接')
    summary = models.JSONField(default=dict, verbose_name='报告摘要')
    content = models.JSONField(default=dict, verbose_name='报告内容')
    # AI 分析结果
    ai_analysis_result = models.TextField(null=True, blank=True, verbose_name='AI分析总结')
    ai_suggestions = models.TextField(null=True, blank=True, verbose_name='AI修复建议')
    ai_analyzed_at = models.DateTimeField(null=True, blank=True, verbose_name='AI分析时间')
    
    generated_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='生成者', db_index=True)
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间', db_index=True)
    
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
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='创建者', db_index=True)
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间', db_index=True)
    
    class Meta:
        db_table = 'report_templates'
        verbose_name = '报告模板'
        verbose_name_plural = '报告模板'