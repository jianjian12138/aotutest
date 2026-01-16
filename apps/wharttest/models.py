from django.db import models
from django.conf import settings
from django.utils import timezone


class WHartTestConfig(models.Model):
    """WHartTest配置"""
    name = models.CharField(max_length=255, verbose_name='配置名称')
    description = models.TextField(blank=True, null=True, verbose_name='配置描述')
    base_url = models.URLField(max_length=255, verbose_name='WHartTest服务地址')
    api_key = models.CharField(max_length=255, verbose_name='API密钥')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')

    class Meta:
        verbose_name = 'WHartTest配置'
        verbose_name_plural = 'WHartTest配置'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class WHartTestProject(models.Model):
    """WHartTest项目关联"""
    name = models.CharField(max_length=255, verbose_name='项目名称')
    description = models.TextField(blank=True, null=True, verbose_name='项目描述')
    wharttest_project_id = models.CharField(max_length=255, verbose_name='WHartTest项目ID')
    config = models.ForeignKey(WHartTestConfig, on_delete=models.CASCADE, verbose_name='WHartTest配置')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')

    class Meta:
        verbose_name = 'WHartTest项目关联'
        verbose_name_plural = 'WHartTest项目关联'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class WHartTestExecution(models.Model):
    """WHartTest执行记录"""
    STATUS_CHOICES = [
        ('PENDING', '等待中'),
        ('RUNNING', '运行中'),
        ('SUCCESS', '成功'),
        ('FAILED', '失败'),
        ('STOPPED', '已停止'),
    ]

    project = models.ForeignKey(WHartTestProject, on_delete=models.CASCADE, verbose_name='WHartTest项目')
    execution_id = models.CharField(max_length=255, blank=True, null=True, verbose_name='WHartTest执行ID')
    name = models.CharField(max_length=255, verbose_name='执行名称')
    description = models.TextField(blank=True, null=True, verbose_name='执行描述')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name='执行状态')
    parameters = models.JSONField(default=dict, blank=True, verbose_name='执行参数')
    result = models.JSONField(default=dict, blank=True, verbose_name='执行结果')
    logs = models.TextField(blank=True, null=True, verbose_name='执行日志')
    start_time = models.DateTimeField(auto_now_add=True, verbose_name='开始时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    executed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='执行人')

    class Meta:
        verbose_name = 'WHartTest执行记录'
        verbose_name_plural = 'WHartTest执行记录'
        ordering = ['-start_time']

    def __str__(self):
        return self.name

    def get_status_display(self):
        """获取状态的中文显示"""
        status_dict = dict(self.STATUS_CHOICES)
        return status_dict.get(self.status, self.status)


class WHartTestTask(models.Model):
    """WHartTest任务"""
    TASK_TYPE_CHOICES = [
        ('TESTCASE_GENERATION', '测试用例生成'),
        ('TEST_EXECUTION', '测试执行'),
        ('KNOWLEDGE_MANAGEMENT', '知识库管理'),
        ('OTHER', '其他'),
    ]

    project = models.ForeignKey(WHartTestProject, on_delete=models.CASCADE, verbose_name='WHartTest项目')
    name = models.CharField(max_length=255, verbose_name='任务名称')
    description = models.TextField(blank=True, null=True, verbose_name='任务描述')
    task_type = models.CharField(max_length=50, choices=TASK_TYPE_CHOICES, default='TESTCASE_GENERATION', verbose_name='任务类型')
    status = models.CharField(max_length=20, choices=WHartTestExecution.STATUS_CHOICES, default='PENDING', verbose_name='任务状态')
    task_data = models.JSONField(default=dict, verbose_name='任务数据')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = 'WHartTest任务'
        verbose_name_plural = 'WHartTest任务'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_task_type_display(self):
        """获取任务类型的中文显示"""
        task_type_dict = dict(self.TASK_TYPE_CHOICES)
        return task_type_dict.get(self.task_type, self.task_type)

    def get_status_display(self):
        """获取状态的中文显示"""
        status_dict = dict(WHartTestExecution.STATUS_CHOICES)
        return status_dict.get(self.status, self.status)


class WHartTestIntegrationLog(models.Model):
    """WHartTest集成日志"""
    LOG_LEVEL_CHOICES = [
        ('DEBUG', '调试'),
        ('INFO', '信息'),
        ('WARN', '警告'),
        ('ERROR', '错误'),
        ('CRITICAL', '严重'),
    ]

    config = models.ForeignKey(WHartTestConfig, on_delete=models.CASCADE, verbose_name='WHartTest配置')
    log_level = models.CharField(max_length=20, choices=LOG_LEVEL_CHOICES, default='INFO', verbose_name='日志级别')
    message = models.TextField(verbose_name='日志消息')
    request_data = models.JSONField(default=dict, blank=True, verbose_name='请求数据')
    response_data = models.JSONField(default=dict, blank=True, verbose_name='响应数据')
    error_details = models.TextField(blank=True, null=True, verbose_name='错误详情')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = 'WHartTest集成日志'
        verbose_name_plural = 'WHartTest集成日志'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.log_level} - {self.message[:50]}'

    def get_log_level_display(self):
        """获取日志级别的中文显示"""
        log_level_dict = dict(self.LOG_LEVEL_CHOICES)
        return log_level_dict.get(self.log_level, self.log_level)
