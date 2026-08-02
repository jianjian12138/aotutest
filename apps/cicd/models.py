from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from backend.utils.crypto import EncryptedTextField

User = get_user_model()


class CICDServer(models.Model):
    """CI/CD服务器配置模型"""
    SERVER_TYPE_CHOICES = [
        ('JENKINS', 'Jenkins'),
        ('GITLAB', 'GitLab'),
    ]

    name = models.CharField(max_length=200, verbose_name='服务器名称')
    server_type = models.CharField(max_length=20, choices=SERVER_TYPE_CHOICES, verbose_name='服务器类型')
    url = models.URLField(verbose_name='服务器URL')
    username = models.CharField(max_length=100, blank=True, verbose_name='用户名')
    password = EncryptedTextField(blank=True, verbose_name='密码')
    token = EncryptedTextField(blank=True, verbose_name='API Token')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'cicd_servers'
        verbose_name = 'CI/CD服务器'
        verbose_name_plural = 'CI/CD服务器'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_server_type_display()})"


class CICDJob(models.Model):
    """CI/CD任务模型"""
    STATUS_CHOICES = [
        ('ACTIVE', '激活'),
        ('INACTIVE', '停用'),
    ]

    name = models.CharField(max_length=200, verbose_name='任务名称')
    description = models.TextField(blank=True, verbose_name='任务描述')
    server = models.ForeignKey(CICDServer, on_delete=models.CASCADE, related_name='jobs', verbose_name='关联服务器')
    job_name = models.CharField(max_length=200, verbose_name='服务器任务名称')
    job_url = models.URLField(blank=True, verbose_name='任务URL')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE', verbose_name='状态')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'cicd_jobs'
        verbose_name = 'CI/CD任务'
        verbose_name_plural = 'CI/CD任务'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class CICDExecution(models.Model):
    """CI/CD执行记录模型"""
    STATUS_CHOICES = [
        ('PENDING', '待执行'),
        ('RUNNING', '执行中'),
        ('SUCCESS', '成功'),
        ('FAILURE', '失败'),
        ('CANCELLED', '已取消'),
    ]

    job = models.ForeignKey(CICDJob, on_delete=models.CASCADE, related_name='executions', verbose_name='关联任务')
    execution_id = models.CharField(max_length=200, blank=True, verbose_name='执行ID')
    build_number = models.IntegerField(null=True, blank=True, verbose_name='构建编号')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name='执行状态')
    parameters = models.JSONField(default=dict, blank=True, verbose_name='执行参数')
    start_time = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    duration = models.FloatField(null=True, blank=True, verbose_name='执行时长(秒)')
    triggered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='触发者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'cicd_executions'
        verbose_name = 'CI/CD执行记录'
        verbose_name_plural = 'CI/CD执行记录'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.job.name} - {self.build_number or self.execution_id} ({self.get_status_display()})"


class CICDLog(models.Model):
    """CI/CD执行日志模型"""
    execution = models.ForeignKey(CICDExecution, on_delete=models.CASCADE, related_name='logs', verbose_name='关联执行记录')
    log_content = models.TextField(verbose_name='日志内容')
    log_url = models.URLField(blank=True, verbose_name='日志URL')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'cicd_logs'
        verbose_name = 'CI/CD执行日志'
        verbose_name_plural = 'CI/CD执行日志'
        ordering = ['-created_at']

    def __str__(self):
        return f"日志 - {self.execution}"


class GitLabRepository(models.Model):
    """GitLab仓库模型"""
    name = models.CharField(max_length=200, verbose_name='仓库名称')
    repository_url = models.URLField(verbose_name='仓库URL')
    project_id = models.CharField(max_length=100, verbose_name='项目ID')
    server = models.ForeignKey(CICDServer, on_delete=models.CASCADE, related_name='gitlab_repos', verbose_name='关联服务器')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'cicd_gitlab_repos'
        verbose_name = 'GitLab仓库'
        verbose_name_plural = 'GitLab仓库'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class CICDTrigger(models.Model):
    """CI/CD触发配置模型"""
    TRIGGER_TYPE_CHOICES = [
        ('MANUAL', '手动触发'),
        ('SCHEDULED', '定时触发'),
        ('WEBHOOK', 'Webhook触发'),
    ]

    job = models.ForeignKey(CICDJob, on_delete=models.CASCADE, related_name='triggers', verbose_name='关联任务')
    trigger_type = models.CharField(max_length=20, choices=TRIGGER_TYPE_CHOICES, default='MANUAL', verbose_name='触发类型')
    cron_expression = models.CharField(max_length=100, blank=True, verbose_name='Cron表达式')
    webhook_url = models.URLField(blank=True, verbose_name='Webhook URL')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'cicd_triggers'
        verbose_name = 'CI/CD触发配置'
        verbose_name_plural = 'CI/CD触发配置'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.job.name} - {self.get_trigger_type_display()}"
