from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    MidsceneConfig,
    MidsceneTask,
    MidsceneExecutionLog
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class MidsceneConfigSerializer(serializers.ModelSerializer):
    """Midscene.js配置序列化器"""
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = MidsceneConfig
        fields = '__all__'
        extra_kwargs = {
            'api_key': {'write_only': True},  # API密钥只在创建和更新时可见
        }


class MidsceneTaskSerializer(serializers.ModelSerializer):
    """Midscene.js任务序列化器"""
    config = MidsceneConfigSerializer(read_only=True)
    config_id = serializers.PrimaryKeyRelatedField(
        queryset=MidsceneConfig.objects.all(), source='config', write_only=True
    )
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = MidsceneTask
        fields = '__all__'


class MidsceneExecutionLogSerializer(serializers.ModelSerializer):
    """Midscene.js执行日志序列化器"""
    task = MidsceneTaskSerializer(read_only=True)

    class Meta:
        model = MidsceneExecutionLog
        fields = '__all__'
