from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class User(AbstractUser):
    """扩展用户模型"""
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name='头像')
    phone = models.CharField(max_length=11, null=True, blank=True, verbose_name='手机号')
    department = models.CharField(max_length=100, null=True, blank=True, verbose_name='部门')
    position = models.CharField(max_length=100, null=True, blank=True, verbose_name='职位')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'users_user'
        verbose_name = '用户'
        verbose_name_plural = '用户'

class UserProfile(models.Model):
    """用户配置"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    theme = models.CharField(max_length=20, default='light', verbose_name='主题')
    language = models.CharField(max_length=10, default='zh-cn', verbose_name='语言')
    timezone = models.CharField(max_length=50, default='Asia/Shanghai', verbose_name='时区')
    notifications = models.JSONField(default=dict, verbose_name='通知设置')
    
    class Meta:
        db_table = 'user_profiles'
        verbose_name = '用户配置'
        verbose_name_plural = '用户配置'