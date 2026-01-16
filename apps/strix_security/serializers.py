from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    StrixConfig,
    SecurityTestProject,
    SecurityTestExecution,
    Vulnerability,
    SecurityTestHistory
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class StrixConfigSerializer(serializers.ModelSerializer):
    """Strix安全测试配置序列化器"""
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = StrixConfig
        fields = '__all__'
        extra_kwargs = {
            'api_key': {'write_only': True},  # API密钥只在创建和更新时可见
        }


class SecurityTestProjectSerializer(serializers.ModelSerializer):
    """安全测试项目序列化器"""
    config = StrixConfigSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = SecurityTestProject
        fields = '__all__'


class SecurityTestExecutionSerializer(serializers.ModelSerializer):
    """安全测试执行记录序列化器"""
    project = SecurityTestProjectSerializer(read_only=True)
    executed_by = UserSerializer(read_only=True)

    class Meta:
        model = SecurityTestExecution
        fields = '__all__'


class VulnerabilitySerializer(serializers.ModelSerializer):
    """漏洞记录序列化器"""
    execution = SecurityTestExecutionSerializer(read_only=True)

    class Meta:
        model = Vulnerability
        fields = '__all__'


class SecurityTestHistorySerializer(serializers.ModelSerializer):
    """安全测试历史记录序列化器"""
    project = SecurityTestProjectSerializer(read_only=True)
    execution = SecurityTestExecutionSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = SecurityTestHistory
        fields = '__all__'
