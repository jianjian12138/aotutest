from django.db import models
from django.conf import settings
from django.utils import timezone
from backend.utils.crypto import EncryptedTextField


class VannaConfig(models.Model):
    """Vanna AI配置"""
    name = models.CharField(max_length=255, verbose_name='配置名称')
    description = models.TextField(blank=True, null=True, verbose_name='配置描述')
    provider = models.CharField(max_length=100, default='openai', verbose_name='AI提供商')
    model = models.CharField(max_length=100, default='gpt-4o', verbose_name='AI模型')
    api_key = EncryptedTextField(verbose_name='API密钥')
    db_type = models.CharField(max_length=50, default='mysql', verbose_name='数据库类型')
    db_connection = models.JSONField(default=dict, verbose_name='数据库连接配置')
    db_password = EncryptedTextField(blank=True, null=True, verbose_name='数据库连接密码')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')

    class Meta:
        verbose_name = 'Vanna AI配置'
        verbose_name_plural = 'Vanna AI配置'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_db_password(self):
        """数据库密码仅从加密字段 db_password 读取；缺失即返回 None，由调用方 fail-fast。"""
        return self.db_password or None


class SqlGeneration(models.Model):
    """SQL生成记录"""
    STATUS_CHOICES = [
        ('PENDING', '等待中'),
        ('SUCCESS', '成功'),
        ('FAILED', '失败'),
    ]

    config = models.ForeignKey(VannaConfig, on_delete=models.CASCADE, verbose_name='Vanna配置')
    natural_language = models.TextField(verbose_name='自然语言查询')
    generated_sql = models.TextField(blank=True, null=True, verbose_name='生成的SQL')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name='生成状态')
    execution_result = models.JSONField(default=dict, blank=True, verbose_name='执行结果')
    execution_status = models.CharField(max_length=20, choices=STATUS_CHOICES, blank=True, null=True, verbose_name='执行状态')
    error_message = models.TextField(blank=True, null=True, verbose_name='错误信息')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = 'SQL生成记录'
        verbose_name_plural = 'SQL生成记录'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.id} - {self.natural_language[:50]}'

    def get_status_display(self):
        """获取状态的中文显示"""
        status_dict = dict(self.STATUS_CHOICES)
        return status_dict.get(self.status, self.status)


class DataFactoryProject(models.Model):
    """数据工厂项目"""
    name = models.CharField(max_length=255, verbose_name='项目名称')
    description = models.TextField(blank=True, null=True, verbose_name='项目描述')
    config = models.ForeignKey(VannaConfig, on_delete=models.SET_NULL, null=True, verbose_name='关联Vanna配置')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='项目所有者')
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='data_factory_projects', blank=True, verbose_name='项目成员')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')

    class Meta:
        verbose_name = '数据工厂项目'
        verbose_name_plural = '数据工厂项目'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class SavedQuery(models.Model):
    """保存的查询"""
    project = models.ForeignKey(DataFactoryProject, on_delete=models.CASCADE, verbose_name='所属项目')
    name = models.CharField(max_length=255, verbose_name='查询名称')
    natural_language = models.TextField(verbose_name='自然语言查询')
    generated_sql = models.TextField(verbose_name='生成的SQL')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_favorite = models.BooleanField(default=False, verbose_name='是否收藏')

    class Meta:
        verbose_name = '保存的查询'
        verbose_name_plural = '保存的查询'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class QueryHistory(models.Model):
    """查询历史记录"""
    project = models.ForeignKey(DataFactoryProject, on_delete=models.CASCADE, verbose_name='所属项目')
    sql_generation = models.ForeignKey(SqlGeneration, on_delete=models.CASCADE, verbose_name='SQL生成记录')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    execution_time = models.FloatField(null=True, blank=True, verbose_name='执行时间(秒)')
    row_count = models.IntegerField(null=True, blank=True, verbose_name='返回行数')

    class Meta:
        verbose_name = '查询历史记录'
        verbose_name_plural = '查询历史记录'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.id} - {self.created_at.strftime("%Y-%m-%d %H:%M:%S")}'


class TableMetadata(models.Model):
    """表元数据"""
    config = models.ForeignKey(VannaConfig, on_delete=models.CASCADE, verbose_name='Vanna配置')
    table_name = models.CharField(max_length=255, verbose_name='表名')
    schema_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='模式名')
    description = models.TextField(blank=True, null=True, verbose_name='表描述')
    columns = models.JSONField(default=list, verbose_name='列信息')
    indexes = models.JSONField(default=list, blank=True, verbose_name='索引信息')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '表元数据'
        verbose_name_plural = '表元数据'
        ordering = ['schema_name', 'table_name']

    def __str__(self):
        if self.schema_name:
            return f'{self.schema_name}.{self.table_name}'
        return self.table_name


class DataSource(models.Model):
    """通用数据源管理 (例如: MySQL, PostgreSQL, Redis, MongoDB)"""
    project = models.ForeignKey(DataFactoryProject, on_delete=models.CASCADE, verbose_name='所属项目', null=True, blank=True)
    name = models.CharField(max_length=255, verbose_name='数据源名称')
    type = models.CharField(max_length=50, choices=[
        ('mysql', 'MySQL'),
        ('postgresql', 'PostgreSQL'),
        ('redis', 'Redis'),
        ('mongodb', 'MongoDB'),
        ('oracle', 'Oracle'),
        ('sqlserver', 'SQL Server')
    ], default='mysql', verbose_name='数据源类型')
    host = models.CharField(max_length=255, verbose_name='主机地址')
    port = models.IntegerField(verbose_name='端口')
    username = models.CharField(max_length=100, blank=True, null=True, verbose_name='用户名')
    password = EncryptedTextField(blank=True, null=True, verbose_name='密码')
    database = models.CharField(max_length=100, blank=True, null=True, verbose_name='数据库名/索引编号')
    extra_config = models.JSONField(default=dict, blank=True, verbose_name='其他配置')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='创建人')
    organization = models.ForeignKey(
        'core_platform.Organization',
        on_delete=models.CASCADE,
        null=True, blank=True, db_index=True,
        verbose_name='所属组织')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_active = models.BooleanField(default=True, verbose_name='是否活跃')

    class Meta:
        verbose_name = '通用数据源'
        verbose_name_plural = '通用数据源'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.type})'


class DataPool(models.Model):
    """测试数据池 (存储生成的、用来进行数据驱动测试的集合)"""
    project = models.ForeignKey(DataFactoryProject, on_delete=models.CASCADE, verbose_name='所属项目', null=True, blank=True)
    name = models.CharField(max_length=255, verbose_name='数据池名称')
    description = models.TextField(blank=True, null=True, verbose_name='描述')
    schema_definition = models.JSONField(default=list, blank=True, verbose_name='数据结构定义(Schema)')
    data = models.JSONField(default=list, blank=True, verbose_name='池数据(JSON Array)')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '数据池'
        verbose_name_plural = '数据池'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

