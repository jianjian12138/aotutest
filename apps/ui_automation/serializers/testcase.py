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
from .project import UserSerializer, UiProjectSerializer
from .element import ElementEnhancedSerializer, ElementSerializer, PageObjectSerializer

class UiTestCaseModuleSerializer(serializers.ModelSerializer):
    """UI测试用例模块序列化器"""
    children = serializers.SerializerMethodField()
    test_case_count = serializers.SerializerMethodField()

    class Meta:
        model = UiTestCaseModule
        fields = ['id', 'name', 'project', 'parent', 'order', 'children', 'test_case_count', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_children(self, obj):
        children = obj.children.all()
        return UiTestCaseModuleSerializer(children, many=True).data

    def get_test_case_count(self, obj):
        return obj.test_cases.count()


class TestCaseStepSerializer(serializers.ModelSerializer):
    """测试用例步骤序列化器"""
    element_name = serializers.CharField(source='element.name', read_only=True)
    element_locator = serializers.CharField(source='element.locator_value', read_only=True)

    class Meta:
        model = TestCaseStep
        fields = [
            'id', 'step_number', 'action_type', 'element', 'element_name', 'element_locator',
            'input_value', 'wait_time', 'assert_type', 'assert_value', 'description',
            'enable_debug_capture', 'created_at'
        ]


class TestCaseSerializer(serializers.ModelSerializer):
    """测试用例序列化器"""
    steps = TestCaseStepSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    project_id = serializers.IntegerField(write_only=True, required=False)
    module_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = TestCase
        fields = [
            'id', 'name', 'description', 'project', 'project_id', 'project_name', 'module', 'module_id', 'status', 'priority',
            'created_by', 'created_by_name', 'created_at', 'updated_at', 'steps'
        ]
        read_only_fields = ['created_by', 'project', 'module']

    def validate(self, attrs):
        if not attrs.get('project_id') and not self.instance:
            raise serializers.ValidationError({'project_id': '请选择所属项目'})
        return attrs

    def create(self, validated_data):
        project_id = validated_data.pop('project_id', None)
        if project_id:
            try:
                validated_data['project'] = UiProject.objects.get(id=project_id)
            except UiProject.DoesNotExist:
                raise serializers.ValidationError({'project_id': '所选项目不存在'})
        
        validated_data['created_by'] = self.context['request'].user
        
        module_id = validated_data.pop('module_id', None)
        if module_id:
            try:
                validated_data['module'] = UiTestCaseModule.objects.get(id=module_id)
            except UiTestCaseModule.DoesNotExist:
                pass
                
        return super().create(validated_data)

    def update(self, instance, validated_data):
        module_id = validated_data.pop('module_id', None)
        if module_id is not None:
            if module_id:
                try:
                    validated_data['module'] = UiTestCaseModule.objects.get(id=module_id)
                except UiTestCaseModule.DoesNotExist:
                    pass
            else:
                validated_data['module'] = None
                
        return super().update(instance, validated_data)


class TestCaseExecutionSerializer(serializers.ModelSerializer):
    """测试用例执行记录序列化器"""
    test_case_name = serializers.CharField(source='test_case.name', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    test_suite_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = TestCaseExecution
        fields = [
            'id', 'test_case', 'test_case_name', 'project', 'project_name',
            'test_suite', 'test_suite_name', 'execution_source', 'status',
            'engine', 'browser', 'headless', 'execution_logs', 'error_message',
            'screenshots', 'execution_time', 'started_at', 'finished_at',
            'created_by', 'created_by_name', 'created_at'
        ]
        read_only_fields = ['created_by']
    
    def get_test_suite_name(self, obj):
        """获取测试套件名称"""
        return obj.test_suite.name if obj.test_suite else None
    
    def get_created_by_name(self, obj):
        """获取创建人姓名"""
        return obj.created_by.username if obj.created_by else '-'

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class TestCaseRunSerializer(serializers.Serializer):
    """测试用例运行序列化器"""
    test_case_id = serializers.IntegerField()
    project_id = serializers.IntegerField()
    browser = serializers.ChoiceField(choices=['chrome', 'firefox', 'safari'], default='chrome')

    def validate_test_case_id(self, value):
        try:
            TestCase.objects.get(id=value)
        except TestCase.DoesNotExist:
            raise serializers.ValidationError("测试用例不存在")
        return value

    def validate_project_id(self, value):
        try:
            UiProject.objects.get(id=value)
        except UiProject.DoesNotExist:
            raise serializers.ValidationError("项目不存在")
        return value


class AICaseSerializer(serializers.ModelSerializer):
    project = UiProjectSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    project_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = AICase
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'created_by')

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class AIExecutionRecordSerializer(serializers.ModelSerializer):
    project = UiProjectSerializer(read_only=True)
    ai_case = AICaseSerializer(read_only=True)
    executed_by = UserSerializer(read_only=True)
    project_id = serializers.IntegerField(write_only=True)
    ai_case_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    ai_case_name = serializers.CharField(source='ai_case.name', read_only=True)
    executed_by_name = serializers.CharField(source='executed_by.username', read_only=True)

    class Meta:
        model = AIExecutionRecord
        fields = [
            'id', 'project', 'project_id', 'project_name', 'ai_case', 'ai_case_id', 'ai_case_name', 'case_name',
            'task_description',
            'execution_mode', 'status', 'start_time', 'end_time', 'duration',
            'logs', 'steps_completed', 'planned_tasks', 'executed_by', 'executed_by_name',
            'gif_path', 'screenshots_sequence'
        ]
        read_only_fields = ('start_time', 'end_time', 'duration', 'executed_by', 'gif_path', 'screenshots_sequence')


