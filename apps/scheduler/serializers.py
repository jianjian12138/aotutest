from rest_framework import serializers
from .models import ScheduledTask, NotificationConfig, TaskExecutionLog
from apps.projects.models import Project

class NotificationConfigSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    api_project_name = serializers.CharField(source='api_project.name', read_only=True, allow_null=True)
    
    class Meta:
        model = NotificationConfig
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at']

class ScheduledTaskSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True, allow_null=True)
    api_project_name = serializers.CharField(source='api_project.name', read_only=True, allow_null=True)
    notification_config_name = serializers.CharField(source='notification_config.name', read_only=True, allow_null=True)
    
    # Target names for display
    api_test_suite_name = serializers.CharField(source='api_test_suite.name', read_only=True, allow_null=True)
    ui_test_suite_name = serializers.CharField(source='ui_test_suite.name', read_only=True, allow_null=True)
    ui_test_case_name = serializers.CharField(source='ui_test_case.name', read_only=True, allow_null=True)
    performance_test_suite_name = serializers.CharField(source='performance_test_suite.name', read_only=True, allow_null=True)

    class Meta:
        model = ScheduledTask
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'last_run_time', 'next_run_time', 
                          'total_runs', 'successful_runs', 'failed_runs']

class TaskExecutionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskExecutionLog
        fields = '__all__'
