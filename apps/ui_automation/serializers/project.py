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


class UserSerializer(PIIMaskMixin, serializers.ModelSerializer):
    # 第六轮批次2：email 属 PII，非本人/非管理员输出掩码
    pii_masked_fields = ('email',)

    class Meta:
        model = User
        fields = ('id', 'username', 'email')


class UiProjectSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    members = UserSerializer(many=True, read_only=True)

    class Meta:
        model = UiProject
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class UiProjectCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UiProject
        fields = ('name', 'description', 'status', 'base_url', 'start_date', 'end_date', 'owner', 'members')


class UiProjectUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UiProject
        fields = ('name', 'description', 'status', 'base_url', 'start_date', 'end_date', 'members')


class UiDeviceSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    platform_display = serializers.CharField(source='get_platform_display', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)

    class Meta:
        model = UiDevice
        fields = '__all__'
        # organization / created_by 由服务端按当前登录用户回填，禁止客户端篡改（防跨租户挂载）
        read_only_fields = ('created_at', 'last_online', 'organization', 'created_by')


class ExecutionNodeSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    node_type_display = serializers.CharField(source='get_node_type_display', read_only=True)

    class Meta:
        model = ExecutionNode
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'last_heartbeat')


