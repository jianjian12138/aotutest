from apps.notifications.models import NotificationConfig, NotificationLog
from rest_framework import serializers
from .models import ScheduledTask, TaskExecutionLog
from apps.core_platform.models import Project

class NotificationConfigSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    # 敏感：webhook_url/secret 只写不读，读侧提供掩码视图（D2 P0 修复）
    webhook_bots = serializers.JSONField(write_only=True, required=False)
    webhook_bots_masked = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = NotificationConfig
        fields = [
            'id', 'name', 'config_type', 'webhook_bots', 'webhook_bots_masked',
            'is_default', 'is_active', 'enable_ui_automation', 'enable_api_testing',
            'created_at', 'updated_at', 'created_by', 'created_by_name',
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def get_webhook_bots_masked(self, obj):
        from apps.notifications.serializers import mask_webhook_bots
        return mask_webhook_bots(obj.webhook_bots)

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
