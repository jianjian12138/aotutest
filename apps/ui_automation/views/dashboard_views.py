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




class UiDashboardViewSet(viewsets.ViewSet):
    """UI自动化仪表盘视图集"""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """获取仪表盘统计数据"""
        try:
            user = request.user
            accessible_projects = UiProject.objects.filter(models.Q(owner=
                user) | models.Q(members=user)).distinct()
            project_ids = accessible_projects.values_list('id', flat=True)
            project_count = accessible_projects.count()
            test_case_count = TestCase.objects.filter(project_id__in=
                project_ids).count()
            suite_count = TestSuite.objects.filter(project_id__in=project_ids
                ).count()
            execution_count = TestExecution.objects.filter(project_id__in=
                project_ids).count()
            test_case_execution_count = TestCaseExecution.objects.filter(
                project_id__in=project_ids).count()
            total_execution_count = execution_count + test_case_execution_count
            return Response({'project_count': project_count,
                'test_case_count': test_case_count, 'suite_count':
                suite_count, 'execution_count': total_execution_count})
        except Exception as e:
            import traceback
            print(f'Error in UiDashboardViewSet.stats: {str(e)}')
            traceback.print_exc()
            return Response({'project_count': 0, 'test_case_count': 0,
                'suite_count': 0, 'execution_count': 0}, status=200)
