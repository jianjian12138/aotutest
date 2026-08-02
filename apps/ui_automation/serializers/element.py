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

class LocatorStrategySerializer(serializers.ModelSerializer):
    class Meta:
        model = LocatorStrategy
        fields = '__all__'


class ElementSerializer(serializers.ModelSerializer):
    project = UiProjectSerializer(read_only=True)
    locator_strategy = LocatorStrategySerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    project_id = serializers.IntegerField()
    group_id = serializers.IntegerField(required=False, allow_null=True)
    locator_strategy_id = serializers.IntegerField()  # 显式定义，支持读写

    class Meta:
        model = Element
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'created_by')

    def validate_project_id(self, value):
        """验证项目ID是否有效"""
        try:
            UiProject.objects.get(id=value)
        except UiProject.DoesNotExist:
            raise serializers.ValidationError("请选择有效的项目")
        return value

    def validate_locator_strategy_id(self, value):
        """验证定位策略ID是否有效"""
        if value is not None:
            try:
                LocatorStrategy.objects.get(id=value)
            except LocatorStrategy.DoesNotExist:
                raise serializers.ValidationError("请选择有效的定位策略")
        return value

    def validate_group_id(self, value):
        """验证分组ID是否有效"""
        if value is not None:  # 允许None值
            try:
                ElementGroup.objects.get(id=value)
            except ElementGroup.DoesNotExist:
                raise serializers.ValidationError("请选择有效的元素分组")
        return value

    def create(self, validated_data):
        # 处理外键字段
        project_id = validated_data.pop('project_id')
        locator_strategy_id = validated_data.pop('locator_strategy_id', None)
        group_id = validated_data.pop('group_id', None)

        validated_data['project'] = UiProject.objects.get(id=project_id)

        if locator_strategy_id:
            validated_data['locator_strategy'] = LocatorStrategy.objects.get(id=locator_strategy_id)

        if group_id:
            validated_data['group'] = ElementGroup.objects.get(id=group_id)

        return super().create(validated_data)

    def update(self, instance, validated_data):
        # 处理外键字段
        project_id = validated_data.pop('project_id', None)
        locator_strategy_id = validated_data.pop('locator_strategy_id', None)
        group_id = validated_data.pop('group_id', None)

        if project_id:
            validated_data['project'] = UiProject.objects.get(id=project_id)

        if locator_strategy_id:
            validated_data['locator_strategy'] = LocatorStrategy.objects.get(id=locator_strategy_id)

        if group_id is not None:  # 允许设置为None来清除分组
            if group_id:
                validated_data['group'] = ElementGroup.objects.get(id=group_id)
            else:
                validated_data['group'] = None

        return super().update(instance, validated_data)


class ElementGroupSerializer(serializers.ModelSerializer):
    project = UiProjectSerializer(read_only=True)
    project_id = serializers.IntegerField(write_only=True)
    elements_count = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()

    class Meta:
        model = ElementGroup
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def get_elements_count(self, obj):
        """获取分组下的元素数量"""
        return obj.elements.count()

    def get_children(self, obj):
        """获取子分组"""
        children = obj.elementgroup_set.all()
        return ElementGroupSerializer(children, many=True, context=self.context).data


class ElementGroupCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElementGroup
        fields = ('project', 'name', 'description', 'parent_group', 'order')


