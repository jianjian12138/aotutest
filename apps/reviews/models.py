from django.db import models
from django.utils import timezone
from apps.users.models import User
from apps.projects.models import Project
from apps.testcases.models import TestCase


class TestCaseReview(models.Model):
    """测试用例评审"""
    STATUS_CHOICES = [
        ('pending', '待评审'),
        ('in_progress', '评审中'),
        ('approved', '已通过'),
        ('rejected', '已拒绝'),
        ('cancelled', '已取消'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('urgent', '紧急'),
    ]
    
    title = models.CharField(max_length=500, verbose_name='评审标题')
    description = models.TextField(blank=True, verbose_name='评审描述')
    projects = models.ManyToManyField(Project, related_name='reviews', verbose_name='关联项目')
    testcases = models.ManyToManyField(TestCase, related_name='reviews', verbose_name='评审用例')
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_reviews', verbose_name='创建人')
    reviewers = models.ManyToManyField(User, through='ReviewAssignment', related_name='assigned_reviews', verbose_name='评审人员')
    template = models.ForeignKey('ReviewTemplate', on_delete=models.SET_NULL, null=True, blank=True, related_name='used_in_reviews', verbose_name='使用的模板')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='评审状态')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium', verbose_name='优先级')
    deadline = models.DateTimeField(null=True, blank=True, verbose_name='截止日期')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    
    class Meta:
        db_table = 'testcase_reviews'
        verbose_name = '测试用例评审'
        verbose_name_plural = '测试用例评审'
        ordering = ['-created_at']


class ReviewAssignment(models.Model):
    """评审分配"""
    STATUS_CHOICES = [
        ('pending', '待评审'),
        ('approved', '已通过'), 
        ('rejected', '已拒绝'),
        ('abstained', '弃权'),
    ]
    
    review = models.ForeignKey(TestCaseReview, on_delete=models.CASCADE, verbose_name='评审')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='评审人')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='评审状态')
    comment = models.TextField(blank=True, verbose_name='评审意见')
    checklist_results = models.JSONField(default=dict, blank=True, verbose_name='检查清单结果')  # 存储每个检查项的通过/不通过状态
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='评审时间')
    assigned_at = models.DateTimeField(default=timezone.now, verbose_name='分配时间')
    
    class Meta:
        db_table = 'review_assignments'
        unique_together = ['review', 'reviewer']
        verbose_name = '评审分配'
        verbose_name_plural = '评审分配'


class TestCaseReviewComment(models.Model):
    """用例评审意见"""
    COMMENT_TYPE_CHOICES = [
        ('general', '整体意见'),
        ('testcase', '用例意见'),
        ('step', '步骤意见'),
    ]
    
    review = models.ForeignKey(TestCaseReview, on_delete=models.CASCADE, related_name='comments', verbose_name='评审')
    testcase = models.ForeignKey(TestCase, on_delete=models.CASCADE, null=True, blank=True, related_name='review_comments', verbose_name='相关用例')
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='评论者')
    comment_type = models.CharField(max_length=20, choices=COMMENT_TYPE_CHOICES, default='general', verbose_name='意见类型')
    content = models.TextField(verbose_name='意见内容')
    step_number = models.PositiveIntegerField(null=True, blank=True, verbose_name='步骤序号')
    is_resolved = models.BooleanField(default=False, verbose_name='是否已解决')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'review_comments'
        verbose_name = '评审意见'
        verbose_name_plural = '评审意见'
        ordering = ['-created_at']


class ReviewTemplate(models.Model):
    """评审模板"""
    name = models.CharField(max_length=200, verbose_name='模板名称')
    description = models.TextField(blank=True, verbose_name='模板描述')
    project = models.ManyToManyField(Project, related_name='review_templates', verbose_name='关联项目')
    creator = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='创建人')
    checklist = models.JSONField(default=list, verbose_name='检查清单')  # 检查项列表
    default_reviewers = models.ManyToManyField(User, blank=True, related_name='template_reviews', verbose_name='默认评审人')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'review_templates'
        verbose_name = '评审模板'
        verbose_name_plural = '评审模板'
        ordering = ['-created_at']