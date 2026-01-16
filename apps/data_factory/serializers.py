from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    VannaConfig,
    SqlGeneration,
    DataFactoryProject,
    SavedQuery,
    QueryHistory,
    TableMetadata
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class VannaConfigSerializer(serializers.ModelSerializer):
    """Vanna AI配置序列化器"""
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = VannaConfig
        fields = '__all__'
        extra_kwargs = {
            'api_key': {'write_only': True},  # API密钥只在创建和更新时可见
        }


class SqlGenerationSerializer(serializers.ModelSerializer):
    """SQL生成记录序列化器"""
    config = VannaConfigSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = SqlGeneration
        fields = '__all__'


class DataFactoryProjectSerializer(serializers.ModelSerializer):
    """数据工厂项目序列化器"""
    owner = UserSerializer(read_only=True)
    members = UserSerializer(many=True, read_only=True)
    config = VannaConfigSerializer(read_only=True, allow_null=True)

    class Meta:
        model = DataFactoryProject
        fields = '__all__'


class SavedQuerySerializer(serializers.ModelSerializer):
    """保存的查询序列化器"""
    # 简化实现，让DRF自动处理ForeignKey字段
    # 对于ForeignKey，DRF会自动：
    # - 读取时返回关联对象的id
    # - 创建时接收关联对象的id
    # - 如果需要返回完整对象信息，可以在view中使用select_related
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = SavedQuery
        fields = '__all__'


class QueryHistorySerializer(serializers.ModelSerializer):
    """查询历史记录序列化器"""
    project = DataFactoryProjectSerializer(read_only=True)
    sql_generation = SqlGenerationSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = QueryHistory
        fields = '__all__'


class TableMetadataSerializer(serializers.ModelSerializer):
    """表元数据序列化器"""
    config = VannaConfigSerializer(read_only=True)
    database = serializers.ReadOnlyField(source='schema_name')
    schema = serializers.ReadOnlyField(source='schema_name')
    column_count = serializers.SerializerMethodField()

    def get_column_count(self, obj):
        """计算列数"""
        return len(obj.columns) if obj.columns else 0

    class Meta:
        model = TableMetadata
        fields = ['id', 'table_name', 'description', 'database', 'schema', 'column_count', 'columns', 'created_at', 'updated_at', 'config']
