from rest_framework import serializers
from .models import TestCaseModule, TestCase, TestCaseStep, TestCaseAttachment, TestCaseComment
from apps.core_platform.serializers.users import UserSerializer
from apps.core_platform.serializers.versions import VersionSimpleSerializer

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


class TestCaseModuleSerializer(serializers.ModelSerializer):
    """测试用例模块序列化器"""
    children = serializers.SerializerMethodField()
    test_case_count = serializers.SerializerMethodField()
    case_count = serializers.SerializerMethodField()

    class Meta:
        model = TestCaseModule
        fields = ['id', 'name', 'project', 'parent', 'order', 'children', 'test_case_count', 'case_count', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_children(self, obj):
        children = obj.children.all()
        return TestCaseModuleSerializer(children, many=True).data

    def get_test_case_count(self, obj):
        return obj.testcases.count()
        
    def get_case_count(self, obj):
        return obj.testcases.count()

class TestCaseSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    assignee = UserSerializer(read_only=True)
    project = ProjectSimpleSerializer(read_only=True)
    versions = VersionSimpleSerializer(many=True, read_only=True)
    step_details = TestCaseStepSerializer(many=True, read_only=True)
    attachments = TestCaseAttachmentSerializer(many=True, read_only=True)
    comments = TestCaseCommentSerializer(many=True, read_only=True)
    module_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = TestCase
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'module']

class TestCaseCreateSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(required=False, allow_null=True, help_text="项目ID，可选")
    module_id = serializers.IntegerField(required=False, allow_null=True, help_text="模块ID，可选")
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
            'priority', 'status', 'test_type', 'tags', 'project_id', 'version_ids', 'module_id'
        ]
    
    def create(self, validated_data):
        version_ids = validated_data.pop('version_ids', [])
        # project_id会在视图的perform_create中处理
        validated_data.pop('project_id', None)
        
        module_id = validated_data.pop('module_id', None)
        if module_id:
            try:
                validated_data['module'] = TestCaseModule.objects.get(id=module_id)
            except TestCaseModule.DoesNotExist:
                pass
        
        testcase = super().create(validated_data)
        
        # 设置版本关联
        if version_ids:
            testcase.versions.set(version_ids)
        
        return testcase

class TestCaseUpdateSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(required=False, allow_null=True, help_text="项目ID，可选")
    module_id = serializers.IntegerField(required=False, allow_null=True, help_text="模块ID，可选")
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
            'priority', 'status', 'test_type', 'tags', 'project_id', 'version_ids', 'module_id'
        ]
    
    def update(self, instance, validated_data):
        version_ids = validated_data.pop('version_ids', None)
        # project_id会在视图中处理
        validated_data.pop('project_id', None)
        
        module_id = validated_data.pop('module_id', None)
        if module_id is not None:
            if module_id:
                try:
                    validated_data['module'] = TestCaseModule.objects.get(id=module_id)
                except TestCaseModule.DoesNotExist:
                    pass
            else:
                validated_data['module'] = None
        
        instance = super().update(instance, validated_data)
        
        # 更新版本关联
        if version_ids is not None:
            instance.versions.set(version_ids)
        
        return instance