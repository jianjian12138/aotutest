from apps.notifications.models import NotificationConfig
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()
from django.utils import timezone
import json
class UiProject(models.Model):
    """UI自动化测试项目模型"""
    STATUS_CHOICES = [
        ('NOT_STARTED', '未开始'),
        ('IN_PROGRESS', '进行中'),
        ('COMPLETED', '已结束'),
    ]

    name = models.CharField(max_length=200, verbose_name='项目名称')
    description = models.TextField(blank=True, verbose_name='项目描述')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name='项目状态', default='IN_PROGRESS')
    base_url = models.URLField(verbose_name='基础URL')
    start_date = models.DateField(null=True, blank=True, verbose_name='开始日期')
    end_date = models.DateField(null=True, blank=True, verbose_name='结束日期')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_ui_projects', verbose_name='负责人')
    members = models.ManyToManyField(User, blank=True, related_name='ui_projects', verbose_name='团队成员')
    
    # 调试配置
    debug_config = models.JSONField(default=dict, blank=True, verbose_name='调试配置', help_text='Playwright调试数据采集配置')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'ui_projects'
        verbose_name = 'UI自动化项目'
        verbose_name_plural = 'UI自动化项目'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class TestEnvironment(models.Model):
    """测试环境配置模型"""
    name = models.CharField(max_length=100, verbose_name='环境名称')
    description = models.TextField(blank=True, verbose_name='环境描述')
    browser_type = models.CharField(max_length=50, verbose_name='浏览器类型')
    browser_version = models.CharField(max_length=50, blank=True, verbose_name='浏览器版本')
    resolution = models.CharField(max_length=50, blank=True, verbose_name='屏幕分辨率')
    os_type = models.CharField(max_length=50, blank=True, verbose_name='操作系统')
    os_version = models.CharField(max_length=50, blank=True, verbose_name='操作系统版本')
    device_type = models.CharField(max_length=20, choices=[('PC', '电脑端'), ('MOBILE', '移动端(H5)'), ('MINI_PROGRAM', '小程序')], default='PC', verbose_name='设备类型')
    device_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='设备名称', help_text='Playwright支持的移动设备名称，如 "iPhone 13", "Pixel 5"等')
    capabilities = models.JSONField(blank=True, null=True, verbose_name='浏览器能力配置')
    browser_configs = models.JSONField(default=list, blank=True, verbose_name='多浏览器配置', help_text='支持多浏览器并行执行，例如 ["chromium", "firefox"]')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'ui_test_environments'
        verbose_name = 'UI测试环境'
        verbose_name_plural = 'UI测试环境'
        ordering = ['name']

    def __str__(self):
        return self.name


