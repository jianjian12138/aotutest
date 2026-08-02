from rest_framework import serializers
from apps.core_platform.masking import PIIMaskMixin
from django.contrib.auth import get_user_model
from .models import (
    VannaConfig,
    SqlGeneration,
    DataFactoryProject,
    SavedQuery,
    QueryHistory,
    TableMetadata,
    DataSource,
    DataPool
)

User = get_user_model()


class UserSerializer(PIIMaskMixin, serializers.ModelSerializer):
    """用户序列化器"""
    # 第六轮批次2：email 属 PII，非本人/非管理员输出掩码
    pii_masked_fields = ('email',)

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
            'db_password': {'write_only': True},  # 数据库密码独立加密存储
        }

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # db_connection 中不应残留明文密码，脱敏展示
        db_conn = ret.get('db_connection')
        if isinstance(db_conn, dict) and 'password' in db_conn:
            db_conn = dict(db_conn)
            db_conn['password'] = '********'
            ret['db_connection'] = db_conn
        # db_password 仅回显掩码
        if 'db_password' in ret and ret['db_password']:
            ret['db_password'] = '********'
        return ret

    def create(self, validated_data):
        return self._save_secret(validated_data)

    def update(self, instance, validated_data):
        return self._save_secret(validated_data, instance=instance)

    def _save_secret(self, validated_data, instance=None):
        """创建/更新时，将 db_connection 中的明文密码剥离到加密字段 db_password。"""
        db_conn = validated_data.get('db_connection')
        if isinstance(db_conn, dict) and db_conn.get('password'):
            validated_data['db_password'] = db_conn.pop('password')
        obj = instance or VannaConfig()
        for attr, value in validated_data.items():
            setattr(obj, attr, value)
        obj.save()
        return obj


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


class DataSourceSerializer(serializers.ModelSerializer):
    """数据源序列化器"""
    created_by = UserSerializer(read_only=True)
    project_detail = DataFactoryProjectSerializer(source='project', read_only=True)

    class Meta:
        model = DataSource
        fields = '__all__'
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # 掩码密码
        if 'password' in ret and ret['password']:
            ret['password'] = '********'
        return ret


class DataPoolSerializer(serializers.ModelSerializer):
    """数据池序列化器"""
    created_by = UserSerializer(read_only=True)
    project_detail = DataFactoryProjectSerializer(source='project', read_only=True)
    row_count = serializers.SerializerMethodField()

    class Meta:
        model = DataPool
        fields = '__all__'

    def get_row_count(self, obj):
        if hasattr(obj, 'data') and isinstance(obj.data, list):
            return len(obj.data)
        return 0
