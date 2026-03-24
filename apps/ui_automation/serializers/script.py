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

User = get_user_model()
from .project import UserSerializer
from .element import ElementEnhancedSerializer, ElementSerializer, PageObjectSerializer

from .project import UiProjectSerializer, UserSerializer
from .element import ElementEnhancedSerializer, ElementSerializer, PageObjectSerializer, LocatorStrategySerializer

class TestScriptSerializer(serializers.ModelSerializer):
    project = UiProjectSerializer(read_only=True)
    project_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = TestScript
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class TestScriptCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestScript
        fields = ('project', 'name', 'description', 'script_type', 'content', 'language', 'framework')


class TestScriptUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestScript
        fields = ('name', 'description', 'script_type', 'content')


class ScriptStepSerializer(serializers.ModelSerializer):
    script = TestScriptSerializer(read_only=True)
    target_element = ElementEnhancedSerializer(read_only=True)
    page_object = PageObjectSerializer(read_only=True)

    script_id = serializers.IntegerField(write_only=True)
    target_element_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    page_object_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = ScriptStep
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def validate(self, data):
        """验证步骤配置"""
        target_element_id = data.get('target_element_id')
        page_object_id = data.get('page_object_id')
        action_type = data.get('action_type')

        # 某些操作类型需要指定目标元素
        if action_type in ['CLICK', 'INPUT', 'SELECT', 'HOVER', 'VERIFY'] and not target_element_id and not page_object_id:
            raise serializers.ValidationError("此操作类型需要指定目标元素或页面对象")

        return data


class ScriptElementUsageSerializer(serializers.ModelSerializer):
    script = TestScriptSerializer(read_only=True)
    element = ElementEnhancedSerializer(read_only=True)
    script_id = serializers.IntegerField(write_only=True)
    element_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ScriptElementUsage
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class ScriptAnalysisSerializer(serializers.Serializer):
    """脚本分析结果序列化器"""
    element_usages = ScriptElementUsageSerializer(many=True, read_only=True)
    missing_elements = serializers.ListField(child=serializers.CharField(), read_only=True)
    recommendations = serializers.ListField(child=serializers.CharField(), read_only=True)
    complexity_score = serializers.IntegerField(read_only=True)


class ElementValidationSerializer(serializers.Serializer):
    """元素验证结果序列化器"""
    is_valid = serializers.BooleanField(read_only=True)
    validation_message = serializers.CharField(read_only=True)
    suggestions = serializers.ListField(child=serializers.CharField(), read_only=True)


class CodeGenerationSerializer(serializers.Serializer):
    """代码生成序列化器"""
    language = serializers.ChoiceField(choices=[('javascript', 'JavaScript'), ('python', 'Python')], default='javascript')
    framework = serializers.ChoiceField(choices=[('playwright', 'Playwright'), ('selenium', 'Selenium')], default='playwright')
    include_comments = serializers.BooleanField(default=True)

    def validate(self, data):
        # 可以添加更多验证逻辑
        return data


