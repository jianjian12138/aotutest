from django.contrib import admin
from .models import Defect, DefectHistory


@admin.register(Defect)
class DefectAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'status', 'severity', 'priority', 'assignee', 'project', 'created_at')
    list_filter = ('status', 'severity', 'priority', 'project')
    search_fields = ('title', 'description', 'steps')
    readonly_fields = ('reporter', 'created_at', 'updated_at')


@admin.register(DefectHistory)
class DefectHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'defect', 'from_status', 'to_status', 'actor', 'created_at')
    readonly_fields = ('defect', 'from_status', 'to_status', 'actor', 'comment', 'created_at')
