from apps.notifications.models import NotificationConfig
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()
from django.utils import timezone
import json
from .project import UiProject, TestEnvironment
from .script import TestScript
from .testcase import TestCase

class TestSuite(models.Model):
    """测试套件模型"""
    EXECUTION_STATUS_CHOICES = [
        ('not_run', '未执行'),
        ('passed', '通过'),
        ('failed', '失败'),
        ('running', '执行中'),
    ]

    project = models.ForeignKey(UiProject, on_delete=models.CASCADE, related_name='test_suites', verbose_name='所属项目')
    name = models.CharField(max_length=200, verbose_name='套件名称')
    description = models.TextField(blank=True, verbose_name='套件描述')
    scripts = models.ManyToManyField(TestScript, through='TestSuiteScript', verbose_name='测试脚本')
    test_cases = models.ManyToManyField('TestCase', through='TestSuiteTestCase', verbose_name='测试用例', blank=True)

    # 执行统计字段
    execution_status = models.CharField(max_length=20, choices=EXECUTION_STATUS_CHOICES, default='not_run', verbose_name='执行状态')
    passed_count = models.IntegerField(default=0, verbose_name='通过数')
    failed_count = models.IntegerField(default=0, verbose_name='失败数')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'ui_test_suites'
        verbose_name = 'UI测试套件'
        verbose_name_plural = 'UI测试套件'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class TestSuiteScript(models.Model):
    """测试套件与测试脚本的关联模型"""
    test_suite = models.ForeignKey(TestSuite, on_delete=models.CASCADE, related_name='suite_scripts', verbose_name='测试套件')
    test_script = models.ForeignKey(TestScript, on_delete=models.CASCADE, verbose_name='测试脚本')
    order = models.IntegerField(default=0, verbose_name='执行顺序')

    class Meta:
        db_table = 'ui_test_suite_scripts'
        verbose_name = '测试套件脚本关联'
        verbose_name_plural = '测试套件脚本关联'
        ordering = ['order']


class TestSuiteTestCase(models.Model):
    """测试套件与测试用例的关联模型"""
    test_suite = models.ForeignKey(TestSuite, on_delete=models.CASCADE, related_name='suite_test_cases', verbose_name='测试套件')
    test_case = models.ForeignKey('TestCase', on_delete=models.CASCADE, verbose_name='测试用例')
    order = models.IntegerField(default=0, verbose_name='执行顺序')

    class Meta:
        db_table = 'ui_test_suite_test_cases'
        verbose_name = '测试套件用例关联'
        verbose_name_plural = '测试套件用例关联'
        ordering = ['order']
        unique_together = ['test_suite', 'test_case']

    def __str__(self):
        return f'{self.test_suite.name} - {self.test_case.name}'


