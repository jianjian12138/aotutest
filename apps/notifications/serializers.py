from rest_framework import serializers
from .models import NotificationConfig, NotificationLog


def mask_webhook_bots(webhook_bots):
    """对 webhook 机器人配置做只读掩码：隐藏 webhook_url 敏感段与 secret 明文。"""
    masked = {}
    for bot_type, cfg in (webhook_bots or {}).items():
        if not isinstance(cfg, dict):
            continue
        url = cfg.get('webhook_url') or ''
        masked[bot_type] = {
            'name': cfg.get('name', f'{bot_type}机器人'),
            'enabled': cfg.get('enabled', True),
            'webhook_url_masked': (url[:28] + '****') if url else '',
            'has_secret': bool(cfg.get('secret')),
        }
    return masked


class NotificationConfigSerializer(serializers.ModelSerializer):
    # 敏感：webhook_url/secret 只写不读，读侧提供掩码视图（D2 P0 修复）
    webhook_bots = serializers.JSONField(write_only=True, required=False)
    webhook_bots_masked = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = NotificationConfig
        fields = [
            'id', 'name', 'config_type', 'webhook_bots', 'webhook_bots_masked',
            'is_default', 'is_active', 'enable_ui_automation', 'enable_api_testing',
            'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def get_webhook_bots_masked(self, obj):
        return mask_webhook_bots(obj.webhook_bots)


class NotificationLogSerializer(serializers.ModelSerializer):
    # 敏感：recipient_info 含邮箱 PII、webhook_bot_info 可能含 webhook 地址——不输出原始 JSON
    recipient_display = serializers.CharField(source='get_recipient_names', read_only=True)

    class Meta:
        model = NotificationLog
        fields = [
            'id', 'module', 'task_id', 'task_name', 'notification_type',
            'sender_name', 'recipient_display', 'notification_content',
            'status', 'error_message', 'created_at', 'sent_at',
            'retry_count', 'is_retried',
        ]
        read_only_fields = fields
