from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    WHartTestConfig,
    WHartTestProject,
    WHartTestExecution,
    WHartTestTask,
    WHartTestIntegrationLog
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class WHartTestConfigSerializer(serializers.ModelSerializer):
    """WHartTest配置序列化器"""
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = WHartTestConfig
        fields = '__all__'
        extra_kwargs = {
            'api_key': {'write_only': True},  # API密钥只在创建和更新时可见
        }


class WHartTestProjectSerializer(serializers.ModelSerializer):
    """WHartTest项目关联序列化器"""
    config = WHartTestConfigSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = WHartTestProject
        fields = '__all__'


class WHartTestExecutionSerializer(serializers.ModelSerializer):
    """WHartTest执行记录序列化器"""
    project = WHartTestProjectSerializer(read_only=True)
    executed_by = UserSerializer(read_only=True)

    class Meta:
        model = WHartTestExecution
        fields = '__all__'


class WHartTestTaskSerializer(serializers.ModelSerializer):
    """WHartTest任务序列化器"""
    project = WHartTestProjectSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = WHartTestTask
        fields = '__all__'


class WHartTestIntegrationLogSerializer(serializers.ModelSerializer):
    """WHartTest集成日志序列化器"""
    config = WHartTestConfigSerializer(read_only=True)

    class Meta:
        model = WHartTestIntegrationLog
        fields = '__all__'
