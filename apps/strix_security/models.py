from django.db import models
from django.conf import settings
from django.utils import timezone
from backend.utils.crypto import EncryptedTextField


class StrixConfig(models.Model):
    """Strix安全测试配置"""
    name = models.CharField(max_length=255, verbose_name='配置名称')
    description = models.TextField(blank=True, null=True, verbose_name='配置描述')
    base_url = models.URLField(max_length=255, default='http://localhost:8000', verbose_name='Strix服务地址')
    api_key = EncryptedTextField(verbose_name='API密钥')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')

    class Meta:
        verbose_name = 'Strix安全测试配置'
        verbose_name_plural = 'Strix安全测试配置'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class SecurityTestProject(models.Model):
    """安全测试项目"""
    name = models.CharField(max_length=255, verbose_name='项目名称')
    description = models.TextField(blank=True, null=True, verbose_name='项目描述')
    target_url = models.URLField(max_length=255, verbose_name='测试目标URL')
    config = models.ForeignKey(StrixConfig, on_delete=models.CASCADE, verbose_name='Strix配置')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')

    class Meta:
        verbose_name = '安全测试项目'
        verbose_name_plural = '安全测试项目'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class SecurityTestExecution(models.Model):
    """安全测试执行记录"""
    STATUS_CHOICES = [
        ('PENDING', '等待中'),
        ('RUNNING', '运行中'),
        ('SUCCESS', '成功'),
        ('FAILED', '失败'),
        ('STOPPED', '已停止'),
    ]

    project = models.ForeignKey(SecurityTestProject, on_delete=models.CASCADE, verbose_name='安全测试项目')
    name = models.CharField(max_length=255, verbose_name='执行名称')
    description = models.TextField(blank=True, null=True, verbose_name='执行描述')
    execution_id = models.CharField(max_length=255, blank=True, null=True, verbose_name='Strix执行ID')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name='执行状态')
    scan_type = models.CharField(max_length=100, default='full', verbose_name='扫描类型')
    parameters = models.JSONField(default=dict, blank=True, verbose_name='扫描参数')
    result = models.JSONField(default=dict, blank=True, verbose_name='扫描结果')
    vulnerabilities = models.JSONField(default=list, blank=True, verbose_name='漏洞列表')
    logs = models.TextField(blank=True, null=True, verbose_name='执行日志')
    start_time = models.DateTimeField(auto_now_add=True, verbose_name='开始时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    executed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='执行人')

    class Meta:
        verbose_name = '安全测试执行记录'
        verbose_name_plural = '安全测试执行记录'
        ordering = ['-start_time']

    def __str__(self):
        return self.name

    def get_status_display(self):
        """获取状态的中文显示"""
        status_dict = dict(self.STATUS_CHOICES)
        return status_dict.get(self.status, self.status)


class Vulnerability(models.Model):
    """漏洞记录"""
    SEVERITY_CHOICES = [
        ('CRITICAL', '严重'),
        ('HIGH', '高危'),
        ('MEDIUM', '中危'),
        ('LOW', '低危'),
        ('INFO', '信息'),
    ]

    execution = models.ForeignKey(SecurityTestExecution, on_delete=models.CASCADE, verbose_name='关联执行记录')
    vuln_id = models.CharField(max_length=100, verbose_name='漏洞ID')
    name = models.CharField(max_length=255, verbose_name='漏洞名称')
    description = models.TextField(verbose_name='漏洞描述')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='MEDIUM', verbose_name='严重程度')
    cvss_score = models.FloatField(default=0.0, verbose_name='CVSS评分')
    url = models.URLField(max_length=500, verbose_name='漏洞URL')
    method = models.CharField(max_length=10, default='GET', verbose_name='请求方法')
    payload = models.TextField(blank=True, null=True, verbose_name='漏洞载荷')
    fix_suggestion = models.TextField(blank=True, null=True, verbose_name='修复建议')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '漏洞记录'
        verbose_name_plural = '漏洞记录'
        ordering = ['-severity', '-cvss_score', '-created_at']

    def __str__(self):
        return self.name

    def get_severity_display(self):
        """获取严重程度的中文显示"""
        severity_dict = dict(self.SEVERITY_CHOICES)
        return severity_dict.get(self.severity, self.severity)


class SecurityTestHistory(models.Model):
    """安全测试历史记录"""
    project = models.ForeignKey(SecurityTestProject, on_delete=models.CASCADE, verbose_name='安全测试项目')
    execution = models.ForeignKey(SecurityTestExecution, on_delete=models.CASCADE, verbose_name='执行记录')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='创建人')

    class Meta:
        verbose_name = '安全测试历史记录'
        verbose_name_plural = '安全测试历史记录'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.project.name} - {self.created_at.strftime("%Y-%m-%d %H:%M:%S")}'