class ElementEnhancedSerializer(serializers.ModelSerializer):
    """增强的元素序列化器，包含新字段"""
    project = UiProjectSerializer(read_only=True)
    group = ElementGroupSerializer(read_only=True)
    locator_strategy = LocatorStrategySerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    parent_element = serializers.SerializerMethodField()
    children_elements = serializers.SerializerMethodField()
    all_locators = serializers.SerializerMethodField()
    usage_scripts = serializers.SerializerMethodField()

    # Write-only fields for foreign keys
    project_id = serializers.IntegerField()
    group_id = serializers.IntegerField(required=False, allow_null=True)
    locator_strategy_id = serializers.IntegerField()  # 允许读写,支持回显
    parent_element_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Element
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'created_by', 'usage_count', 'last_validated')

    def get_parent_element(self, obj):
        """获取父元素信息"""
        if obj.parent_element:
            return {
                'id': obj.parent_element.id,
                'name': obj.parent_element.name,
                'page': obj.parent_element.page
            }
        return None

    def get_children_elements(self, obj):
        """获取子元素"""
        children = obj.element_set.all()
        return [{
            'id': child.id,
            'name': child.name,
            'element_type': child.element_type
        } for child in children]

    def get_all_locators(self, obj):
        """获取所有定位器（主要+备用）"""
        return obj.get_all_locators()

    def get_usage_scripts(self, obj):
        """获取使用此元素的脚本列表"""
        usages = obj.script_usages.select_related('script').all()[:5]  # 只返回前5个
        return [{
            'script_id': usage.script.id,
            'script_name': usage.script.name,
            'usage_type': usage.usage_type,
            'frequency': usage.frequency
        } for usage in usages]

    def create(self, validated_data):
        # 处理外键字段
        project_id = validated_data.pop('project_id')
        locator_strategy_id = validated_data.pop('locator_strategy_id')
        group_id = validated_data.pop('group_id', None)
        parent_element_id = validated_data.pop('parent_element_id', None)

        validated_data['project'] = UiProject.objects.get(id=project_id)
        validated_data['locator_strategy'] = LocatorStrategy.objects.get(id=locator_strategy_id)

        if group_id:
            validated_data['group'] = ElementGroup.objects.get(id=group_id)

        if parent_element_id:
            validated_data['parent_element'] = Element.objects.get(id=parent_element_id)

        return super().create(validated_data)

    def update(self, instance, validated_data):
        # 处理外键字段
        project_id = validated_data.pop('project_id', None)
        locator_strategy_id = validated_data.pop('locator_strategy_id', None)
        group_id = validated_data.pop('group_id', None)
        parent_element_id = validated_data.pop('parent_element_id', None)

        if project_id:
            validated_data['project'] = UiProject.objects.get(id=project_id)

        if locator_strategy_id:
            validated_data['locator_strategy'] = LocatorStrategy.objects.get(id=locator_strategy_id)

        if group_id is not None:  # 允许设置为None来清除分组
            if group_id:
                validated_data['group'] = ElementGroup.objects.get(id=group_id)
            else:
                validated_data['group'] = None

        if parent_element_id is not None:  # 允许设置为None来清除父元素
            if parent_element_id:
                validated_data['parent_element'] = Element.objects.get(id=parent_element_id)
            else:
                validated_data['parent_element'] = None

        return super().update(instance, validated_data)


class PageObjectSerializer(serializers.ModelSerializer):
    project = UiProjectSerializer(read_only=True)
    created_by = UserSerializer(read_only=True)
    elements_count = serializers.SerializerMethodField()
    elements = serializers.SerializerMethodField()
    project_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = PageObject
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'created_by', 'template_code')

    def get_elements_count(self, obj):
        """获取页面对象包含的元素数量"""
        return obj.page_object_elements.count()

    def get_elements(self, obj):
        """获取页面对象包含的元素"""
        po_elements = obj.page_object_elements.select_related('element').all()
        return [{
            'id': po_element.id,
            'element_id': po_element.element.id,
            'element_name': po_element.element.name,
            'method_name': po_element.method_name,
            'is_property': po_element.is_property,
            'order': po_element.order
        } for po_element in po_elements]


class PageObjectCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PageObject
        fields = ('project', 'name', 'class_name', 'url_pattern', 'description')

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class PageObjectElementSerializer(serializers.ModelSerializer):
    page_object = PageObjectSerializer(read_only=True)
    element = ElementEnhancedSerializer(read_only=True)
    page_object_id = serializers.IntegerField(write_only=True)
    element_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = PageObjectElement
        fields = '__all__'
        read_only_fields = ('created_at',)

    def validate_method_name(self, value):
        """验证方法名称是否符合命名规范"""
        import re
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', value):
            raise serializers.ValidationError("方法名称只能包含字母、数字和下划线，且不能以数字开头")
        return value


