from django.db import models
from django.conf import settings
from django.utils import timezone


class PerformanceProject(models.Model):
    """性能测试项目"""
    name = models.CharField(max_length=255, verbose_name='项目名称')
    description = models.TextField(blank=True, null=True, verbose_name='项目描述')
    project_type = models.CharField(max_length=50, default='HTTP', verbose_name='项目类型')
    status = models.CharField(max_length=50, default='IN_PROGRESS', verbose_name='项目状态')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='项目所有者')
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='performance_projects', blank=True, verbose_name='项目成员')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    start_date = models.DateField(null=True, blank=True, verbose_name='开始日期')
    end_date = models.DateField(null=True, blank=True, verbose_name='结束日期')

    class Meta:
        verbose_name = '性能测试项目'
        verbose_name_plural = '性能测试项目'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class PerformanceCollection(models.Model):
    """性能测试集合"""
    project = models.ForeignKey(PerformanceProject, on_delete=models.CASCADE, verbose_name='所属项目')
    name = models.CharField(max_length=255, verbose_name='集合名称')
    description = models.TextField(blank=True, null=True, verbose_name='集合描述')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children', verbose_name='父集合')
    order = models.IntegerField(default=0, verbose_name='排序')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '性能测试集合'
        verbose_name_plural = '性能测试集合'
        ordering = ['project', 'order', 'created_at']

    def __str__(self):
        return self.name


class PerformanceRequest(models.Model):
    """性能测试请求"""
    collection = models.ForeignKey(PerformanceCollection, on_delete=models.CASCADE, verbose_name='所属集合')
    name = models.CharField(max_length=255, verbose_name='请求名称')
    description = models.TextField(blank=True, null=True, verbose_name='请求描述')
    method = models.CharField(max_length=10, default='GET', verbose_name='请求方法')
    url = models.CharField(max_length=1000, verbose_name='请求URL')
    headers = models.JSONField(default=dict, blank=True, verbose_name='请求头')
    params = models.JSONField(default=dict, blank=True, verbose_name='查询参数')
    body = models.JSONField(default=dict, blank=True, verbose_name='请求体')
    request_type = models.CharField(max_length=50, default='HTTP', verbose_name='请求类型')
    assertions = models.JSONField(default=list, blank=True, verbose_name='断言')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    order = models.IntegerField(default=0, verbose_name='排序')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')

    class Meta:
        verbose_name = '性能测试请求'
        verbose_name_plural = '性能测试请求'
        ordering = ['collection', 'order', 'created_at']

    def __str__(self):
        return self.name


class PerformanceEnvironment(models.Model):
    """性能测试环境"""
    name = models.CharField(max_length=255, verbose_name='环境名称')
    description = models.TextField(blank=True, null=True, verbose_name='环境描述')
    scope = models.CharField(max_length=20, default='GLOBAL', verbose_name='环境范围')
    variables = models.JSONField(default=dict, blank=True, verbose_name='环境变量')
    project = models.ForeignKey(PerformanceProject, on_delete=models.CASCADE, null=True, blank=True, verbose_name='所属项目')
    is_active = models.BooleanField(default=False, verbose_name='是否激活')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '性能测试环境'
        verbose_name_plural = '性能测试环境'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class PerformanceTestSuite(models.Model):
    """性能测试套件"""
    name = models.CharField(max_length=255, verbose_name='测试套件名称')
    description = models.TextField(blank=True, null=True, verbose_name='测试套件描述')
    project = models.ForeignKey(PerformanceProject, on_delete=models.CASCADE, verbose_name='所属项目')
    environment = models.ForeignKey(PerformanceEnvironment, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='关联环境')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    locust_settings = models.JSONField(default=dict, blank=True, verbose_name='Locust配置')
    worker_count = models.IntegerField(default=0, verbose_name='Worker数量(0为单机模式)')

    class Meta:
        verbose_name = '性能测试套件'
        verbose_name_plural = '性能测试套件'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class PerformanceTestSuiteRequest(models.Model):
    """性能测试套件请求关联"""
    test_suite = models.ForeignKey(PerformanceTestSuite, on_delete=models.CASCADE, verbose_name='所属测试套件')
    request = models.ForeignKey(PerformanceRequest, on_delete=models.CASCADE, verbose_name='关联请求')
    enabled = models.BooleanField(default=True, verbose_name='是否启用')
    order = models.IntegerField(default=0, verbose_name='排序')
    weight = models.IntegerField(default=1, verbose_name='权重')
    assertions = models.JSONField(default=list, blank=True, verbose_name='断言')

    class Meta:
        verbose_name = '性能测试套件请求关联'
        verbose_name_plural = '性能测试套件请求关联'
        ordering = ['test_suite', 'order']

    def __str__(self):
        return f'{self.test_suite.name} - {self.request.name}'


