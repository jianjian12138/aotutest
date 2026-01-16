from django.contrib import admin
from .models import TestCaseReview, ReviewAssignment, TestCaseReviewComment, ReviewTemplate


@admin.register(TestCaseReview)
class TestCaseReviewAdmin(admin.ModelAdmin):
    list_display = ['title', 'get_projects', 'creator', 'status', 'priority', 'created_at']
    list_filter = ['status', 'priority', 'created_at']
    search_fields = ['title', 'description']
    date_hierarchy = 'created_at'
    filter_horizontal = ['projects', 'testcases']
    
    def get_projects(self, obj):
        return ", ".join([p.name for p in obj.projects.all()])
    get_projects.short_description = '关联项目'


@admin.register(ReviewAssignment)  
class ReviewAssignmentAdmin(admin.ModelAdmin):
    list_display = ['review', 'reviewer', 'status', 'assigned_at', 'reviewed_at']
    list_filter = ['status', 'assigned_at', 'reviewed_at']


@admin.register(TestCaseReviewComment)
class TestCaseReviewCommentAdmin(admin.ModelAdmin):
    list_display = ['review', 'author', 'comment_type', 'is_resolved', 'created_at']
    list_filter = ['comment_type', 'is_resolved', 'created_at']


@admin.register(ReviewTemplate)
class ReviewTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_projects', 'creator', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    filter_horizontal = ['project', 'default_reviewers']
    
    def get_projects(self, obj):
        return ", ".join([p.name for p in obj.project.all()])
    get_projects.short_description = '关联项目'