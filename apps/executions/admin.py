from django.contrib import admin
from .models import TestPlan, TestRun, TestRunCase, TestRunCaseHistory

@admin.register(TestPlan)
class TestPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'version', 'creator', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at', 'version')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('projects', 'assignees')  # 为ManyToManyField添加更好的界面

@admin.register(TestRun)
class TestRunAdmin(admin.ModelAdmin):
    list_display = ('name', 'test_plan', 'project', 'status', 'assignee', 'created_at')
    list_filter = ('status', 'created_at', 'project')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(TestRunCase)
class TestRunCaseAdmin(admin.ModelAdmin):
    list_display = ('testcase', 'test_run', 'status', 'priority', 'executed_by', 'executed_at')
    list_filter = ('status', 'priority', 'executed_at')
    search_fields = ('testcase__title', 'actual_result', 'comments')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(TestRunCaseHistory)
class TestRunCaseHistoryAdmin(admin.ModelAdmin):
    list_display = ('run_case', 'status', 'executed_by', 'executed_at')
    list_filter = ('status', 'executed_at')
    search_fields = ('actual_result', 'comments')
    readonly_fields = ('executed_at',)