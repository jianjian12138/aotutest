from apps.core_platform.views.base import BaseProjectViewSet
from apps.core_platform.permissions import TenantAwareViewSetMixin
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

class ApiCollectionViewSet(BaseProjectViewSet):
    queryset = ApiCollection.objects.all()
    serializer_class = ApiCollectionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['project', 'parent']

    def perform_destroy(self, instance):
        """删除集合时记录日志"""
        log_operation(operation_type='delete', resource_type='collection',
            resource_id=instance.id, resource_name=instance.name, user=self
            .request.user)
        instance.delete()


class ApiRequestViewSet(TenantAwareViewSetMixin, BaseProjectViewSet):
    # 说明：自定义 get_queryset 已按 owner/members 做租户隔离（含成员共享语义），
    # 引入 mixin 主要为在 @action 内使用 scoped_get/scoped_filter 零件。
    # 第六轮批次2：核查该历史遗留形式挂靠，确认边界有效，显式声明自管并收口 _apply_tenant_scope。
    tenant_scope_self_managed = True
    tenant_scope_self_managed_reason = (
        'get_queryset 以 collection__project__in = Q(owner=user)|Q(members=user) 的 ApiProject 做归属过滤，'
        '未命中即空集（fail-closed）；query_params 的 project 只在该已收敛集合上二次收窄，'
        '传他人 project id 也读不到数据。ApiRequest 无 organization、亦无 project 直连字段，'
        '自动解析会落到 created_by，把项目成员共享的接口收成 creator-only、破坏协作，故声明自管'
    )
    queryset = ApiRequest.objects.all()
    serializer_class = ApiRequestSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['collection', 'method', 'request_type',
        'collection__project']
    search_fields = ['name', 'url']
    ordering_fields = ['name', 'url', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        queryset = ApiRequest.objects.filter(collection__project__in=
            ApiProject.objects.filter(models.Q(owner=user) | models.Q(
            members=user))).distinct()
        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(collection__project_id=project_id)
        return self._apply_tenant_scope(queryset)

    def perform_destroy(self, instance):
        """删除接口时记录日志"""
        log_operation(operation_type='delete', resource_type='request',
            resource_id=instance.id, resource_name=instance.name, user=self
            .request.user)
        instance.delete()

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """执行API请求"""
        api_request = self.get_object()
        environment_id = request.data.get('environment_id')
        engine = request.data.get('engine', 'requests')
        if engine == 'httprunner':
            from ..utils import execute_api_request_httprunner
            try:
                environment = None
                if environment_id:
                    try:
                        # Environment 无 organization 且 ApiProject 无 organization 字段，
                        # 显式按 created_by 做租户过滤
                        environment = self.scoped_get(Environment,
                            org_field='created_by', id=environment_id)
                    except Environment.DoesNotExist:
                        pass
                result = execute_api_request_httprunner(api_request,
                    environment, request.user)
                if result.get('success'):
                    return Response(result)
                else:
                    return Response(result, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({'error': str(e)}, status=status.
                    HTTP_500_INTERNAL_SERVER_ERROR)
        env = None
        try:
            variables = {}
            if environment_id:
                try:
                    env = self.scoped_get(Environment,
                        org_field='created_by', id=environment_id)
                    variables.update(env.variables)
                except Environment.DoesNotExist:
                    pass
            global_params = GlobalParameter.objects.all()
            for param in global_params:
                if param.key not in variables:
                    variables[param.key] = param.value
            url = self._replace_variables(api_request.url or '', variables)
            headers = {}
            if isinstance(api_request.headers, list):
                for header_item in api_request.headers:
                    if header_item.get('enabled', True) and header_item.get(
                        'key'):
                        key = header_item['key']
                        value = self._replace_variables(str(header_item.get
                            ('value', '')), variables)
                        headers[key] = value
            else:
                headers = api_request.headers.copy()
                for key, value in headers.items():
                    headers[key] = self._replace_variables(str(value),
                        variables)
            params = api_request.params.copy() if api_request.params else {}
            for key, value in params.items():
                params[key] = self._replace_variables(str(value), variables)
            body_data = None
            if api_request.body and api_request.method in ['POST', 'PUT',
                'PATCH']:
                if api_request.body.get('type') == 'json':
                    body_data = api_request.body.get('data', {})
                    body_data = self._replace_variables_in_dict(body_data,
                        variables)
                else:
                    body_data = self._replace_variables_in_dict(api_request
                        .body.get('data'), variables)
            start_time = time.time()
            response = requests.request(method=api_request.method, url=url,
                headers=headers, params=params, json=body_data, timeout=30)
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            assertions = api_request.assertions or []
            for assertion in assertions:
                if assertion.get('type') == 'response_time':
                    assertion['actual_time'] = response_time
            assertions_results = execute_assertions(response, assertions)
            # 通过已校验父对象 api_request 的关系创建，环境改用已过租户校验的 env
            history = api_request.histories.create(
                environment=env, request_data={'url': url,
                'method': api_request.method, 'headers': headers, 'params':
                params, 'body': body_data}, response_data={'headers': dict(
                response.headers), 'body': response.text, 'json': response.
                json() if response.headers.get('content-type', '').
                startswith('application/json') else None, 'size': len(
                response.content)}, status_code=response.status_code,
                response_time=response_time, executed_by=request.user)
            log_operation(operation_type='execute', resource_type='request',
                resource_id=api_request.id, resource_name=api_request.name,
                user=request.user)
            history_data = RequestHistorySerializer(history).data
            history_data['assertions_results'] = assertions_results
            return Response(history_data)
        except Exception as e:
            # 通过已校验父对象 api_request 的关系创建，环境改用已过租户校验的 env
            history = api_request.histories.create(
                environment=env, request_data={'url':
                api_request.url, 'method': api_request.method, 'headers':
                api_request.headers, 'params': api_request.params, 'body':
                api_request.body}, error_message=str(e), executed_by=
                request.user)
            return Response(RequestHistorySerializer(history).data, status=
                status.HTTP_400_BAD_REQUEST)

    def _replace_variables(self, text, variables):
        """替换文本中的变量"""
        if not isinstance(text, str):
            return text
        result = text
        for key, value in (variables or {}).items():
            if isinstance(value, dict):
                replacement = str(value.get('currentValue', '') or value.
                    get('initialValue', ''))
            else:
                replacement = str(value) if value is not None else ''
            result = result.replace(f'{{{{{key}}}}}', replacement)
        return result

    def _replace_variables_in_dict(self, data, variables):
        """递归替换字典中的变量"""
        if isinstance(data, dict):
            return {k: self._replace_variables_in_dict(v, variables) for k,
                v in data.items()}
        elif isinstance(data, list):
            return [self._replace_variables_in_dict(item, variables) for
                item in data]
        elif isinstance(data, str):
            return self._replace_variables(data, variables)
        else:
            return data


class RequestHistoryViewSet(BaseProjectViewSet):
    queryset = RequestHistory.objects.all()
    serializer_class = RequestHistorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['request__request_type', 'status_code']
    ordering = ['-executed_at']
    pagination_class = StandardPagination

    @action(detail=False, methods=['post'], url_path='batch-delete')
    def batch_delete(self, request):
        """批量删除请求历史"""
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'error': '未提供要删除的记录ID'}, status=status.
                HTTP_400_BAD_REQUEST)
        queryset = self.get_queryset()
        valid_ids = list(queryset.filter(id__in=ids).values_list('id', flat
            =True))
        deleted_count, _ = RequestHistory.objects.filter(id__in=valid_ids
            ).delete()
        return Response({'message': f'成功删除 {deleted_count} 条记录'})


