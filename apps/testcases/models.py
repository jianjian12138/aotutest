from django.db import models
from django.utils import timezone
from apps.users.models import User
from apps.projects.models import Project
from apps.versions.models import Version

class TestCase(models.Model):
    """测试用例模型"""
    PRIORITY_CHOICES = [
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('critical', '紧急'),
    ]
    
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('active', '激活'),
        ('deprecated', '废弃'),
    ]
    
    TYPE_CHOICES = [
        ('functional', '功能测试'),
        ('integration', '集成测试'),
        ('api', 'API测试'),
        ('ui', 'UI测试'),
        ('performance', '性能测试'),
        ('security', '安全测试'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='testcases')
    versions = models.ManyToManyField(Version, blank=True, related_name='testcases', verbose_name='关联版本')
    title = models.CharField(max_length=500, verbose_name='用例标题')
    description = models.TextField(blank=True, verbose_name='用例描述')
    preconditions = models.TextField(blank=True, verbose_name='前置条件')
    steps = models.TextField(blank=True, max_length=1000, verbose_name='操作步骤')
    expected_result = models.TextField(verbose_name='预期结果')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium', verbose_name='优先级')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='状态')
    test_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='functional', verbose_name='测试类型')
    tags = models.JSONField(default=list, verbose_name='标签')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='authored_testcases', verbose_name='作者')
    assignee = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_testcases', verbose_name='指派人')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    def __str__(self):
        return self.title
    
    class Meta:
        db_table = 'testcases'
        verbose_name = '测试用例'
        verbose_name_plural = '测试用例'
        ordering = ['-created_at']

class TestCaseStep(models.Model):
    """测试用例步骤"""
    testcase = models.ForeignKey(TestCase, on_delete=models.CASCADE, related_name='step_details')
    step_number = models.PositiveIntegerField(verbose_name='步骤序号')
    action = models.TextField(verbose_name='操作')
    expected = models.TextField(verbose_name='预期结果')
    
    class Meta:
        db_table = 'testcase_steps'
        unique_together = ['testcase', 'step_number']
        ordering = ['step_number']
        verbose_name = '测试用例步骤'
        verbose_name_plural = '测试用例步骤'

class TestCaseAttachment(models.Model):
    """测试用例附件"""
    testcase = models.ForeignKey(TestCase, on_delete=models.CASCADE, related_name='attachments')
    name = models.CharField(max_length=255, verbose_name='附件名称')
    file = models.FileField(upload_to='testcase_attachments/', verbose_name='文件')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='上传者')
    uploaded_at = models.DateTimeField(default=timezone.now, verbose_name='上传时间')
    
    class Meta:
        db_table = 'testcase_attachments'
        verbose_name = '测试用例附件'
        verbose_name_plural = '测试用例附件'

class TestCaseComment(models.Model):
    """测试用例评论"""
    testcase = models.ForeignKey(TestCase, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='评论者')
    content = models.TextField(verbose_name='评论内容')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='评论时间')
    
    class Meta:
        db_table = 'testcase_comments'
        verbose_name = '测试用例评论'
        verbose_name_plural = '测试用例评论'
        ordering = ['-created_at']