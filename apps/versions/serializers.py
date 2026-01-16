from rest_framework import serializers
from .models import Version
from apps.users.serializers import UserSerializer
from apps.projects.serializers import ProjectSimpleSerializer

class VersionSerializer(serializers.ModelSerializer):
    """版本序列化器"""
    created_by = UserSerializer(read_only=True)
    projects = ProjectSimpleSerializer(many=True, read_only=True)
    testcases_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Version
        fields = ['id', 'name', 'description', 'is_baseline', 'projects', 'created_by', 'created_at', 'testcases_count']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_testcases_count(self, obj):
        return obj.testcases.count()

class VersionCreateSerializer(serializers.ModelSerializer):
    """版本创建序列化器"""
    project_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True)
    
    class Meta:
        model = Version
        fields = ['name', 'description', 'is_baseline', 'project_ids']
    
    def validate_project_ids(self, value):
        from apps.projects.models import Project
        if not value:
            raise serializers.ValidationError("至少需要关联一个项目")
        
        # 检查所有项目是否存在
        existing_projects = Project.objects.filter(id__in=value)
        if existing_projects.count() != len(value):
            raise serializers.ValidationError("部分项目不存在")
        
        return value

    def create(self, validated_data):
        project_ids = validated_data.pop('project_ids')
        version = super().create(validated_data)
        version.projects.set(project_ids)
        return version

    def update(self, instance, validated_data):
        project_ids = validated_data.pop('project_ids', None)
        instance = super().update(instance, validated_data)
        if project_ids is not None:
            instance.projects.set(project_ids)
        return instance

class VersionSimpleSerializer(serializers.ModelSerializer):
    """版本简单序列化器，用于在测试用例中显示"""
    class Meta:
        model = Version
        fields = ['id', 'name', 'is_baseline']
