from apps.notifications.models import NotificationConfig
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()
from django.utils import timezone
import json
from .project import UiProject
from .element import Element, PageObject, LocatorStrategy

class UiTestCaseModule(models.Model):
    """UI测试用例模块模型"""
    project = models.ForeignKey(UiProject, on_delete=models.CASCADE, related_name='test_case_modules', verbose_name='所属项目')
    name = models.CharField(max_length=200, verbose_name='模块名称')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children', verbose_name='父模块')
    order = models.IntegerField(default=0, verbose_name='排序')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'ui_test_case_modules'
        verbose_name = 'UI测试用例模块'
        verbose_name_plural = 'UI测试用例模块'
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.name


class TestCase(models.Model):
    """UI自动化测试用例模型"""
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('ready', '就绪'),
        ('running', '执行中'),
        ('passed', '通过'),
        ('failed', '失败'),
    ]

    PRIORITY_CHOICES = [
        ('high', '高'),
        ('medium', '中'),
        ('low', '低'),
    ]

    name = models.CharField(max_length=200, verbose_name='用例名称')
    description = models.TextField(blank=True, verbose_name='用例描述')
    project = models.ForeignKey(UiProject, on_delete=models.CASCADE, related_name='test_cases', verbose_name='所属项目')
    module = models.ForeignKey(UiTestCaseModule, on_delete=models.SET_NULL, null=True, blank=True, related_name='test_cases', verbose_name='所属模块')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='状态')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', verbose_name='优先级')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_test_cases', verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'ui_test_cases'
        verbose_name = 'UI测试用例'
        verbose_name_plural = 'UI测试用例'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class TestCaseStep(models.Model):
    """测试用例步骤模型"""
    ACTION_TYPE_CHOICES = [
        ('click', '点击'),
        ('fill', '输入文本'),
        ('getText', '获取文本'),
        ('waitFor', '等待元素'),
        ('hover', '悬停'),
        ('scroll', '滚动'),
        ('screenshot', '截图'),
        ('assert', '断言'),
        ('wait', '等待'),
        ('switchTab', '切换标签页'),
        ('urlJump', 'URL跳转'),
        ('urlExtract', 'URL提取'),
        ('ai_act', 'AI智能操作'),
        ('ai_extract', 'AI智能提取'),
        ('ai_vision', 'AI视觉操作(Magnitude)'),
        ('dragAndDrop', '拖拽'),
        ('upload', '文件上传'),
        ('custom', '自定义'),
    ]

    ASSERT_TYPE_CHOICES = [
        ('textContains', '文本包含'),
        ('textEquals', '文本等于'),
        ('isVisible', '元素可见'),
        ('exists', '元素存在'),
        ('hasAttribute', '属性值'),
        ('urlContains', 'URL包含'),
        ('urlEquals', 'URL等于'),
    ]

    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE, related_name='steps', verbose_name='测试用例')
    step_number = models.IntegerField(verbose_name='步骤序号')
    action_type = models.CharField(max_length=20, choices=ACTION_TYPE_CHOICES, verbose_name='操作类型')
    element = models.ForeignKey(Element, on_delete=models.CASCADE, null=True, blank=True, verbose_name='目标元素')
    input_value = models.TextField(blank=True, verbose_name='输入值')
    wait_time = models.IntegerField(default=1000, verbose_name='等待时间(毫秒)')
    assert_type = models.CharField(max_length=20, choices=ASSERT_TYPE_CHOICES, blank=True, verbose_name='断言类型')
    assert_value = models.TextField(blank=True, verbose_name='断言期望值')
    description = models.TextField(blank=True, verbose_name='步骤描述')
    enable_debug_capture = models.BooleanField(default=False, verbose_name='启用调试采集')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'ui_test_case_steps'
        verbose_name = 'UI测试用例步骤'
        verbose_name_plural = 'UI测试用例步骤'
        ordering = ['step_number']
        unique_together = ['test_case', 'step_number']

    def __str__(self):
        return f"{self.test_case.name} - 步骤{self.step_number}"


