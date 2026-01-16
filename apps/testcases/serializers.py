from rest_framework import serializers
from .models import TestCase, TestCaseStep, TestCaseAttachment, TestCaseComment
from apps.users.serializers import UserSerializer
from apps.versions.serializers import VersionSimpleSerializer

class TestCaseStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCaseStep
        fields = '__all__'

class TestCaseAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = UserSerializer(read_only=True)
    
    class Meta:
        model = TestCaseAttachment
        fields = '__all__'

class TestCaseCommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    
    class Meta:
        model = TestCaseComment
        fields = '__all__'

class ProjectSimpleSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()

class TestCaseSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    assignee = UserSerializer(read_only=True)
    project = ProjectSimpleSerializer(read_only=True)
    versions = VersionSimpleSerializer(many=True, read_only=True)
    step_details = TestCaseStepSerializer(many=True, read_only=True)
    attachments = TestCaseAttachmentSerializer(many=True, read_only=True)
    comments = TestCaseCommentSerializer(many=True, read_only=True)
    
    class Meta:
        model = TestCase
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

class TestCaseCreateSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(required=False, allow_null=True, help_text="项目ID，可选")
    version_ids = serializers.ListField(
        child=serializers.IntegerField(), 
        required=False, 
        allow_empty=True,
        help_text="关联版本ID列表"
    )
    
    class Meta:
        model = TestCase
        fields = [
            'title', 'description', 'preconditions', 'steps', 'expected_result', 
            'priority', 'status', 'test_type', 'tags', 'project_id', 'version_ids'
        ]
    
    def create(self, validated_data):
        version_ids = validated_data.pop('version_ids', [])
        # project_id会在视图的perform_create中处理
        validated_data.pop('project_id', None)
        
        testcase = super().create(validated_data)
        
        # 设置版本关联
        if version_ids:
            testcase.versions.set(version_ids)
        
        return testcase

class TestCaseUpdateSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(required=False, allow_null=True, help_text="项目ID，可选")
    version_ids = serializers.ListField(
        child=serializers.IntegerField(), 
        required=False, 
        allow_empty=True,
        help_text="关联版本ID列表"
    )
    
    class Meta:
        model = TestCase
        fields = [
            'title', 'description', 'preconditions', 'steps', 'expected_result', 
            'priority', 'status', 'test_type', 'tags', 'project_id', 'version_ids'
        ]
    
    def update(self, instance, validated_data):
        version_ids = validated_data.pop('version_ids', None)
        # project_id会在视图中处理
        validated_data.pop('project_id', None)
        
        instance = super().update(instance, validated_data)
        
        # 更新版本关联
        if version_ids is not None:
            instance.versions.set(version_ids)
        
        return instance