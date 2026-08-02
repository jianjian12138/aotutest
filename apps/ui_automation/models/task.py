from apps.notifications.models import NotificationConfig
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()
from django.utils import timezone
import json
from .project import UiProject, TestEnvironment
from .execution import TestSuite

class UiScheduledTask(models.Model):
    """UI自动化定时任务模型"""
    TASK_TYPE_CHOICES = [
        ('TEST_SUITE', '测试套件执行'),
        ('TEST_CASE', '测试用例执行'),
    ]

    STATUS_CHOICES = [
        ('ACTIVE', '激活'),
        ('PAUSED', '暂停'),
        ('COMPLETED', '已完成'),
        ('FAILED', '失败'),
    ]

    TRIGGER_TYPE_CHOICES = [
        ('CRON', 'Cron表达式'),
        ('INTERVAL', '固定间隔'),
        ('ONCE', '单次执行'),
    ]

    name = models.CharField(max_length=200, verbose_name='任务名称')
    description = models.TextField(blank=True, verbose_name='任务描述')
    task_type = models.CharField(max_length=20, choices=TASK_TYPE_CHOICES, verbose_name='任务类型')
    trigger_type = models.CharField(max_length=20, choices=TRIGGER_TYPE_CHOICES, verbose_name='触发器类型')

    # Cron表达式配置
    cron_expression = models.CharField(max_length=100, blank=True, verbose_name='Cron表达式')

    # 固定间隔配置（秒）
    interval_seconds = models.IntegerField(null=True, blank=True, verbose_name='间隔秒数')

    # 单次执行时间
    execute_at = models.DateTimeField(null=True, blank=True, verbose_name='执行时间')

    # 任务配置
    project = models.ForeignKey('UiProject', on_delete=models.CASCADE, verbose_name='关联项目')
    test_suite = models.ForeignKey('TestSuite', on_delete=models.CASCADE, null=True, blank=True,
                                   verbose_name='测试套件')
    test_cases = models.JSONField(default=list, blank=True, verbose_name='测试用例列表',
                                 help_text='测试用例ID列表，用于TEST_CASE类型任务')

    # 执行配置
    engine = models.CharField(max_length=20, default='playwright', verbose_name='执行引擎',
                             help_text='playwright, selenium或airtest')
    browser = models.CharField(max_length=20, default='chrome', verbose_name='浏览器类型')
    headless = models.BooleanField(default=False, verbose_name='无头模式')

    # 通知配置
    NOTIFICATION_TYPE_CHOICES = [
        ('email', '邮箱通知'),
        ('webhook', 'Webhook机器人'),
        ('both', '两者都发送'),
    ]
    
    notify_on_success = models.BooleanField(default=False, verbose_name='成功时通知')
    notify_on_failure = models.BooleanField(default=False, verbose_name='失败时通知')
    notification_type = models.CharField(max_length=20, blank=True, choices=NOTIFICATION_TYPE_CHOICES, 
                                        verbose_name='通知类型')
    notify_emails = models.JSONField(default=list, blank=True, verbose_name='通知邮箱列表')

    # 状态管理
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE', verbose_name='任务状态')
    last_run_time = models.DateTimeField(null=True, blank=True, verbose_name='最后运行时间')
    next_run_time = models.DateTimeField(null=True, blank=True, verbose_name='下次运行时间')
    total_runs = models.IntegerField(default=0, verbose_name='总运行次数')
    successful_runs = models.IntegerField(default=0, verbose_name='成功运行次数')
    failed_runs = models.IntegerField(default=0, verbose_name='失败运行次数')

    # 执行结果
    last_result = models.JSONField(default=dict, verbose_name='最后执行结果')
    error_message = models.TextField(blank=True, verbose_name='错误信息')

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'ui_scheduled_tasks'
        verbose_name = 'UI定时任务'
        verbose_name_plural = 'UI定时任务'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_task_type_display()})"

    def calculate_next_run(self):
        """计算下次运行时间"""
        from datetime import datetime, timedelta
        from croniter import croniter

        now = timezone.now()

        if self.trigger_type == 'CRON' and self.cron_expression:
            try:
                iter = croniter(self.cron_expression, now)
                return iter.get_next(datetime)
            except Exception:
                return None

        elif self.trigger_type == 'INTERVAL' and self.interval_seconds:
            return now + timedelta(seconds=self.interval_seconds)

        elif self.trigger_type == 'ONCE' and self.execute_at:
            return self.execute_at if self.execute_at > now else None

        return None

    def should_run_now(self):
        """检查是否应该现在运行"""
        if self.status != 'ACTIVE':
            return False

        if not self.next_run_time:
            return False

        return timezone.now() >= self.next_run_time


class UiTaskNotificationSetting(models.Model):
    """UI定时任务通知设置模型"""
    NOTIFICATION_TYPES = [
        ('email', '邮箱通知'),
        ('webhook', 'Webhook机器人'),
        ('both', '两种都发送'),
    ]

    task = models.ForeignKey(UiScheduledTask, on_delete=models.CASCADE, related_name='notification_settings',
                             verbose_name='关联任务')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='webhook',
                                         verbose_name='通知类型')
    notification_config = models.ForeignKey(NotificationConfig, on_delete=models.SET_NULL, null=True, blank=True,
                                            related_name='ui_automation_notification_config', verbose_name='通知配置')
    is_enabled = models.BooleanField(default=False, verbose_name='是否启用通知')
    notify_on_success = models.BooleanField(default=True, verbose_name='成功时通知')
    notify_on_failure = models.BooleanField(default=True, verbose_name='失败时通知')
    notify_on_timeout = models.BooleanField(default=False, verbose_name='超时时通知')
    notify_on_error = models.BooleanField(default=True, verbose_name='错误时通知')
    custom_webhook_bots = models.JSONField(default=dict, blank=True, null=True, verbose_name='自定义Webhook机器人',
                                           help_text='临时覆盖通知配置中的Webhook机器人设置')
    custom_recipients = models.ManyToManyField(User, blank=True,
                                               related_name='ui_task_notification_settings_as_custom_recipient',
                                               verbose_name='自定义收件人', help_text='临时覆盖通知配置中的收件人设置')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'ui_task_notification_settings'
        verbose_name = 'UI任务通知设置'
        verbose_name_plural = 'UI任务通知设置'
        unique_together = ['task']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.task.name} - {self.get_notification_type_display()}"

    def get_active_notification_types(self):
        """获取当前激活的通知类型"""
        active_types = []
        if self.notification_type in ['email', 'both']:
            active_types.append('email')
        if self.notification_type in ['webhook', 'both']:
            active_types.append('webhook')
        return active_types

    def get_notification_config(self):
        """获取通知配置，优先使用任务自定义配置"""
        if self.notification_config:
            return self.notification_config
        # 如果没有指定配置，使用默认配置
        return NotificationConfig.objects.filter(is_default=True, is_active=True).first()


