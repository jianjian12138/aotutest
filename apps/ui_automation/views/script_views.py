from apps.core_platform.views.base import BaseProjectViewSet
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
                except:
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




class ScriptStepViewSet(BaseProjectViewSet):
    queryset = ScriptStep.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = ScriptStepSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['script', 'action_type', 'target_element',
        'page_object']

    @action(detail=False, methods=['post'])
    def batch_create(self, request):
        """批量创建脚本步骤"""
        steps_data = request.data.get('steps', [])
        created_steps = []
        for step_data in steps_data:
            serializer = ScriptStepSerializer(data=step_data)
            if serializer.is_valid():
                step = serializer.save()
                created_steps.append(step)
            else:
                return Response({'error': f'步骤创建失败: {serializer.errors}'},
                    status=status.HTTP_400_BAD_REQUEST)
        response_serializer = ScriptStepSerializer(created_steps, many=True)
        return Response(response_serializer.data, status=status.
            HTTP_201_CREATED)


class ScriptElementUsageViewSet(BaseProjectViewSet):
    queryset = ScriptElementUsage.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = ScriptElementUsageSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['script', 'element', 'usage_type']

    @action(detail=False, methods=['post'])
    def analyze_script(self, request):
        """分析脚本中的元素使用情况"""
        script_id = request.data.get('script_id')
        if not script_id:
            return Response({'error': '需要指定脚本ID'}, status=status.
                HTTP_400_BAD_REQUEST)
        try:
            script = TestScript.objects.get(id=script_id)
            analysis_result = self._analyze_script_elements(script)
            serializer = ScriptAnalysisSerializer(analysis_result)
            return Response(serializer.data)
        except TestScript.DoesNotExist:
            return Response({'error': '脚本不存在'}, status=status.
                HTTP_404_NOT_FOUND)

    def _analyze_script_elements(self, script):
        """分析脚本中的元素使用"""
        content = script.content
        usages = []
        missing_elements = []
        recommendations = []
        if script.script_type == 'CODE':
            locator_patterns = ['locator\\(["\\\']([^"\\\']+)["\\\']\\)',
                'findElement\\(["\\\']([^"\\\']+)["\\\']\\)',
                'css\\(["\\\']([^"\\\']+)["\\\']\\)',
                'xpath\\(["\\\']([^"\\\']+)["\\\']\\)']
            for pattern in locator_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    try:
                        element = Element.objects.get(project=script.
                            project, locator_value=match)
                        usage, created = (ScriptElementUsage.objects.
                            get_or_create(script=script, element=element,
                            defaults={'usage_type': 'CLICK', 'line_number':
                            1, 'frequency': 1}))
                        if not created:
                            usage.frequency += 1
                            usage.save()
                        element.increment_usage_count()
                        usages.append(usage)
                    except Element.DoesNotExist:
                        missing_elements.append(match)
        if missing_elements:
            recommendations.append(f'发现 {len(missing_elements)} 个未定义的元素定位器')
        if len(usages) > 20:
            recommendations.append('脚本复杂度较高，建议拆分为多个小脚本')
        complexity_score = min(100, len(usages) * 5)
        return {'element_usages': usages, 'missing_elements':
            missing_elements, 'recommendations': recommendations,
            'complexity_score': complexity_score}


class TestScriptViewSet(BaseProjectViewSet):
    queryset = TestScript.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['project', 'script_type']
    search_fields = ['name', 'description']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return TestScriptCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TestScriptUpdateSerializer
        return TestScriptSerializer

    @action(detail=False, methods=['post'])
    def format_code(self, request):
        """格式化代码"""
        code = request.data.get('code', '')
        language = request.data.get('language', 'python')
        if not code:
            return Response({'error': '代码不能为空'}, status=status.
                HTTP_400_BAD_REQUEST)
        if language == 'python':
            try:
                import black
                formatted_code = black.format_str(code, mode=black.Mode())
                return Response({'code': formatted_code})
            except ImportError:
                return Response({'error': '服务器未安装black格式化工具'}, status=
                    status.HTTP_501_NOT_IMPLEMENTED)
            except Exception as e:
                return Response({'error': f'格式化失败: {str(e)}'}, status=
                    status.HTTP_400_BAD_REQUEST)
        return Response({'code': code})
