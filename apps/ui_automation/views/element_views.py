from apps.core_platform.views.base import BaseProjectViewSet
from apps.core_platform.permissions import TenantAwareViewSetMixin
from apps.notifications.models import NotificationConfig, NotificationLog
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db import models
from django.utils import timezone
from django.conf import settings
import os
import logging
import json
import re
import random
import time
from ..models import UiProject, LocatorStrategy, Element, TestScript, TestSuite, TestSuiteScript, TestExecution, Screenshot, ElementGroup, PageObject, PageObjectElement, ScriptStep, ScriptElementUsage, TestCase, TestCaseStep, TestCaseExecution, OperationRecord, UiTestCaseModule, UiScheduledTask, UiTaskNotificationSetting, AICase, AIExecutionRecord, UiDevice, ExecutionNode
from ..serializers import UiProjectSerializer, UiProjectCreateSerializer, UiProjectUpdateSerializer, LocatorStrategySerializer, ElementSerializer, ElementEnhancedSerializer, TestScriptSerializer, TestScriptCreateSerializer, TestScriptUpdateSerializer, TestSuiteSerializer, TestSuiteCreateSerializer, TestSuiteUpdateSerializer, TestSuiteWithScriptsSerializer, TestSuiteScriptSerializer, TestSuiteTestCaseSerializer, TestExecutionSerializer, TestExecutionCreateSerializer, ScreenshotSerializer, ElementGroupSerializer, ElementGroupCreateSerializer, PageObjectSerializer, PageObjectCreateSerializer, PageObjectElementSerializer, ScriptStepSerializer, ScriptElementUsageSerializer, ScriptAnalysisSerializer, ElementValidationSerializer, CodeGenerationSerializer, TestCaseSerializer, TestCaseStepSerializer, TestCaseExecutionSerializer, TestCaseRunSerializer, OperationRecordSerializer, UiTestCaseModuleSerializer, UiScheduledTaskSerializer, NotificationConfigSerializer, NotificationLogSerializer, UiTaskNotificationSettingSerializer, AICaseSerializer, AIExecutionRecordSerializer, UiDeviceSerializer, ExecutionNodeSerializer
from ..operation_logger import log_operation
from ..services.case_generator import CaseGenerator
logger = logging.getLogger(__name__)
User = get_user_model()


def extract_step_info(s, step_index):
    """提取步骤信息的辅助函数，确保返回可读的步骤描述"""
    step_info = {'step': step_index}
    if hasattr(s, 'action'):
        action_data = s.action
        if isinstance(action_data, str):
            step_info['action'] = action_data
        elif hasattr(action_data, '__dict__'):
            attrs = {}
            for key in ['type', 'description', 'goal', 'coordinate', 'text',
                'output', 'result']:
                if hasattr(action_data, key):
                    value = getattr(action_data, key)
                    if isinstance(value, str):
                        attrs[key] = value
                    elif callable(value):
                        attrs[key] = getattr(value, '__name__', str(value))
                    else:
                        attrs[key] = str(value)
            if attrs:
                step_info['action'] = attrs
        else:
            step_info['action'] = str(action_data)
    elif hasattr(s, 'model_output'):
        output_data = s.model_output
        if isinstance(output_data, str):
            step_info['action'] = output_data
        elif hasattr(output_data, '__dict__'):
            attrs = {'type': 'model_output'}
            for key in ['action', 'description', 'goal', 'coordinate', 'text']:
                if hasattr(output_data, key):
                    value = getattr(output_data, key)
                    attrs[key] = str(value) if value else None
            step_info['action'] = attrs
        else:
            step_info['action'] = str(output_data)
    elif hasattr(s, '__dict__'):
        attrs = {}
        for key in dir(s):
            if not key.startswith('_'):
                try:
                    value = getattr(s, key)
                    if not callable(value):
                        attrs[key] = str(value)
                except Exception:
                    pass
        if attrs:
            step_info['action'] = attrs
    elif callable(s):
        step_info['action'
            ] = f"<Action: {getattr(s, '__name__', 'unknown action')}>"
    else:
        step_info['action'] = str(s)
    return step_info


from rest_framework.pagination import PageNumberPagination




class LocatorStrategyViewSet(BaseProjectViewSet):
    queryset = LocatorStrategy.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = LocatorStrategySerializer
    ordering = ['id']


