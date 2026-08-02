from rest_framework import serializers
from .models import CICDServer, CICDJob, CICDExecution, CICDLog, GitLabRepository, CICDTrigger


class CICDServerSerializer(serializers.ModelSerializer):
    """CI/CD服务器序列化器"""
    server_type_display = serializers.CharField(source='get_server_type_display', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = CICDServer
        fields = ['id', 'name', 'server_type', 'server_type_display', 'url', 'username', 'password', 'token', 'is_active', 'created_by', 'created_by_username', 'created_at', 'updated_at']
        extra_kwargs = {
            'password': {'write_only': True},  # 密码只在写入时可用，不回传
            'token': {'write_only': True},     # API Token 同样不回传（安全整改）
        }


class CICDJobSerializer(serializers.ModelSerializer):
    """CI/CD任务序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    server_name = serializers.CharField(source='server.name', read_only=True)
    server_type = serializers.CharField(source='server.server_type', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = CICDJob
        fields = ['id', 'name', 'description', 'server', 'server_name', 'server_type', 'job_name', 'job_url', 'status', 'status_display', 'created_by', 'created_by_username', 'created_at', 'updated_at']


class CICDExecutionSerializer(serializers.ModelSerializer):
    """CI/CD执行记录序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    job_name = serializers.CharField(source='job.name', read_only=True)
    triggered_by_username = serializers.CharField(source='triggered_by.username', read_only=True, allow_null=True)

    class Meta:
        model = CICDExecution
        fields = ['id', 'job', 'job_name', 'execution_id', 'build_number', 'status', 'status_display', 'parameters', 'start_time', 'end_time', 'duration', 'triggered_by', 'triggered_by_username', 'created_at']


class CICDLogSerializer(serializers.ModelSerializer):
    """CI/CD执行日志序列化器"""
    execution_name = serializers.CharField(source='execution.job.name', read_only=True)
    build_number = serializers.IntegerField(source='execution.build_number', read_only=True)

    class Meta:
        model = CICDLog
        fields = ['id', 'execution', 'execution_name', 'build_number', 'log_content', 'log_url', 'created_at']


class GitLabRepositorySerializer(serializers.ModelSerializer):
    """GitLab仓库序列化器"""
    server_name = serializers.CharField(source='server.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = GitLabRepository
        fields = ['id', 'name', 'repository_url', 'project_id', 'server', 'server_name', 'created_by', 'created_by_username', 'created_at', 'updated_at']


class CICDTriggerSerializer(serializers.ModelSerializer):
    """CI/CD触发配置序列化器"""
    trigger_type_display = serializers.CharField(source='get_trigger_type_display', read_only=True)
    job_name = serializers.CharField(source='job.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    # 敏感：webhook_url 可能含鉴权 token，只写不读，读侧提供掩码（D2 P0 修复）
    webhook_url = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    webhook_url_masked = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CICDTrigger
        fields = ['id', 'job', 'job_name', 'trigger_type', 'trigger_type_display', 'cron_expression',
                  'webhook_url', 'webhook_url_masked', 'is_active', 'created_by', 'created_by_username',
                  'created_at', 'updated_at']
        extra_kwargs = {'webhook_url': {'write_only': True}}

    def get_webhook_url_masked(self, obj):
        url = obj.webhook_url or ''
        return (url[:28] + '****') if url else ''


class TriggerExecutionSerializer(serializers.Serializer):
    """触发执行序列化器"""
    parameters = serializers.JSONField(default=dict, help_text='执行参数')
