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
from .script import TestScriptSerializer
from .testcase import TestCaseSerializer

class TestSuiteScriptSerializer(serializers.ModelSerializer):
    test_script = TestScriptSerializer(read_only=True)
    test_script_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = TestSuiteScript
        fields = ('id', 'test_script', 'test_script_id', 'order')


class TestSuiteTestCaseSerializer(serializers.ModelSerializer):
    test_case = serializers.SerializerMethodField()
    test_case_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = TestSuiteTestCase
        fields = ('id', 'test_case', 'test_case_id', 'order')

    def get_test_case(self, obj):
        """获取测试用例信息"""
        test_case = obj.test_case
        return {
            'id': test_case.id,
            'name': test_case.name,
            'description': test_case.description,
            'status': test_case.status,
            'priority': test_case.priority,
            'created_at': test_case.created_at
        }


class TestSuiteSerializer(serializers.ModelSerializer):
    project = UiProjectSerializer(read_only=True)
    scripts = TestScriptSerializer(many=True, read_only=True)
    test_cases_data = serializers.SerializerMethodField()
    project_id = serializers.IntegerField(write_only=True)
    suite_scripts = TestSuiteScriptSerializer(many=True, read_only=True)
    suite_test_cases = TestSuiteTestCaseSerializer(many=True, read_only=True)
    test_case_count = serializers.SerializerMethodField()

    class Meta:
        model = TestSuite
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'execution_status', 'passed_count', 'failed_count')

    def get_test_cases_data(self, obj):
        """获取测试用例数据"""
        return TestSuiteTestCaseSerializer(obj.suite_test_cases.all(), many=True).data

    def get_test_case_count(self, obj):
        """获取测试用例数量"""
        return obj.suite_test_cases.count()


class TestSuiteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestSuite
        fields = ('id', 'project', 'name', 'description')
        read_only_fields = ('id',)


class TestSuiteUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestSuite
        fields = ('name', 'description')


class TestSuiteWithScriptsSerializer(serializers.ModelSerializer):
    project = UiProjectSerializer(read_only=True)
    suite_scripts = TestSuiteScriptSerializer(many=True, read_only=True)

    class Meta:
        model = TestSuite
        fields = '__all__'


class TestExecutionSerializer(serializers.ModelSerializer):
    project = UiProjectSerializer(read_only=True)
    test_suite = TestSuiteSerializer(read_only=True)
    test_script = TestScriptSerializer(read_only=True)
    executed_by = UserSerializer(read_only=True)
    project_id = serializers.IntegerField(write_only=True)
    test_suite_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    test_script_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    executed_by_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    # 添加计算字段
    test_suite_name = serializers.SerializerMethodField()
    executed_by_name = serializers.SerializerMethodField()
    pass_rate = serializers.SerializerMethodField()

    class Meta:
        model = TestExecution
        fields = '__all__'
        read_only_fields = (
            'created_at', 'started_at', 'finished_at', 'duration',
            'total_cases', 'passed_cases', 'failed_cases', 'skipped_cases'
        )

    def get_test_suite_name(self, obj):
        """获取测试套件名称"""
        return obj.test_suite.name if obj.test_suite else '-'
    
    def get_executed_by_name(self, obj):
        """获取执行人姓名"""
        return obj.executed_by.username if obj.executed_by else '-'

    def get_pass_rate(self, obj):
        """获取通过率"""
        return obj.pass_rate


class TestExecutionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestExecution
        fields = ('project', 'test_suite', 'test_script', 'environment', 'executed_by')


class ScreenshotSerializer(serializers.ModelSerializer):
    execution = TestExecutionSerializer(read_only=True)
    execution_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Screenshot
        fields = '__all__'
        read_only_fields = ('created_at', 'captured_at')


class OperationRecordSerializer(serializers.ModelSerializer):
    """操作记录序列化器"""
    user_name = serializers.CharField(source='user.username', read_only=True)
    operation_type_display = serializers.CharField(source='get_operation_type_display', read_only=True)
    resource_type_display = serializers.CharField(source='get_resource_type_display', read_only=True)

    class Meta:
        model = OperationRecord
        fields = [
            'id', 'operation_type', 'operation_type_display', 'resource_type',
            'resource_type_display', 'resource_id', 'resource_name', 'description',
            'user', 'user_name', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


