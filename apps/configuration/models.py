from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class GlobalParameter(models.Model):
    """全局参数模型"""
    key = models.CharField(max_length=255, unique=True, verbose_name='参数键')
    value = models.TextField(verbose_name='参数值')
    description = models.TextField(blank=True, verbose_name='参数描述')
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, null=True, blank=True, related_name='global_parameters', verbose_name='关联项目')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'config_global_parameters'
        verbose_name = '全局参数'
        verbose_name_plural = '全局参数'
        ordering = ['-created_at']

    def __str__(self):
        return self.key

class CommonMethod(models.Model):
    """公共方法模型"""
    name = models.CharField(max_length=200, verbose_name='方法名称')
    keyword = models.CharField(max_length=100, unique=True, verbose_name='调用关键字', help_text='例如 $smart_click')
    description = models.TextField(blank=True, verbose_name='方法描述')
    code_snippet = models.TextField(blank=True, verbose_name='代码片段')
    params_schema = models.JSONField(default=list, blank=True, verbose_name='参数定义', help_text='参数列表定义')
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, null=True, blank=True, related_name='common_methods', verbose_name='关联项目')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'config_common_methods'
        verbose_name = '公共方法'
        verbose_name_plural = '公共方法'
        ordering = ['-created_at']

    def __str__(self):
        return self.name
