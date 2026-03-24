from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser

# ==========================================
# 1. User Domain
# ==========================================
class User(AbstractUser):
    # Extension of original User model
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name='Avatar')
    phone = models.CharField(max_length=11, null=True, blank=True, verbose_name='Phone')
    department = models.CharField(max_length=100, null=True, blank=True, verbose_name='Department')
    position = models.CharField(max_length=100, null=True, blank=True, verbose_name='Position')
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
