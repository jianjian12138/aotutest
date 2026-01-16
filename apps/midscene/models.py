from django.db import models
from django.conf import settings
from django.utils import timezone


class MidsceneConfig(models.Model):
    """Midscene.js配置"""
    name = models.CharField(max_length=255, verbose_name='配置名称')
    description = models.TextField(blank=True, null=True, verbose_name='配置描述')
    api_key = models.CharField(max_length=255, verbose_name='API密钥')
    base_url = models.URLField(max_length=255, default='https://api.midscene.ai/v1', verbose_name='Midscene API地址')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')

    class Meta:
        verbose_name = 'Midscene.js配置'
        verbose_name_plural = 'Midscene.js配置'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class MidsceneTask(models.Model):
    """Midscene.js任务"""
    STATUS_CHOICES = [
        ('PENDING', '等待中'),
        ('RUNNING', '运行中'),
        ('SUCCESS', '成功'),
        ('FAILED', '失败'),
        ('STOPPED', '已停止'),
    ]

    config = models.ForeignKey(MidsceneConfig, on_delete=models.CASCADE, verbose_name='Midscene配置')
    name = models.CharField(max_length=255, verbose_name='任务名称')
    description = models.TextField(blank=True, null=True, verbose_name='任务描述')
    natural_language = models.TextField(verbose_name='自然语言指令')
    task_id = models.CharField(max_length=255, blank=True, null=True, verbose_name='Midscene任务ID')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name='任务状态')
    result = models.JSONField(default=dict, blank=True, verbose_name='任务结果')
    logs = models.TextField(blank=True, null=True, verbose_name='任务日志')
    start_time = models.DateTimeField(auto_now_add=True, verbose_name='开始时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='创建人')

    class Meta:
        verbose_name = 'Midscene.js任务'
        verbose_name_plural = 'Midscene.js任务'
        ordering = ['-start_time']

    def __str__(self):
        return self.name

    def get_status_display(self):
        """获取状态的中文显示"""
        status_dict = dict(self.STATUS_CHOICES)
        return status_dict.get(self.status, self.status)


class MidsceneExecutionLog(models.Model):
    """Midscene.js执行日志"""
    LOG_LEVEL_CHOICES = [
        ('DEBUG', '调试'),
        ('INFO', '信息'),
        ('WARN', '警告'),
        ('ERROR', '错误'),
        ('CRITICAL', '严重'),
    ]

    task = models.ForeignKey(MidsceneTask, on_delete=models.CASCADE, verbose_name='关联任务')
    log_level = models.CharField(max_length=20, choices=LOG_LEVEL_CHOICES, default='INFO', verbose_name='日志级别')
    message = models.TextField(verbose_name='日志消息')
    data = models.JSONField(default=dict, blank=True, verbose_name='日志数据')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = 'Midscene.js执行日志'
        verbose_name_plural = 'Midscene.js执行日志'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.log_level} - {self.message[:50]}'

    def get_log_level_display(self):
        """获取日志级别的中文显示"""
        log_level_dict = dict(self.LOG_LEVEL_CHOICES)
        return log_level_dict.get(self.log_level, self.log_level)
