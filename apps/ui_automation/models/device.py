from apps.notifications.models import NotificationConfig
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()
from django.utils import timezone
import json
from apps.core_platform.models import Organization
from .project import UiProject

class ExecutionNode(models.Model):
    """执行节点模型 (Agent)"""
    STATUS_CHOICES = [
        ('online', '在线'),
        ('offline', '离线'),
        ('busy', '忙碌'),
    ]

    NODE_TYPE_CHOICES = [
        ('execution', '执行节点'),
        ('recorder', '录制节点'),
    ]

    name = models.CharField(max_length=200, verbose_name='节点名称')
    token = models.CharField(max_length=100, unique=True, verbose_name='认证令牌')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='offline', verbose_name='状态')
    node_type = models.CharField(max_length=20, choices=NODE_TYPE_CHOICES, default='execution', verbose_name='节点类型')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP地址')
    last_heartbeat = models.DateTimeField(null=True, blank=True, verbose_name='最后心跳时间')
    capabilities = models.JSONField(default=dict, blank=True, verbose_name='能力配置')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'ui_execution_nodes'
        verbose_name = '执行节点'
        verbose_name_plural = '执行节点'
        ordering = ['-last_heartbeat']

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class UiDevice(models.Model):
    """UI自动化测试设备模型"""
    PLATFORM_CHOICES = [
        ('android', 'Android'),
        ('ios', 'iOS'),
    ]
    
    TYPE_CHOICES = [
        ('real', '真机'),
        ('emulator', '模拟器'),
    ]
    
    STATUS_CHOICES = [
        ('online', '在线'),
        ('offline', '离线'),
        ('busy', '忙碌'),
        ('unauthorized', '未授权'),
    ]

    name = models.CharField(max_length=200, verbose_name='设备名称')
    device_id = models.CharField(max_length=100, unique=True, verbose_name='设备ID', help_text='UDID或序列号')
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, verbose_name='平台')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='real', verbose_name='设备类型')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='offline', verbose_name='设备状态')
    version = models.CharField(max_length=50, blank=True, verbose_name='系统版本')
    remote_url = models.CharField(max_length=200, blank=True, null=True, verbose_name='远程连接URL')
    last_online = models.DateTimeField(default=timezone.now, verbose_name='最后在线时间')
    # 第六轮批次2 #157：补租户字段，解除 BaseProjectViewSet 对 UiDevice 的 fail-closed 降级
    # （此前 UiDevice 无任何 organization/project/created_by 字段，BaseProjectViewSet.get_queryset
    #  对无 project_id 且无 created_by 的模型直接返回空集，导致非管理员永远看不到设备）。
    # 新增 organization 后，TenantAware 解析链路自动按 organization 过滤，设备归属到注册用户的组织。
    # null=True 兼容存量数据（存量设备刷新/注册时回填 organization），organization 为空时
    # 非管理员按 fail-closed 不可见（与整改前行为一致，不引入越权）。
    organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='所属组织')
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_ui_devices', verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'ui_devices'
        verbose_name = '测试设备'
        verbose_name_plural = '测试设备'
        ordering = ['-status', '-last_online']

    def __str__(self):
        return f"{self.name} ({self.device_id})"


