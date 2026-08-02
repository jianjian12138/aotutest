from apps.core_platform.views.base import BaseProjectViewSet
from apps.core_platform.permissions import scoped_queryset_for, TenantAwareViewSetMixin
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
from ..models import ApiProject, ApiCollection, ApiRequest, Environment, RequestHistory, TestSuite, TestExecution, TestSuiteRequest, ScheduledTask, TaskExecutionLog, TaskNotificationSetting, OperationLog, ApiImportTask, ApiTestCaseModule, ApiTestCase, ApiTestCaseStep, ApiTestCaseExecution, TestSuiteTestCase
from apps.core_platform.models import GlobalParameter
from ..import_utils import parse_openapi_spec
from ..serializers import ApiProjectSerializer, ApiCollectionSerializer, ApiRequestSerializer, ApiTestCaseModuleSerializer, ApiTestCaseSerializer, ApiTestCaseStepSerializer, ApiTestCaseExecutionSerializer, TestSuiteTestCaseSerializer, EnvironmentSerializer, RequestHistorySerializer, TestSuiteSerializer, TestSuiteRequestSerializer, TestExecutionSerializer, UserSerializer, ScheduledTaskSerializer, TaskExecutionLogSerializer, NotificationConfigSerializer, NotificationLogSerializer, TaskNotificationSettingSerializer, NotificationConfigDetailSerializer, NotificationLogDetailSerializer, TaskNotificationSettingDetailSerializer, OperationLogSerializer
logger = logging.getLogger(__name__)
from ..utils import execute_assertions, execute_test_case
from ..operation_logger import log_operation
User = get_user_model()
from rest_framework.pagination import PageNumberPagination
from .project_views import StandardPagination

class ApiTestCaseModuleViewSet(BaseProjectViewSet):
    """API测试用例模块视图集

    第六轮批次2：核查该历史遗留形式挂靠 —— 自定义 get_queryset 首行即
    super().get_queryset()，基类 BaseProjectViewSet 的项目归属校验实际已生效，
    未发现跨租户越权；本次改为显式声明自管 + 收口 _apply_tenant_scope。
    """
    tenant_scope_self_managed = True
    tenant_scope_self_managed_reason = (
        'get_queryset 以 super().get_queryset() 起步，完整继承 BaseProjectViewSet 的归属边界：'
        '携带 project_id 时校验该项目的 owner/members（传他人 project_id 返回空集），'
        '未携带时因 ApiTestCaseModule 无 created_by 字段而直接 none()，两路均 fail-closed；'
        '其后仅追加 parent__isnull 层级筛选，不放宽任何可见性。'
        '模型有 project 外键但 ApiProject 无 organization 字段，自动解析会命中 '
        'project__organization 导致 FieldError，故声明自管'
    )
    queryset = ApiTestCaseModule.objects.all()
    serializer_class = ApiTestCaseModuleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['order', 'created_at']
    ordering = ['order', 'created_at']
    filterset_fields = ['project', 'parent']

    def get_queryset(self):
        queryset = super().get_queryset()
        # 默认只返回顶级模块（如果没有显式请求特定父模块）
        parent_id = self.request.query_params.get('parent')
        get_all = self.request.query_params.get('get_all')
        if parent_id is None and not get_all:
            return self._apply_tenant_scope(queryset.filter(parent__isnull=True))
        return self._apply_tenant_scope(queryset)

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """获取模块树形结构，支持通过project过滤"""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def batch_update_order(self, request):
        """批量更新模块排序（租户安全整改：仅允许操作归属当前用户可见项目的模块）"""
        user = request.user
        items = request.data.get('items', [])
        if not items:
            return Response({'error': '未提供排序数据'}, status=status.HTTP_400_BAD_REQUEST)

        updated_modules = []
        is_privileged = user.is_staff or user.is_superuser
        for index, item_id in enumerate(items):
            module = ApiTestCaseModule.objects.filter(id=item_id).first()
            if module is None:
                continue
            proj = module.project
            is_owner = proj.owner_id == (user.id if user else None)
            is_member = user.is_authenticated and proj.members.filter(id=user.id).exists()
            if not (is_privileged or is_owner or is_member):
                continue
            module.order = index
            module.save()
            updated_modules.append(module)

        serializer = self.get_serializer(updated_modules, many=True)
        return Response(serializer.data)


class ApiTestCaseViewSet(BaseProjectViewSet):
    queryset = ApiTestCase.objects.all()
    serializer_class = ApiTestCaseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.
        OrderingFilter]
    filterset_fields = ['project', 'module', 'status', 'priority']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'priority']
    ordering = ['-created_at']

    @action(detail=True, methods=['get'], url_path='latest-execution')
    def get_latest_execution(self, request, pk=None):
        """获取用例最新的执行结果"""
        test_case = self.get_object()
        execution = ApiTestCaseExecution.objects.filter(test_case=test_case
            ).first()
        if execution:
            return Response(ApiTestCaseExecutionSerializer(execution).data)
        return Response(None)

    @action(detail=True, methods=['get'], url_path='executions')
    def get_executions(self, request, pk=None):
        """获取用例的执行历史"""
        test_case = self.get_object()
        executions = ApiTestCaseExecution.objects.filter(test_case=test_case
            ).order_by('-created_at')[:20]
        return Response(ApiTestCaseExecutionSerializer(executions, many=
            True).data)

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """执行测试用例"""
        test_case = self.get_object()
        environment_id = request.data.get('environment_id')
        engine = request.data.get('engine', 'requests')
        if engine == 'httprunner':
            from ..utils import execute_test_case_httprunner
            try:
                environment = None
                if environment_id:
                    try:
                        # Environment 无法自动解析租户路径（ApiProject 无 organization），
                        # 显式按 created_by 做租户过滤
                        environment = scoped_queryset_for(
                            request.user, Environment,
                            org_field='created_by').get(id=environment_id)
                    except Environment.DoesNotExist:
                        pass
                result = execute_test_case_httprunner(test_case,
                    environment, request.user)
                if result.get('success'):
                    return Response(result)
                else:
                    return Response(result, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({'error': str(e)}, status=status.
                    HTTP_500_INTERNAL_SERVER_ERROR)
        try:
            environment = None
            if environment_id:
                try:
                    # 同上：显式按 created_by 做租户过滤
                    environment = scoped_queryset_for(
                        request.user, Environment,
                        org_field='created_by').get(id=environment_id)
                except Environment.DoesNotExist:
                    pass
            result = execute_test_case(test_case, environment, request.user,
                create_report=True)
            if result.get('success'):
                return Response(result)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.
                HTTP_400_BAD_REQUEST)


class ApiTestCaseStepViewSet(BaseProjectViewSet):
    queryset = ApiTestCaseStep.objects.all()
    serializer_class = ApiTestCaseStepSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['test_case']
    ordering = ['step_number']


class ApiTestCaseExecutionViewSet(TenantAwareViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ApiTestCaseExecution.objects.all()
    serializer_class = ApiTestCaseExecutionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['test_case', 'status']
    ordering = ['-created_at']
    pagination_class = StandardPagination

    def get_queryset(self):
        user = self.request.user
        # 第六轮批次2：接入统一租户隔离
        # 租户锚点 ApiProject(owner/members)；M2M 成员语义 mixin 单 owner 无法表达，
        # 故保留原 owner|members 手工过滤（与统一隔离同等严格，且保留协作权限），不调 _apply_tenant_scope。
        return ApiTestCaseExecution.objects.filter(test_case__project__in=
            ApiProject.objects.filter(models.Q(owner=user) | models.Q(
            members=user))).distinct()


