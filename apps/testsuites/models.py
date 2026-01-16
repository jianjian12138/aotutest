from django.db import models
from django.utils import timezone
from apps.users.models import User
from apps.projects.models import Project
from apps.testcases.models import TestCase

class TestSuite(models.Model):
    """测试套件"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='testsuites')
    name = models.CharField(max_length=200, verbose_name='套件名称')
    description = models.TextField(blank=True, verbose_name='套件描述')
    testcases = models.ManyToManyField(TestCase, through='TestSuiteCase', verbose_name='测试用例')
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='创建者')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'testsuites'
        verbose_name = '测试套件'
        verbose_name_plural = '测试套件'
        ordering = ['-created_at']

class TestSuiteCase(models.Model):
    """测试套件用例关联"""
    testsuite = models.ForeignKey(TestSuite, on_delete=models.CASCADE)
    testcase = models.ForeignKey(TestCase, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0, verbose_name='执行顺序')
    
    class Meta:
        db_table = 'testsuite_cases'
        unique_together = ['testsuite', 'testcase']
        ordering = ['order']
        verbose_name = '测试套件用例'
        verbose_name_plural = '测试套件用例'