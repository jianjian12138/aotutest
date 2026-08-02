from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.core_platform.models import Project
from apps.notifications.models import NotificationConfig

class ScheduledTask(models.Model):
    """统一调度任务模型"""
    TASK_TYPE_CHOICES = [
        ('API', '接口测试'),
        ('UI', 'UI自动化'),
        ('PERFORMANCE', '性能测试'),
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
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True, verbose_name='所属项目')
    api_project = models.ForeignKey('api_testing.ApiProject', on_delete=models.CASCADE, null=True, blank=True, verbose_name='所属API项目')
    
    task_type = models.CharField(max_length=20, choices=TASK_TYPE_CHOICES, verbose_name='任务类型')
    
    # 关联的具体测试资源
    api_test_suite = models.ForeignKey('api_testing.TestSuite', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='API测试套件', related_name='scheduler_tasks')
    ui_test_suite = models.ForeignKey('ui_automation.TestSuite', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='UI测试套件', related_name='scheduler_tasks')
    ui_test_case = models.ForeignKey('ui_automation.TestCase', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='UI测试用例', related_name='scheduler_tasks')
    performance_test_suite = models.ForeignKey('performance_test.PerformanceTestSuite', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='性能测试套件', related_name='scheduler_tasks')
    
    # 调度配置
    trigger_type = models.CharField(max_length=20, choices=TRIGGER_TYPE_CHOICES, default='CRON', verbose_name='触发器类型')
    cron_expression = models.CharField(max_length=100, blank=True, verbose_name='Cron表达式')
    interval_seconds = models.IntegerField(null=True, blank=True, verbose_name='间隔秒数')
    execute_at = models.DateTimeField(null=True, blank=True, verbose_name='执行时间')
    
    # 状态
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE', verbose_name='任务状态')
    last_run_time = models.DateTimeField(null=True, blank=True, verbose_name='最后运行时间')
    next_run_time = models.DateTimeField(null=True, blank=True, verbose_name='下次运行时间')
    
    # 统计
    total_runs = models.IntegerField(default=0, verbose_name='总运行次数')
    successful_runs = models.IntegerField(default=0, verbose_name='成功运行次数')
    failed_runs = models.IntegerField(default=0, verbose_name='失败运行次数')
    
    # 通知
    notification_config = models.ForeignKey(NotificationConfig, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='通知配置', related_name='scheduler_tasks')
    notify_on_success = models.BooleanField(default=False, verbose_name='成功时通知')
    notify_on_failure = models.BooleanField(default=True, verbose_name='失败时通知')
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='创建者', related_name='scheduler_tasks')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'scheduler_tasks'
        verbose_name = '定时任务'
        verbose_name_plural = '定时任务'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_task_type_display()})"


class TaskExecutionLog(models.Model):
    """任务执行日志"""
    STATUS_CHOICES = [
        ('PENDING', '待执行'),
        ('RUNNING', '执行中'),
        ('SUCCESS', '成功'),
        ('FAILED', '失败'),
    ]

    task = models.ForeignKey(ScheduledTask, on_delete=models.CASCADE, related_name='execution_logs', verbose_name='关联任务')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name='执行状态')
    start_time = models.DateTimeField(auto_now_add=True, verbose_name='开始时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    duration = models.FloatField(null=True, blank=True, verbose_name='执行时长(秒)')
    
    result = models.JSONField(default=dict, blank=True, verbose_name='执行结果')
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    
    class Meta:
        db_table = 'scheduler_execution_logs'
        verbose_name = '执行日志'
        verbose_name_plural = '执行日志'
        ordering = ['-start_time']