class PerformanceTestExecution(models.Model):
    """性能测试执行记录"""
    STATUS_CHOICES = [
        ('RUNNING', '运行中'),
        ('COMPLETED', '已完成'),
        ('FAILED', '失败'),
        ('STOPPED', '已停止'),
    ]

    test_suite = models.ForeignKey(PerformanceTestSuite, on_delete=models.CASCADE, null=True, blank=True, verbose_name='测试套件')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='RUNNING', verbose_name='执行状态')
    start_time = models.DateTimeField(auto_now_add=True, verbose_name='开始时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    executed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='执行人员')
    total_requests = models.IntegerField(default=0, verbose_name='总请求数')
    passed_requests = models.IntegerField(default=0, verbose_name='通过请求数')
    failed_requests = models.IntegerField(default=0, verbose_name='失败请求数')
    response_time_avg = models.FloatField(null=True, blank=True, verbose_name='平均响应时间(ms)')
    response_time_min = models.FloatField(null=True, blank=True, verbose_name='最小响应时间(ms)')
    response_time_max = models.FloatField(null=True, blank=True, verbose_name='最大响应时间(ms)')
    rps = models.FloatField(null=True, blank=True, verbose_name='每秒请求数')
    concurrency = models.IntegerField(default=1, verbose_name='并发数')
    duration = models.IntegerField(default=60, verbose_name='持续时间(秒)')
    results = models.JSONField(default=dict, blank=True, verbose_name='执行结果')
    locust_logs = models.TextField(blank=True, null=True, verbose_name='Locust日志')
    report_html = models.TextField(blank=True, null=True, verbose_name='HTML报告')

    class Meta:
        verbose_name = '性能测试执行记录'
        verbose_name_plural = '性能测试执行记录'
        ordering = ['-start_time']

    def __str__(self):
        return f'{self.test_suite.name} - {self.start_time.strftime("%Y-%m-%d %H:%M:%S")}'

    def get_status_display(self):
        """获取状态的中文显示"""
        status_dict = dict(self.STATUS_CHOICES)
        return status_dict.get(self.status, self.status)


class PerformanceTestHistory(models.Model):
    """性能测试历史记录"""
    execution = models.ForeignKey(PerformanceTestExecution, on_delete=models.CASCADE, verbose_name='执行记录')
    request = models.ForeignKey(PerformanceRequest, on_delete=models.CASCADE, verbose_name='请求')
    environment = models.ForeignKey(PerformanceEnvironment, on_delete=models.SET_NULL, null=True, verbose_name='环境')
    request_data = models.JSONField(default=dict, blank=True, verbose_name='请求数据')
    response_data = models.JSONField(default=dict, blank=True, verbose_name='响应数据')
    status_code = models.IntegerField(null=True, blank=True, verbose_name='状态码')
    response_time = models.FloatField(null=True, blank=True, verbose_name='响应时间(ms)')
    assertions_results = models.JSONField(default=list, blank=True, verbose_name='断言结果')
    executed_at = models.DateTimeField(auto_now_add=True, verbose_name='执行时间')

    class Meta:
        verbose_name = '性能测试历史记录'
        verbose_name_plural = '性能测试历史记录'
        ordering = ['-executed_at']

    def __str__(self):
        return f'{self.request.name} - {self.executed_at.strftime("%Y-%m-%d %H:%M:%S")}'


class PerformanceScheduledTask(models.Model):
    """性能测试定时任务"""
    STATUS_CHOICES = [
        ('ACTIVE', '活跃'),
        ('INACTIVE', '不活跃'),
        ('PAUSED', '暂停'),
    ]

    name = models.CharField(max_length=255, verbose_name='任务名称')
    test_suite = models.ForeignKey(PerformanceTestSuite, on_delete=models.CASCADE, verbose_name='测试套件')
    cron_expression = models.CharField(max_length=100, verbose_name='Cron表达式')
    concurrency = models.IntegerField(default=1, verbose_name='并发数')
    duration = models.IntegerField(default=60, verbose_name='持续时间(秒)')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE', verbose_name='任务状态')
    last_executed = models.DateTimeField(null=True, blank=True, verbose_name='最后执行时间')
    next_executed = models.DateTimeField(null=True, blank=True, verbose_name='下次执行时间')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '性能测试定时任务'
        verbose_name_plural = '性能测试定时任务'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class PerformanceTaskExecutionLog(models.Model):
    """性能测试定时任务执行日志"""
    task = models.ForeignKey(PerformanceScheduledTask, on_delete=models.CASCADE, verbose_name='定时任务')
    execution = models.ForeignKey(PerformanceTestExecution, on_delete=models.SET_NULL, null=True, verbose_name='执行记录')
    status = models.CharField(max_length=20, default='SUCCESS', verbose_name='执行状态')
    message = models.TextField(blank=True, null=True, verbose_name='执行信息')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '性能测试定时任务执行日志'
        verbose_name_plural = '性能测试定时任务执行日志'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.task.name} - {self.created_at.strftime("%Y-%m-%d %H:%M:%S")}'
