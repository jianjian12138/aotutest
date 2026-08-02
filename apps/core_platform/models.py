import logging
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser

# ==========================================
# 0. Organization Domain (V3.5 Multi-Tenancy)
# ==========================================
class Organization(models.Model):
    name = models.CharField(max_length=200, verbose_name='Organization Name')
    code = models.SlugField(max_length=50, unique=True, verbose_name='Organization Code')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_organizations'
        verbose_name = 'Organization'
        verbose_name_plural = 'Organizations'

# ==========================================
# 1. User Domain
# ==========================================
class User(AbstractUser):
    # Extension of original User model
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name='Avatar')
    phone = models.CharField(max_length=11, null=True, blank=True, verbose_name='Phone')
    department = models.CharField(max_length=100, null=True, blank=True, verbose_name='Department')
    position = models.CharField(max_length=100, null=True, blank=True, verbose_name='Position')
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name="core_user_set",
        related_query_name="core_user",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="core_user_set",
        related_query_name="core_user",
    )
    
    class Meta:
        db_table = 'core_users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    theme = models.CharField(max_length=20, default='light', verbose_name='Theme')
    language = models.CharField(max_length=10, default='zh-cn', verbose_name='Language')
    timezone = models.CharField(max_length=50, default='Asia/Shanghai', verbose_name='Timezone')
    notifications = models.JSONField(default=dict, verbose_name='Notifications')
    
    class Meta:
        db_table = 'core_user_profiles'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

# ==========================================
# 2. Project & Version Domain
# ==========================================
class Project(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    ]
    
    PROJECT_TYPE_CHOICES = [
        ('API', 'API Testing'),
        ('UI', 'UI Automation'),
        ('PERFORMANCE', 'Performance Testing'),
        ('GENERAL', 'General Project'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='Project Name')
    description = models.TextField(blank=True, verbose_name='Project Description')
    project_type = models.CharField(
        max_length=20, choices=PROJECT_TYPE_CHOICES, default='GENERAL', verbose_name='Project Type', db_index=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='Status')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_projects', verbose_name='Owner')
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True, related_name='projects')
    members = models.ManyToManyField(User, through='ProjectMember', related_name='joined_projects', verbose_name='Members')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    class Meta:
        db_table = 'core_projects'
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'
        ordering = ['-created_at']

class ProjectMember(models.Model):
    ROLE_CHOICES = [('owner', 'Owner'), ('admin', 'Admin'), ('developer', 'Developer'), ('tester', 'Tester'), ('viewer', 'Viewer')]
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='core_projectmember_set')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='tester', verbose_name='Role')
    joined_at = models.DateTimeField(default=timezone.now, verbose_name='Joined At')
    
    class Meta:
        db_table = 'core_project_members'
        unique_together = ['project', 'user']

class ProjectEnvironment(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='environments')
    name = models.CharField(max_length=100, verbose_name='Environment Name')
    base_url = models.URLField(verbose_name='Base URL')
    description = models.TextField(blank=True, verbose_name='Description')
    variables = models.JSONField(default=dict, verbose_name='Variables')
    is_default = models.BooleanField(default=False, verbose_name='Is Default')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Created At')
    
    class Meta:
        db_table = 'core_project_environments'
        verbose_name = 'Project Environment'
        verbose_name_plural = 'Project Environments'

class Version(models.Model):
    projects = models.ManyToManyField(Project, related_name='core_versions', verbose_name='Associated Projects')
    name = models.CharField(max_length=100, verbose_name='Version Name')
    description = models.TextField(blank=True, verbose_name='Version Description')
    is_baseline = models.BooleanField(default=False, verbose_name='Is Baseline')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Created By', related_name='core_version_created_by')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Created At')
    
    class Meta:
        db_table = 'core_versions'
        verbose_name = 'Version'
        verbose_name_plural = 'Versions'

# ==========================================
# 3. Configuration Domain
# ==========================================
class GlobalParameter(models.Model):
    key = models.CharField(max_length=255, unique=True, verbose_name='Parameter Key')
    value = models.TextField(verbose_name='Parameter Value')
    description = models.TextField(blank=True, verbose_name='Parameter Description')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True, related_name='core_global_parameters')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='core_global_params_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_global_parameters'

class CommonMethod(models.Model):
    name = models.CharField(max_length=200, verbose_name='Method Name')
    keyword = models.CharField(max_length=100, unique=True, verbose_name='Invocation Keyword')
    description = models.TextField(blank=True, verbose_name='Method Description')
    code_snippet = models.TextField(blank=True, verbose_name='Code Snippet')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True, related_name='core_common_methods')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='core_common_methods_created')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'core_common_methods'

# ==========================================
# 4. 企业基座抽象基类（阶段1：租户隔离 + 时间戳）
# ==========================================
class TimeStampedModel(models.Model):
    """统一时间戳基类（供新建业务模型复用）。"""
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')

    class Meta:
        abstract = True