class TestCaseExecution(models.Model):
    """测试用例执行记录模型"""
    STATUS_CHOICES = [
        ('pending', '待执行'),
        ('running', '执行中'),
        ('passed', '通过'),
        ('failed', '失败'),
        ('error', '错误'),
    ]

    ENGINE_CHOICES = [
        ('playwright', 'Playwright'),
        ('selenium', 'Selenium'),
        ('appium', 'Appium'),
        ('airtest', 'Airtest'),
        ('minium', 'Minium'),
    ]

    SOURCE_CHOICES = [
        ('manual', '单用例执行'),
        ('suite', '套件执行'),
        ('scheduled', '定时任务执行'),
    ]

    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE, related_name='executions', verbose_name='测试用例')
    project = models.ForeignKey(UiProject, on_delete=models.CASCADE, related_name='test_case_executions', verbose_name='项目')
    test_suite = models.ForeignKey('TestSuite', on_delete=models.CASCADE, null=True, blank=True, related_name='case_executions', verbose_name='所属测试套件')
    execution_source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='manual', verbose_name='执行来源')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='执行状态')
    engine = models.CharField(max_length=20, choices=ENGINE_CHOICES, default='playwright', verbose_name='测试引擎')
    browser = models.CharField(max_length=50, default='chrome', verbose_name='浏览器')
    headless = models.BooleanField(default=False, verbose_name='无头模式')
    execution_logs = models.TextField(blank=True, verbose_name='执行日志')
    error_message = models.TextField(null=True, blank=True, verbose_name='错误信息')
    screenshots = models.JSONField(default=list, blank=True, verbose_name='截图列表')
    execution_time = models.FloatField(null=True, blank=True, verbose_name='执行时长(秒)')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_case_executions', verbose_name='执行人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'ui_test_case_executions'
        verbose_name = 'UI测试用例执行记录'
        verbose_name_plural = 'UI测试用例执行记录'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.test_case.name} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"


class AICase(models.Model):
    """AI测试用例"""
    project = models.ForeignKey(UiProject, on_delete=models.CASCADE, verbose_name='所属项目')
    name = models.CharField(max_length=200, verbose_name='用例名称')
    description = models.TextField(blank=True, null=True, verbose_name='描述')
    task_description = models.TextField(verbose_name='任务描述', help_text='自然语言任务描述')
    execution_mode = models.CharField(max_length=20, choices=[('web', 'Web'), ('mobile', 'Mobile'), ('api', 'API')], default='web', verbose_name='执行模式')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='创建者')

    class Meta:
        db_table = 'ui_ai_cases'
        verbose_name = 'AI测试用例'
        verbose_name_plural = 'AI测试用例'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class AIExecutionRecord(models.Model):
    """AI执行记录"""
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('running', '执行中'),
        ('passed', '成功'),
        ('failed', '失败'),
    ]

    project = models.ForeignKey(UiProject, on_delete=models.CASCADE, verbose_name='所属项目')
    ai_case = models.ForeignKey(AICase, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='关联AI用例')
    case_name = models.CharField(max_length=200, verbose_name='用例名称快照')
    task_description = models.TextField(blank=True, default='', verbose_name='任务描述', help_text='用户输入的原始任务描述')
    execution_mode = models.CharField(max_length=20, choices=[('text', '文本模式'), ('web', 'Web模式'), ('mobile', '移动端模式')], default='text', verbose_name='执行模式')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='执行状态')
    start_time = models.DateTimeField(auto_now_add=True, verbose_name='开始时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    duration = models.FloatField(null=True, blank=True, verbose_name='执行时长(秒)')
    logs = models.TextField(blank=True, default='', verbose_name='执行日志')
    steps_completed = models.JSONField(default=list, verbose_name='已完成步骤')
    planned_tasks = models.JSONField(default=list, verbose_name='规划任务') # 规划的任务列表 [{'id': 1, 'description': '...', 'status': 'pending'}]
    executed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='执行人')
    gif_path = models.CharField(max_length=500, null=True, blank=True, verbose_name='GIF录制路径')
    screenshots_sequence = models.JSONField(default=list, verbose_name='截图序列')

    class Meta:
        db_table = 'ui_ai_execution_records'
        verbose_name = 'AI执行记录'
        verbose_name_plural = 'AI执行记录'
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.case_name} - {self.get_status_display()}"


