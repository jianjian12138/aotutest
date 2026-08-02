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




class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 1000


class UiProjectViewSet(BaseProjectViewSet):
    queryset = UiProject.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.
        OrderingFilter]
    filterset_fields = ['status', 'owner', 'members']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return UiProjectCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UiProjectUpdateSerializer
        return UiProjectSerializer

    def perform_destroy(self, instance):
        log_operation('delete', 'project', instance.id, instance.name, self
            .request.user)
        instance.delete()