class TenantScopedModel(models.Model):
    """
    租户（组织）隔离基类。
    所有业务数据继承后，查询层通过 TenantScopedViewSetMixin 自动按
    request.user.organization 注入过滤，跨租户 API 不可达（阶段1.2）。
    """
    organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='%(class)s_set', verbose_name='所属组织'
    )

    class Meta:
        abstract = True


class BaseModel(TimeStampedModel, TenantScopedModel):
    """组合基类：时间戳 + 租户隔离。新建核心模型优先继承它。"""
    class Meta:
        abstract = True


# ==========================================
# 5. RBAC 角色模型（阶段1.1）
# ==========================================
class Role(models.Model):
    """
    平台角色。权限复用 Django 自带 auth.Permission，
    通过 members（User.roles）绑定到用户，实现对象级 + 角色级 RBAC。
    """
    name = models.CharField(max_length=100, verbose_name='角色名称')
    code = models.SlugField(max_length=50, unique=True, verbose_name='角色编码')
    description = models.TextField(blank=True, verbose_name='角色描述')
    is_system = models.BooleanField(default=False, verbose_name='是否系统内置')
    permissions = models.ManyToManyField(
        'auth.Permission', blank=True, related_name='roles', verbose_name='权限'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'core_roles'
        verbose_name = '角色'
        verbose_name_plural = '角色'
        ordering = ['code']

    def __str__(self):
        return f"{self.name}({self.code})"

    def permission_codenames(self):
        return set(self.permissions.values_list('codename', flat=True))


# User <-> Role 多对多（在 Role 定义之后追加到 User 模型）
User.roles = models.ManyToManyField(
    Role, blank=True, related_name='users', verbose_name='角色'
)


# ==========================================
# 6. 操作审计日志（阶段1.3）
# ==========================================
class AuditLog(models.Model):
    """
    关键写操作留痕。由 AuditLogMiddleware 自动记录（也可手动调用
    AuditLog.log()）。与 trace_id 关联，便于安全事件回溯。
    """
    ACTION_CREATE = 'CREATE'
    ACTION_UPDATE = 'UPDATE'
    ACTION_DELETE = 'DELETE'
    ACTION_LOGIN = 'LOGIN'
    ACTION_OTHER = 'OTHER'
    ACTION_CHOICES = [
        (ACTION_CREATE, '创建'),
        (ACTION_UPDATE, '更新'),
        (ACTION_DELETE, '删除'),
        (ACTION_LOGIN, '登录'),
        (ACTION_OTHER, '其他'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, default=ACTION_OTHER)
    resource_type = models.CharField(max_length=100, blank=True, verbose_name='资源类型')
    resource_id = models.CharField(max_length=100, blank=True, verbose_name='资源ID')
    method = models.CharField(max_length=10, blank=True, verbose_name='HTTP方法')
    path = models.CharField(max_length=500, blank=True, verbose_name='请求路径')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP地址')
    user_agent = models.TextField(blank=True, verbose_name='User-Agent')
    query_string = models.TextField(blank=True, verbose_name='查询串')
    body_snippet = models.TextField(blank=True, verbose_name='请求体摘要')
    response_status = models.IntegerField(null=True, blank=True, verbose_name='响应状态码')
    trace_id = models.CharField(max_length=64, blank=True, verbose_name='Trace ID')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='时间')

    class Meta:
        db_table = 'core_audit_logs'
        verbose_name = '审计日志'
        verbose_name_plural = '审计日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['organization', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['action', '-created_at']),
        ]

    def __str__(self):
        return f"[{self.action}] {self.path} @ {self.created_at:%Y-%m-%d %H:%M}"

    @classmethod
    def log(cls, *, user=None, organization=None, action=ACTION_OTHER,
            resource_type='', resource_id='', method='', path='',
            ip_address=None, user_agent='', query_string='', body_snippet='',
            response_status=None, trace_id='', request=None):
        """
        便捷记录方法。若传入 request，则自动补全 user/ip/ua/path 等。
        任何异常都被吞掉，确保审计写入失败不影响主流程。
        """
        try:
            if request is not None:
                u = getattr(request, 'user', None)
                if user is None and u is not None and u.is_authenticated:
                    user = u
                if organization is None and user is not None:
                    organization = getattr(user, 'organization', None)
                if not method:
                    method = request.method
                if not path:
                    path = request.path_info
                if ip_address is None:
                    ip_address = (request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
                                  or request.META.get('REMOTE_ADDR'))
                if not user_agent:
                    user_agent = request.META.get('HTTP_USER_AGENT', '')[:2000]
                if not query_string:
                    query_string = request.META.get('QUERY_STRING', '')[:2000]
                if not trace_id:
                    trace_id = getattr(request, 'trace_id', '')
            cls.objects.create(
                user=user, organization=organization, action=action,
                resource_type=resource_type, resource_id=str(resource_id),
                method=method, path=path, ip_address=ip_address,
                user_agent=user_agent, query_string=query_string,
                body_snippet=body_snippet, response_status=response_status,
                trace_id=trace_id,
            )
        except Exception:
            logging.exception("AuditLog 写入失败（已忽略）")
