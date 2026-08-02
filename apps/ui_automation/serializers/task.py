from apps.notifications.models import NotificationConfig, NotificationLog
from rest_framework import serializers
from django.utils import timezone
from ..models import (
    UiProject, LocatorStrategy, Element, TestScript, TestSuite,
    TestSuiteScript, TestSuiteTestCase, TestExecution, TestEnvironment, Screenshot,
    ElementGroup, PageObject, PageObjectElement, ScriptStep, ScriptElementUsage,
    TestCase, TestCaseStep, TestCaseExecution, OperationRecord,
    UiScheduledTask, UiTaskNotificationSetting, UiTestCaseModule,
    AICase, AIExecutionRecord, UiDevice, ExecutionNode
)
from django.contrib.auth import get_user_model
from apps.core_platform.masking import PIIMaskMixin

User = get_user_model()
from .project import UserSerializer, UiProjectSerializer

from .execution import TestSuiteSerializer, TestExecutionSerializer
from .testcase import TestCaseSerializer

class UiScheduledTaskSerializer(serializers.ModelSerializer):
    """UI定时任务序列化器"""
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    test_suite_name = serializers.CharField(source='test_suite.name', read_only=True)
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    trigger_type_display = serializers.CharField(source='get_trigger_type_display', read_only=True)
    notification_type_display = serializers.SerializerMethodField()

    class Meta:
        model = UiScheduledTask
        fields = [
            'id', 'name', 'description', 'task_type', 'task_type_display',
            'trigger_type', 'trigger_type_display', 'cron_expression',
            'interval_seconds', 'execute_at', 'project', 'project_name',
            'test_suite', 'test_suite_name', 'test_cases',
            'engine', 'browser', 'headless',
            'notify_on_success', 'notify_on_failure', 'notification_type', 'notification_type_display', 'notify_emails',
            'status', 'status_display',
            'last_run_time', 'next_run_time', 'total_runs',
            'successful_runs', 'failed_runs', 'last_result', 'error_message',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'created_by', 'last_run_time', 'next_run_time', 'total_runs',
            'successful_runs', 'failed_runs', 'last_result',
            'error_message', 'created_at', 'updated_at'
        ]

    def get_notification_type_display(self, obj):
        """获取通知类型显示"""
        if obj.notification_type:
            return obj.get_notification_type_display()
        return "-"

    def validate(self, attrs):
        """验证定时任务配置"""
        trigger_type = attrs.get('trigger_type')

        if trigger_type == 'CRON':
            if not attrs.get('cron_expression'):
                raise serializers.ValidationError("Cron表达式不能为空")

        elif trigger_type == 'INTERVAL':
            if not attrs.get('interval_seconds'):
                raise serializers.ValidationError("间隔秒数不能为空")
            if attrs['interval_seconds'] < 60:
                raise serializers.ValidationError("间隔秒数不能小于60秒")

        elif trigger_type == 'ONCE':
            if not attrs.get('execute_at'):
                raise serializers.ValidationError("执行时间不能为空")
            if attrs['execute_at'] <= timezone.now():
                raise serializers.ValidationError("执行时间必须大于当前时间")

        # 验证任务类型配置
        task_type = attrs.get('task_type')
        if task_type == 'TEST_SUITE' and not attrs.get('test_suite'):
            raise serializers.ValidationError("测试套件不能为空")
        elif task_type == 'TEST_CASE':
            test_cases = attrs.get('test_cases', [])
            if not test_cases or len(test_cases) == 0:
                raise serializers.ValidationError("至少选择一个测试用例")

        return attrs

    def create(self, validated_data):
        """创建定时任务"""
        validated_data['created_by'] = self.context['request'].user
        instance = super().create(validated_data)
        # 计算下次运行时间
        instance.next_run_time = instance.calculate_next_run()
        instance.save()

        # 创建对应的通知设置（如果启用了通知）
        if instance.notify_on_success or instance.notify_on_failure:
            from .models import UiTaskNotificationSetting

            # 确定通知类型（默认为webhook）
            notification_type = validated_data.get('notification_type', 'webhook')

            # 根据通知类型选择合适的通知配置
            notification_config = None
            if notification_type in ['webhook', 'both']:
                # 如果需要Webhook通知，优先选择Webhook配置
                notification_config = NotificationConfig.objects.filter(
                    config_type__in=['webhook_wechat', 'webhook_feishu', 'webhook_dingtalk'],
                    is_active=True
                ).first()

            if not notification_config:
                # 如果没有找到webhook配置或者是邮件通知，使用默认配置
                notification_config = NotificationConfig.objects.filter(
                    is_default=True,
                    is_active=True
                ).first()

            # 创建通知设置
            UiTaskNotificationSetting.objects.create(
                task=instance,
                notification_type=notification_type,
                is_enabled=True,
                notify_on_success=instance.notify_on_success,
                notify_on_failure=instance.notify_on_failure,
                notification_config=notification_config
            )

        return instance

    def update(self, instance, validated_data):
        """更新定时任务"""
        # 更新任务基本信息
        instance = super().update(instance, validated_data)

        # 重新计算下次运行时间
        instance.next_run_time = instance.calculate_next_run()
        instance.save()

        # 更新通知设置
        if instance.notify_on_success or instance.notify_on_failure:
            from .models import UiTaskNotificationSetting

            # 确定通知类型（默认为webhook）
            notification_type = validated_data.get('notification_type', 'webhook')

            # 根据通知类型选择合适的通知配置
            notification_config = None
            if notification_type in ['webhook', 'both']:
                # 如果需要Webhook通知，优先选择Webhook配置
                notification_config = NotificationConfig.objects.filter(
                    config_type__in=['webhook_wechat', 'webhook_feishu', 'webhook_dingtalk'],
                    is_active=True
                ).first()

            if not notification_config:
                # 如果没有找到webhook配置或者是邮件通知，使用默认配置
                notification_config = NotificationConfig.objects.filter(
                    is_default=True,
                    is_active=True
                ).first()

            # 获取或创建通知设置
            notification_setting, created = UiTaskNotificationSetting.objects.get_or_create(
                task=instance,
                defaults={
                    'notification_type': notification_type,
                    'is_enabled': True,
                    'notify_on_success': instance.notify_on_success,
                    'notify_on_failure': instance.notify_on_failure,
                    'notification_config': notification_config
                }
            )

            # 如果通知设置已存在，更新它
            if not created:
                notification_setting.notification_type = notification_type
                notification_setting.is_enabled = True
                notification_setting.notify_on_success = instance.notify_on_success
                notification_setting.notify_on_failure = instance.notify_on_failure
                notification_setting.notification_config = notification_config
                notification_setting.save()
        else:
            # 如果不需要通知，禁用通知设置
            from .models import UiTaskNotificationSetting
            UiTaskNotificationSetting.objects.filter(task=instance).update(is_enabled=False)

        return instance