class TestExecution(models.Model):
    """测试执行记录模型"""
    STATUS_CHOICES = [
        ('PENDING', '待执行'),
        ('RUNNING', '运行中'),
        ('SUCCESS', '成功'),
        ('FAILED', '失败'),
        ('ABORTED', '中止'),
    ]

    AI_RCA_STATUS_CHOICES = [
        ('PENDING', '待诊断'),
        ('ANALYZING', '诊断中'),
        ('SUCCESS', '诊断完成'),
        ('FAILED', '诊断失败'),
        ('UNNECESSARY', '无需诊断'),
    ]

    ENVIRONMENT_CHOICES = [
        ('CHROME', 'Chrome'),
        ('FIREFOX', 'Firefox'),
        ('SAFARI', 'Safari'),
        ('EDGE', 'Edge'),
        ('IE', 'IE'),
    ]

    project = models.ForeignKey(UiProject, on_delete=models.CASCADE, related_name='executions', verbose_name='所属项目')
    test_suite = models.ForeignKey(TestSuite, on_delete=models.CASCADE, related_name='executions', null=True, blank=True, verbose_name='测试套件')
    test_script = models.ForeignKey(TestScript, on_delete=models.CASCADE, related_name='executions', null=True, blank=True, verbose_name='测试脚本')
    environment = models.CharField(max_length=20, choices=ENVIRONMENT_CHOICES, verbose_name='执行环境', default='CHROME')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name='执行状态', default='PENDING')
    ai_rca_status = models.CharField(max_length=20, choices=AI_RCA_STATUS_CHOICES, default='PENDING', verbose_name='AI根因分析状态')
    ai_rca_result = models.TextField(null=True, blank=True, verbose_name='AI根因分析结果')

    # 执行统计
    total_cases = models.IntegerField(default=0, verbose_name='总用例数')
    passed_cases = models.IntegerField(default=0, verbose_name='通过用例数')
    failed_cases = models.IntegerField(default=0, verbose_name='失败用例数')
    skipped_cases = models.IntegerField(default=0, verbose_name='跳过用例数')

    # 时间信息
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    duration = models.FloatField(default=0, verbose_name='执行时长(秒)')

    # 执行人员和配置
    executed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ui_test_executions', verbose_name='执行人员')
    engine = models.CharField(max_length=20, default='playwright', verbose_name='测试引擎')
    browser = models.CharField(max_length=20, default='chrome', verbose_name='浏览器')
    headless = models.BooleanField(default=False, verbose_name='无头模式')

    # 结果数据
    result_data = models.JSONField(blank=True, null=True, verbose_name='执行结果数据')
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    report_url = models.CharField(max_length=500, blank=True, verbose_name='报告URL')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'ui_test_executions'
        verbose_name = 'UI测试执行记录'
        verbose_name_plural = 'UI测试执行记录'
        ordering = ['-created_at']

    def __str__(self):
        if self.test_suite:
            return f'Suite: {self.test_suite.name} - {self.get_status_display()}'
        elif self.test_script:
            return f'Script: {self.test_script.name} - {self.get_status_display()}'
        return f'Execution #{self.id}'

    @property
    def pass_rate(self):
        """计算通过率"""
        if self.total_cases == 0:
            return 0
        return round((self.passed_cases / self.total_cases) * 100, 2)


class Screenshot(models.Model):
    """截图模型"""
    execution = models.ForeignKey(TestExecution, on_delete=models.CASCADE, related_name='screenshots', verbose_name='测试执行')
    name = models.CharField(max_length=200, verbose_name='截图名称')
    image = models.ImageField(upload_to='ui_screenshots/', verbose_name='截图文件')
    description = models.TextField(blank=True, verbose_name='截图描述')
    captured_at = models.DateTimeField(auto_now_add=True, verbose_name='捕获时间')

    class Meta:
        db_table = 'ui_screenshots'
        verbose_name = 'UI截图'
        verbose_name_plural = 'UI截图'
        ordering = ['-captured_at']

    def __str__(self):
        return self.name


class OperationRecord(models.Model):
    """操作记录模型"""
    OPERATION_TYPE_CHOICES = [
        ('create', '新增'),
        ('edit', '编辑'),
        ('delete', '删除'),
        ('run', '运行'),
        ('rerun', '重新运行'),
        ('save', '保存'),
        ('rename', '重命名'),
    ]

    RESOURCE_TYPE_CHOICES = [
        ('project', '项目'),
        ('element', '元素'),
        ('test_case', '测试用例'),
        ('script', '脚本'),
        ('suite', '套件'),
        ('execution', '执行记录'),
        ('report', '测试报告'),
    ]

    operation_type = models.CharField(max_length=20, choices=OPERATION_TYPE_CHOICES, verbose_name='操作类型')
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPE_CHOICES, verbose_name='资源类型')
    resource_id = models.IntegerField(verbose_name='资源ID')
    resource_name = models.CharField(max_length=200, verbose_name='资源名称')
    description = models.TextField(verbose_name='操作描述')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='操作用户')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'ui_operation_record'
        verbose_name = 'UI操作记录'
        verbose_name_plural = 'UI操作记录'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.get_operation_type_display()} - {self.resource_name}"


