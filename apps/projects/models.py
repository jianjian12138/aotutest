from django.db import models
from django.utils import timezone
from apps.users.models import User

class Project(models.Model):
    """项目模型"""
    STATUS_CHOICES = [
        ('active', '进行中'),
        ('paused', '暂停'),
        ('completed', '已完成'),
        ('archived', '已归档'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='项目名称')
    description = models.TextField(blank=True, verbose_name='项目描述')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='状态')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_projects', verbose_name='负责人')
    members = models.ManyToManyField(User, through='ProjectMember', related_name='joined_projects', verbose_name='成员')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'projects'
        verbose_name = '项目'
        verbose_name_plural = '项目'
        ordering = ['-created_at']

class ProjectMember(models.Model):
    """项目成员"""
    ROLE_CHOICES = [
        ('owner', '负责人'),
        ('admin', '管理员'),
        ('developer', '开发者'),
        ('tester', '测试者'),
        ('viewer', '观察者'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='tester', verbose_name='角色')
    joined_at = models.DateTimeField(default=timezone.now, verbose_name='加入时间')
    
    class Meta:
        db_table = 'project_members'
        unique_together = ['project', 'user']
        verbose_name = '项目成员'
        verbose_name_plural = '项目成员'

class ProjectEnvironment(models.Model):
    """项目环境"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='environments')
    name = models.CharField(max_length=100, verbose_name='环境名称')
    base_url = models.URLField(verbose_name='基础URL')
    description = models.TextField(blank=True, verbose_name='环境描述')
    variables = models.JSONField(default=dict, verbose_name='环境变量')
    is_default = models.BooleanField(default=False, verbose_name='是否默认')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    
    class Meta:
        db_table = 'project_environments'
        verbose_name = '项目环境'
        verbose_name_plural = '项目环境'