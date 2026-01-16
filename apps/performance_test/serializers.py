from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    PerformanceProject,
    PerformanceCollection,
    PerformanceRequest,
    PerformanceEnvironment,
    PerformanceTestSuite,
    PerformanceTestSuiteRequest,
    PerformanceTestExecution,
    PerformanceTestHistory,
    PerformanceScheduledTask,
    PerformanceTaskExecutionLog
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class PerformanceProjectSerializer(serializers.ModelSerializer):
    """性能测试项目序列化器"""
    owner = UserSerializer(read_only=True)
    members = UserSerializer(many=True, read_only=True)

    class Meta:
        model = PerformanceProject
        fields = '__all__'


class PerformanceCollectionSerializer(serializers.ModelSerializer):
    """性能测试集合序列化器"""
    project = PerformanceProjectSerializer(read_only=True)
    parent = serializers.PrimaryKeyRelatedField(queryset=PerformanceCollection.objects.all(), allow_null=True, required=False)

    class Meta:
        model = PerformanceCollection
        fields = '__all__'


class PerformanceRequestSerializer(serializers.ModelSerializer):
    """性能测试请求序列化器"""
    collection = PerformanceCollectionSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = PerformanceRequest
        fields = '__all__'


class PerformanceEnvironmentSerializer(serializers.ModelSerializer):
    """性能测试环境序列化器"""
    created_by = UserSerializer(read_only=True)
    project = PerformanceProjectSerializer(read_only=True, allow_null=True)

    class Meta:
        model = PerformanceEnvironment
        fields = '__all__'


class PerformanceTestSuiteRequestSerializer(serializers.ModelSerializer):
    """性能测试套件请求关联序列化器"""
    test_suite = serializers.PrimaryKeyRelatedField(queryset=PerformanceTestSuite.objects.all())
    request = PerformanceRequestSerializer(read_only=True)

    class Meta:
        model = PerformanceTestSuiteRequest
        fields = '__all__'


class PerformanceTestSuiteSerializer(serializers.ModelSerializer):
    """性能测试套件序列化器"""
    project = PerformanceProjectSerializer(read_only=True)
    environment = PerformanceEnvironmentSerializer(read_only=True, allow_null=True)
    created_by = UserSerializer(read_only=True)
    test_suite_requests = PerformanceTestSuiteRequestSerializer(many=True, read_only=True)

    class Meta:
        model = PerformanceTestSuite
        fields = '__all__'


class PerformanceTestExecutionSerializer(serializers.ModelSerializer):
    """性能测试执行记录序列化器"""
    test_suite = PerformanceTestSuiteSerializer(read_only=True)
    executed_by = UserSerializer(read_only=True)

    class Meta:
        model = PerformanceTestExecution
        fields = '__all__'


class PerformanceTestHistorySerializer(serializers.ModelSerializer):
    """性能测试历史记录序列化器"""
    execution = PerformanceTestExecutionSerializer(read_only=True)
    request = PerformanceRequestSerializer(read_only=True)
    environment = PerformanceEnvironmentSerializer(read_only=True, allow_null=True)

    class Meta:
        model = PerformanceTestHistory
        fields = '__all__'


class PerformanceScheduledTaskSerializer(serializers.ModelSerializer):
    """性能测试定时任务序列化器"""
    test_suite = PerformanceTestSuiteSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = PerformanceScheduledTask
        fields = '__all__'


class PerformanceTaskExecutionLogSerializer(serializers.ModelSerializer):
    """性能测试定时任务执行日志序列化器"""
    task = PerformanceScheduledTaskSerializer(read_only=True)
    execution = PerformanceTestExecutionSerializer(read_only=True, allow_null=True)

    class Meta:
        model = PerformanceTaskExecutionLog
        fields = '__all__'