class ElementViewSet(BaseProjectViewSet):
    queryset = Element.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['project', 'locator_strategy', 'element_type',
        'validation_status', 'group']
    search_fields = ['name', 'description', 'page', 'component_name']

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return ElementEnhancedSerializer
        return ElementSerializer

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        page_name = self.request.query_params.get('page_name', None)
        if page_name:
            queryset = queryset.filter(page=page_name)
        return queryset

    def perform_destroy(self, instance):
        log_operation('delete', 'element', instance.id, instance.name, self
            .request.user)
        instance.delete()

    @action(detail=True, methods=['post'])
    def validate_locator(self, request, pk=None):
        """验证元素定位器有效性"""
        element = self.get_object()
        validation_result = self._perform_element_validation(element)
        element.validation_status = 'VALID' if validation_result['is_valid'
            ] else 'INVALID'
        element.validation_message = validation_result['validation_message']
        element.last_validated = timezone.now()
        element.save()
        serializer = ElementValidationSerializer(validation_result)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def usages(self, request, pk=None):
        """获取元素在脚本中的使用情况"""
        element = self.get_object()
        usages = ScriptElementUsage.objects.filter(element=element
            ).select_related('script')
        serializer = ScriptElementUsageSerializer(usages, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """获取元素树形结构"""
        project_id = request.query_params.get('project')
        if not project_id:
            return Response({'error': '需要指定项目ID'}, status=status.
                HTTP_400_BAD_REQUEST)
        elements = self.get_queryset().filter(project_id=project_id)
        tree_data = self._build_element_tree(elements)
        return Response(tree_data)

    @action(detail=True, methods=['post'])
    def add_backup_locator(self, request, pk=None):
        """添加备用定位器"""
        element = self.get_object()
        strategy = request.data.get('strategy')
        value = request.data.get('value')
        if not strategy or not value:
            return Response({'error': '策略和值都是必需的'}, status=status.
                HTTP_400_BAD_REQUEST)
        backup_locators = element.backup_locators or []
        backup_locators.append({'strategy': strategy, 'value': value})
        element.backup_locators = backup_locators
        element.save()
        return Response({'message': '备用定位器添加成功'})

    @action(detail=True, methods=['post'])
    def generate_suggestions(self, request, pk=None):
        """生成元素使用建议"""
        element = self.get_object()
        suggestions = self._generate_element_suggestions(element)
        return Response({'suggestions': suggestions})

    @action(detail=True, methods=['post'], url_path='ai-heal')
    def ai_heal(self, request, pk=None):
        """调用大语言模型生成高可用替换策略 (Smart Self-Healing)"""
        try:
            from apps.assistant.healing_service import SelfHealingService
            result = SelfHealingService.suggest_locators(pk)
            if result.get('status') == 'SUCCESS':
                return Response(result, status=status.HTTP_200_OK)
            else:
                return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f'AI 节点自愈引擎错误: {str(e)}')
            return Response({'status': 'FAILED', 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _perform_element_validation(self, element):
        """执行元素验证（模拟实现）"""
        try:
            is_valid = True
            message = '定位器验证通过'
            suggestions = []
            if element.locator_strategy.name == 'css':
                if not element.locator_value.strip():
                    is_valid = False
                    message = 'CSS选择器不能为空'
            elif element.locator_strategy.name == 'xpath':
                if not element.locator_value.strip():
                    is_valid = False
                    message = 'XPath表达式不能为空'
            return {'is_valid': is_valid, 'validation_message': message,
                'suggestions': suggestions}
        except Exception as e:
            return {'is_valid': False, 'validation_message':
                f'验证过程中出现错误: {str(e)}', 'suggestions': []}

    def _build_element_tree(self, elements):
        """构建元素树形结构 - 返回元素列表而不是页面分组，因为前端会自己处理页面关联"""
        element_data_list = []
        for element in elements:
            element_data = {'id': element.id, 'name': element.name, 'type':
                'element', 'element_type': element.element_type,
                'locator_strategy': element.locator_strategy.name if
                element.locator_strategy else None, 'locator_value':
                element.locator_value, 'validation_status': element.
                validation_status, 'usage_count': element.usage_count,
                'group_id': element.group_id, 'page': element.page,
                'children': []}
            element_data_list.append(element_data)
        return element_data_list

    def _generate_element_suggestions(self, element):
        """生成元素使用建议"""
        suggestions = []
        if element.element_type == 'INPUT':
            suggestions.append('建议为输入框元素添加清空和输入验证操作')
        elif element.element_type == 'BUTTON':
            suggestions.append('建议验证按钮点击后的页面跳转或状态变化')
        elif element.element_type == 'DROPDOWN':
            suggestions.append('建议测试下拉框的所有选项')
        if element.usage_count == 0:
            suggestions.append('此元素尚未在任何脚本中使用，考虑是否需要删除')
        elif element.usage_count > 10:
            suggestions.append('此元素使用频率较高，建议添加到页面对象中以提高复用性')
        return suggestions


class ElementGroupViewSet(TenantAwareViewSetMixin, BaseProjectViewSet):
    queryset = ElementGroup.objects.all()
    # UiProject 无 organization 字段，租户锚点为项目负责人 owner
    org_field = 'project__owner'
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['project', 'parent_group']
    search_fields = ['name', 'description']

    def get_serializer_class(self):
        if self.action == 'create':
            return ElementGroupCreateSerializer
        return ElementGroupSerializer

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """获取分组树形结构"""
        project_id = request.query_params.get('project')
        if not project_id:
            return Response({'error': '需要指定项目ID'}, status=status.
                HTTP_400_BAD_REQUEST)
        # 先按租户校验项目归属，后续一律通过已校验的 project 走关系访问，杜绝跨租户读写
        try:
            project = self.scoped_get(UiProject, org_field='owner', id=
                project_id)
        except UiProject.DoesNotExist:
            return Response({'error': '项目不存在或无权访问'}, status=status.
                HTTP_404_NOT_FOUND)
        try:
            page_objects = project.page_objects.all()
            for po in page_objects:
                group, _ = project.element_groups.get_or_create(name=po.
                    name, defaults={'description': po.description or
                    f'Auto-generated for {po.name}'})
                project.elements.filter(page=po.name, group__isnull=True
                    ).update(group=group)
            pages = project.elements.filter(page__isnull=False).exclude(page=''
                ).values_list('page', flat=True).distinct()
            for page_name in pages:
                group, _ = project.element_groups.get_or_create(name=
                    page_name, defaults={'description':
                    f'Auto-generated group for {page_name}'})
                project.elements.filter(page=page_name, group__isnull=True
                    ).update(group=group)
        except Exception as e:
            logger.warning(f'自动同步分组失败: {e}')
        groups = self.get_queryset().filter(project_id=project_id,
            parent_group__isnull=True)
        serializer = ElementGroupSerializer(groups, many=True)
        return Response(serializer.data)


class PageObjectViewSet(BaseProjectViewSet):
    queryset = PageObject.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['project']
    search_fields = ['name', 'class_name', 'description']

    def get_serializer_class(self):
        if self.action == 'create':
            return PageObjectCreateSerializer
        return PageObjectSerializer

    @action(detail=True, methods=['post'])
    def generate_code(self, request, pk=None):
        """生成页面对象代码"""
        page_object = self.get_object()
        serializer = CodeGenerationSerializer(data=request.data)
        if serializer.is_valid():
            language = serializer.validated_data['language']
            framework = serializer.validated_data['framework']
            serializer.validated_data['include_comments']
            try:
                generated_code = page_object.generate_code(language)
                page_object.template_code = generated_code
                page_object.save()
                return Response({'code': generated_code, 'language':
                    language, 'framework': framework})
            except Exception as e:
                return Response({'error': f'代码生成失败: {str(e)}'}, status=
                    status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def add_element(self, request, pk=None):
        """向页面对象添加元素"""
        page_object = self.get_object()
        serializer = PageObjectElementSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(page_object=page_object)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def elements(self, request, pk=None):
        """获取页面对象的所有元素"""
        page_object = self.get_object()
        po_elements = page_object.page_object_elements.select_related('element'
            ).all()
        serializer = PageObjectElementSerializer(po_elements, many=True)
        return Response(serializer.data)


class PageObjectElementViewSet(BaseProjectViewSet):
    queryset = PageObjectElement.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = PageObjectElementSerializer