class NotificationConfigSerializer(serializers.ModelSerializer):
    """UI通知配置序列化器"""
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    webhook_bots_display = serializers.SerializerMethodField()
    config_type_display = serializers.CharField(source='get_config_type_display', read_only=True)
    # 敏感：webhook_url/secret 只写不读（D2 P0 修复）
    webhook_bots = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = NotificationConfig
        fields = [
            'id', 'name', 'config_type', 'config_type_display',
            'webhook_bots', 'webhook_bots_display', 'is_default',
            'is_active', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by']
        extra_kwargs = {'webhook_bots': {'write_only': True}}

    def get_webhook_bots_display(self, obj):
        """获取webhook机器人显示信息"""
        bots = obj.get_webhook_bots()
        return f"{len(bots)} 个机器人配置" if bots else "未配置"

    def create(self, validated_data):
        """创建时自动设置创建者"""
        validated_data['created_by'] = self.context['request'].user
        instance = super().create(validated_data)
        return instance


class NotificationLogSerializer(PIIMaskMixin, serializers.ModelSerializer):
    """UI通知日志序列化器"""
    # 第六轮批次2：发件邮箱属 PII，仅管理员可见明文
    pii_masked_fields = ('sender_email',)
    recipient_names = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    retry_status = serializers.SerializerMethodField()
    task_type_display = serializers.SerializerMethodField()
    actual_notification_type_display = serializers.SerializerMethodField()

    class Meta:
        model = NotificationLog
        fields = [
            'id', 'task', 'task_name', 'notification_type',
            'notification_type_display', 'actual_notification_type_display', 'task_type_display',
            'sender_name', 'sender_email',
            'recipient_names', 'webhook_bot_info', 'notification_content',
            'status', 'status_display', 'error_message', 'response_info',
            'created_at', 'sent_at', 'retry_count', 'retry_status'
        ]
        read_only_fields = ['created_at', 'sent_at']

    def get_recipient_names(self, obj):
        """获取收件人姓名列表"""
        return obj.get_recipient_names()

    def get_retry_status(self, obj):
        """获取重试状态"""
        return obj.get_retry_status()

    def get_task_type_display(self, obj):
        """获取任务类型显示"""
        if obj.task:
            task_type_choices = dict(UiScheduledTask.TASK_TYPE_CHOICES)
            return task_type_choices.get(obj.task.task_type, obj.task.task_type)
        return '-'

    def get_actual_notification_type_display(self, obj):
        """获取实际的通知类型显示 - 根据实际发送的通知来判断"""
        # 优先检查webhook_bot_info,如果存在则说明是webhook通知
        if obj.webhook_bot_info:
            bot_type = obj.webhook_bot_info.get('bot_type', '') or obj.webhook_bot_info.get('type', '')
            # 根据机器人类型返回友好名称
            type_map = {
                'wechat': '企微机器人',
                'feishu': '飞书机器人',
                'dingtalk': '钉钉机器人'
            }
            return type_map.get(bot_type, 'Webhook机器人')

        # 检查recipient_info,如果存在则说明是邮箱通知
        if obj.recipient_info:
            if isinstance(obj.recipient_info, list) and len(obj.recipient_info) > 0:
                return '邮箱通知'
            elif isinstance(obj.recipient_info, dict) and obj.recipient_info.get('email'):
                return '邮箱通知'

        # 如果都没有,回退到任务的notification_type
        if obj.task:
            notification_type = obj.task.notification_type
            type_map = {
                'email': '邮箱通知',
                'webhook': 'Webhook机器人',
                'both': '两种都发送'
            }
            return type_map.get(notification_type, notification_type)

        return '-'


class UiTaskNotificationSettingSerializer(serializers.ModelSerializer):
    """UI任务通知设置序列化器"""
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    notification_config_name = serializers.CharField(source='notification_config.name', read_only=True)
    active_types = serializers.SerializerMethodField()

    class Meta:
        model = UiTaskNotificationSetting
        fields = [
            'id', 'task', 'notification_type', 'notification_type_display',
            'notification_config', 'notification_config_name', 'is_enabled',
            'notify_on_success', 'notify_on_failure', 'notify_on_timeout',
            'notify_on_error', 'custom_webhook_bots', 'active_types',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_active_types(self, obj):
        """获取激活的通知类型"""
        types = obj.get_active_notification_types()
        type_names = []
        if 'email' in types:
            type_names.append('邮箱')
        if 'webhook' in types:
            type_names.append('Webhook机器人')
        return ', '.join(type_names) if type_names else "无"


