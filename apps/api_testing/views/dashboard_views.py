from apps.core_platform.views.base import BaseProjectViewSet
from apps.notifications.models import NotificationConfig, NotificationLog
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db import models
from django.utils import timezone
from django.http import HttpResponse, FileResponse, Http404, HttpResponseNotFound
from django.views.static import serve
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import requests
import time
import os
import json
import logging
import uuid
import subprocess
from datetime import datetime, timedelta
from ..models import ApiProject, ApiCollection, ApiRequest, Environment, RequestHistory, TestSuite, TestExecution, TestSuiteRequest, ScheduledTask, TaskExecutionLog, TaskNotificationSetting, OperationLog, ApiImportTask, ApiTestCaseModule, ApiTestCase, ApiTestCaseStep, ApiTestCaseExecution, TestSuiteTestCase, ApiProject
from apps.core_platform.models import GlobalParameter
from ..import_utils import parse_openapi_spec
from ..serializers import ApiProjectSerializer, ApiCollectionSerializer, ApiRequestSerializer, ApiTestCaseModuleSerializer, ApiTestCaseSerializer, ApiTestCaseStepSerializer, ApiTestCaseExecutionSerializer, TestSuiteTestCaseSerializer, EnvironmentSerializer, RequestHistorySerializer, TestSuiteSerializer, TestSuiteRequestSerializer, TestExecutionSerializer, UserSerializer, ScheduledTaskSerializer, TaskExecutionLogSerializer, NotificationConfigSerializer, NotificationLogSerializer, TaskNotificationSettingSerializer, NotificationConfigDetailSerializer, NotificationLogDetailSerializer, TaskNotificationSettingDetailSerializer, OperationLogSerializer
logger = logging.getLogger(__name__)
from ..utils import execute_assertions, execute_test_case
from ..operation_logger import log_operation
User = get_user_model()
from rest_framework.pagination import PageNumberPagination
from .project_views import StandardPagination

class ApiDashboardViewSet(viewsets.ViewSet):
    """API测试仪表盘视图集"""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """获取仪表盘统计数据"""
        try:
            user = request.user
            accessible_projects = ApiProject.objects.filter(models.Q(owner=
                user) | models.Q(members=user)).distinct()
            project_ids = accessible_projects.values_list('id', flat=True)
            project_count = accessible_projects.count()
            interface_count = ApiRequest.objects.filter(
                collection__project_id__in=project_ids).count()
            suite_count = TestSuite.objects.filter(project_id__in=project_ids
                ).count()
            request_history_count = RequestHistory.objects.filter(
                request__collection__project_id__in=project_ids).count()
            case_execution_count = ApiTestCaseExecution.objects.filter(
                test_case__project_id__in=project_ids).count()
            history_count = request_history_count + case_execution_count
            return Response({'project_count': project_count,
                'interface_count': interface_count, 'suite_count':
                suite_count, 'history_count': history_count})
        except Exception as e:
            import traceback
            print(f'Error in ApiDashboardViewSet.stats: {str(e)}')
            traceback.print_exc()
            return Response({'project_count': 0, 'interface_count': 0,
                'suite_count': 0, 'history_count': 0}, status=200)


