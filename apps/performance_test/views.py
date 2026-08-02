from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db import models
from django.utils import timezone
import requests
import time
import os
import json
import logging
import uuid
import subprocess
import threading
from datetime import datetime, timedelta
import tempfile
import shutil

# 延迟导入Locust库，避免启动时的monkey patching问题
locust_available = False

# 设置日志
logger = logging.getLogger(__name__)

from .models import (
    PerformanceProject, PerformanceCollection, PerformanceRequest,
    PerformanceEnvironment, PerformanceTestHistory, PerformanceTestSuite,
    PerformanceTestSuiteRequest, PerformanceTestExecution, PerformanceScheduledTask,
    PerformanceTaskExecutionLog
)

from apps.core_platform.permissions import TenantAwareViewSetMixin

from .serializers import (
    PerformanceProjectSerializer, PerformanceCollectionSerializer, PerformanceRequestSerializer,
    PerformanceEnvironmentSerializer, PerformanceTestHistorySerializer, PerformanceTestSuiteSerializer,
    PerformanceTestSuiteRequestSerializer, PerformanceTestExecutionSerializer,
    PerformanceScheduledTaskSerializer, PerformanceTaskExecutionLogSerializer,
    UserSerializer
)

logger = logging.getLogger(__name__)

User = get_user_model()


class StandardPagination(viewsets.ModelViewSet.pagination_class):
    """标准分页类"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 1000


class PerformanceProjectViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    """性能测试项目视图集"""
    queryset = PerformanceProject.objects.all()
    serializer_class = PerformanceProjectSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project_type', 'status', 'owner']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name', 'start_date']
    ordering = ['-created_at']
    pagination_class = StandardPagination
    # 第六轮批次2：接入统一租户隔离（PerformanceProject 无 organization 字段，租户根为 owner）
    org_field = 'owner'

    def get_queryset(self):
        """获取用户有权限的项目"""
        user = self.request.user
        qs = PerformanceProject.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        # 第六轮批次2：接入统一租户隔离
        return self._apply_tenant_scope(qs)

    def perform_create(self, serializer):
        """创建项目时设置所有者"""
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        """更新项目"""
        serializer.save()


class PerformanceCollectionViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    """性能测试集合视图集"""
    queryset = PerformanceCollection.objects.all()
    serializer_class = PerformanceCollectionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['project', 'parent']
    ordering = ['order', 'created_at']
    pagination_class = StandardPagination
    # 第六轮批次2：接入统一租户隔离（project→PerformanceProject 无 organization，收口到 project.owner）
    org_field = 'project__owner'

    def get_queryset(self):
        """获取用户有权限的集合"""
        user = self.request.user
        qs = PerformanceCollection.objects.filter(
            project__in=PerformanceProject.objects.filter(
                models.Q(owner=user) | models.Q(members=user)
            )
        ).distinct()
        # 第六轮批次2：接入统一租户隔离
        return self._apply_tenant_scope(qs)


class PerformanceRequestViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    """性能测试请求视图集

    自定义 get_queryset 已按 owner/members 做租户隔离；
    引入 mixin 主要为在 @action 内使用 scoped_get 零件。
    第六轮批次2：修复形式挂靠 —— 显式声明自管 + 收口 _apply_tenant_scope。
    """
    tenant_scope_self_managed = True
    tenant_scope_self_managed_reason = (
        'get_queryset 以 collection__project__in = Q(owner=user)|Q(members=user) 的 PerformanceProject 做归属过滤，'
        '未命中即空集（fail-closed），边界不弱于组织级隔离。'
        'PerformanceRequest 无 organization、亦无 project 直连字段，自动解析会落到 created_by，'
        '把项目成员共享的请求收成 creator-only、破坏协作，故声明自管'
    )
    queryset = PerformanceRequest.objects.all()
    serializer_class = PerformanceRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['collection', 'method', 'request_type']
    search_fields = ['name', 'url']
    ordering = ['order', 'created_at']
    pagination_class = StandardPagination

    def get_queryset(self):
        """获取用户有权限的请求"""
        user = self.request.user
        qs = PerformanceRequest.objects.filter(
            collection__project__in=PerformanceProject.objects.filter(
                models.Q(owner=user) | models.Q(members=user)
            )
        ).distinct()
        return self._apply_tenant_scope(qs)

    def perform_create(self, serializer):
        """创建请求时设置创建者"""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """执行单个性能测试请求"""
        performance_request = self.get_object()
        environment_id = request.data.get('environment_id')
        concurrency = request.data.get('concurrency', 1)
        duration = request.data.get('duration', 10)

        env = None
        try:
            # 解析环境变量
            variables = {}
            if environment_id:
                # PerformanceEnvironment 无法自动解析租户路径（PerformanceProject 无
                # organization 字段），显式按 created_by 做租户过滤
                env = self.scoped_get(PerformanceEnvironment,
                                      org_field='created_by', id=environment_id)
                variables.update(env.variables)

            # 替换URL中的变量
            url = self._replace_variables(performance_request.url or '', variables)

            # 准备请求头
            headers = {}
            if isinstance(performance_request.headers, dict):
                headers = performance_request.headers.copy()
                for key, value in headers.items():
                    headers[key] = self._replace_variables(str(value), variables)

            # 准备请求参数
            params = performance_request.params.copy() if performance_request.params else {}
            for key, value in params.items():
                params[key] = self._replace_variables(str(value), variables)

            # 准备请求体
            body_data = None
            if performance_request.body and performance_request.method in ['POST', 'PUT', 'PATCH']:
                body_data = performance_request.body.copy()
                for key, value in body_data.items():
                    if isinstance(value, str):
                        body_data[key] = self._replace_variables(value, variables)

            # 执行性能测试（这里简化处理，实际应该集成Locust）
            time.time()
            
            # 模拟性能测试结果
            total_requests = concurrency * duration
            passed_requests = total_requests - int(total_requests * 0.05)  # 95%成功率
            failed_requests = total_requests - passed_requests
            response_time_avg = 150.5
            response_time_min = 50.2
            response_time_max = 500.8
            rps = concurrency * 2.5
            
            time.time()

            # 创建执行记录
            execution = PerformanceTestExecution.objects.create(
                test_suite=None,
                status='COMPLETED',
                start_time=timezone.now(),
                end_time=timezone.now(),
                executed_by=request.user,
                total_requests=total_requests,
                passed_requests=passed_requests,
                failed_requests=failed_requests,
                response_time_avg=response_time_avg,
                response_time_min=response_time_min,
                response_time_max=response_time_max,
                rps=rps,
                concurrency=concurrency,
                duration=duration,
                results={
                    'requests_per_second': rps,
                    'response_times': {
                        'avg': response_time_avg,
                        'min': response_time_min,
                        'max': response_time_max
                    },
                    'success_rate': passed_requests / total_requests * 100
                },
                locust_logs='模拟Locust执行日志...'
            )

            # 保存请求历史
            # 环境外键改用已过租户校验的 env 对象，杜绝把他租户环境 ID 写入历史
            history = PerformanceTestHistory.objects.create(
                execution=execution,
                request=performance_request,
                environment=env,
                request_data={
                    'url': url,
                    'method': performance_request.method,
                    'headers': headers,
                    'params': params,
                    'body': body_data
                },
                response_data={
                    'status_code': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': {'message': 'success'}
                },
                status_code=200,
                response_time=response_time_avg,
                assertions_results=[]
            )

            return Response({
                'execution': PerformanceTestExecutionSerializer(execution).data,
                'history': PerformanceTestHistorySerializer(history).data
            })

        except Exception as e:
            logger.error(f"执行性能测试请求失败: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def _replace_variables(self, text, variables):
        """替换文本中的变量"""
        if not isinstance(text, str):
            return text
        
        result = text
        for key, value in (variables or {}).items():
            if isinstance(value, dict):
                replacement = str(value.get('currentValue', '') or value.get('initialValue', ''))
            else:
                replacement = str(value) if value is not None else ''
            result = result.replace(f'{{{{{key}}}}}', replacement)
        return result


class PerformanceEnvironmentViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    """性能测试环境视图集"""
    queryset = PerformanceEnvironment.objects.all()
    serializer_class = PerformanceEnvironmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['scope', 'project', 'is_active']
    ordering = ['-created_at']
    pagination_class = StandardPagination
    # 第六轮批次2：接入统一租户隔离（project 可为空，GLOBAL 环境无项目可依，按 created_by 收口）
    org_field = 'created_by'

    def get_queryset(self):
        """获取用户有权限的环境"""
        user = self.request.user
        qs = PerformanceEnvironment.objects.filter(
            models.Q(scope='GLOBAL') |
            models.Q(
                scope='LOCAL',
                project__in=PerformanceProject.objects.filter(
                    models.Q(owner=user) | models.Q(members=user)
                )
            )
        ).distinct().order_by('-created_at')
        # 第六轮批次2：接入统一租户隔离
        return self._apply_tenant_scope(qs)

    def perform_create(self, serializer):
        """创建环境时设置创建者"""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """激活环境"""
        environment = self.get_object()
        
        # 如果是局部环境，取消同项目下其他环境的激活状态
        if environment.scope == 'LOCAL' and environment.project:
            PerformanceEnvironment.objects.filter(
                project=environment.project,
                scope='LOCAL'
            ).update(is_active=False)
        # 如果是全局环境，取消其他全局环境的激活状态
        elif environment.scope == 'GLOBAL':
            PerformanceEnvironment.objects.filter(scope='GLOBAL').update(is_active=False)
        
        environment.is_active = True
        environment.save()
        
        return Response({'message': '环境已激活'})


from .services import LocustService

class PerformanceTestSuiteViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    """性能测试套件视图集"""
    queryset = PerformanceTestSuite.objects.all()
    serializer_class = PerformanceTestSuiteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['project', 'is_active']
    ordering = ['-created_at']
    pagination_class = StandardPagination
    # 第六轮批次2：接入统一租户隔离（project→PerformanceProject 无 organization，收口到 project.owner）
    org_field = 'project__owner'

    def get_queryset(self):
        """获取用户有权限的测试套件"""
        user = self.request.user
        qs = PerformanceTestSuite.objects.filter(
            project__in=PerformanceProject.objects.filter(
                models.Q(owner=user) | models.Q(members=user)
            )
        ).distinct()
        # 第六轮批次2：接入统一租户隔离
        return self._apply_tenant_scope(qs)

    def perform_create(self, serializer):
        """创建测试套件时设置创建者"""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """执行性能测试套件"""
        test_suite = self.get_object()
        concurrency = int(request.data.get('concurrency', 10))
        duration = int(request.data.get('duration', 60))
        worker_count = int(request.data.get('worker_count', test_suite.worker_count))
        
        try:
            # 创建执行记录
            execution = PerformanceTestExecution.objects.create(
                test_suite=test_suite,
                status='RUNNING',
                start_time=timezone.now(),
                executed_by=request.user,
                total_requests=0,
                passed_requests=0,
                failed_requests=0,
                concurrency=concurrency,
                duration=duration,
                # results={'worker_count': worker_count}
            )
            
            # 使用LocustService执行
            # 这里的执行应该是异步的，但为了简化，我们暂时同步执行
            # 在生产环境中，应该使用Celery任务
            LocustService.execute_test_suite(
                test_suite, 
                execution, 
                concurrency, 
                duration, 
                worker_count
            )
            
            return Response(PerformanceTestExecutionSerializer(execution).data)
            
        except Exception as e:
            logger.error(f"执行性能测试套件失败: {str(e)}")
            if 'execution' in locals():
                execution.status = 'FAILED'
                execution.end_time = timezone.now()
                execution.locust_logs = str(e)
                execution.save()
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='add-requests')
    def add_requests(self, request, pk=None):
        """添加请求到测试套件"""
        test_suite = self.get_object()
        request_ids = request.data.get('request_ids', [])
        
        try:
            for request_id in request_ids:
                performance_request = PerformanceRequest.objects.get(id=request_id)
                PerformanceTestSuiteRequest.objects.get_or_create(
                    test_suite=test_suite,
                    request=performance_request,
                    defaults={
                        'order': PerformanceTestSuiteRequest.objects.filter(test_suite=test_suite).count(),
                        'enabled': True,
                        'weight': 1,
                        'assertions': []
                    }
                )
            
            return Response({'message': '添加成功'})
            
        except Exception as e:
            logger.error(f"添加请求到测试套件失败: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PerformanceTestSuiteRequestViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    """性能测试套件请求关联视图集"""
    queryset = PerformanceTestSuiteRequest.objects.all()
    serializer_class = PerformanceTestSuiteRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['test_suite', 'enabled']
    ordering = ['test_suite', 'order']
    pagination_class = StandardPagination
    # 第六轮批次2：接入统一租户隔离（多跳 test_suite→project→owner，逐段已核对）
    org_field = 'test_suite__project__owner'

    def get_queryset(self):
        """获取用户有权限的测试套件请求关联"""
        user = self.request.user
        qs = PerformanceTestSuiteRequest.objects.filter(
            test_suite__project__in=PerformanceProject.objects.filter(
                models.Q(owner=user) | models.Q(members=user)
            )
        ).distinct()
        # 第六轮批次2：接入统一租户隔离
        return self._apply_tenant_scope(qs)


class PerformanceTestExecutionViewSet(TenantAwareViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """性能测试执行记录视图集"""
    queryset = PerformanceTestExecution.objects.all()
    serializer_class = PerformanceTestExecutionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'test_suite']
    ordering = ['-start_time']
    pagination_class = StandardPagination
    # 第六轮批次2：接入统一租户隔离（多跳 test_suite→project→owner，逐段已核对）
    org_field = 'test_suite__project__owner'

    def get_queryset(self):
        """获取用户有权限的执行记录"""
        user = self.request.user
        qs = PerformanceTestExecution.objects.filter(
            test_suite__project__in=PerformanceProject.objects.filter(
                models.Q(owner=user) | models.Q(members=user)
            )
        ).distinct()
        # 第六轮批次2：接入统一租户隔离
        return self._apply_tenant_scope(qs)


class PerformanceTestHistoryViewSet(TenantAwareViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """性能测试历史记录视图集"""
    queryset = PerformanceTestHistory.objects.all()
    serializer_class = PerformanceTestHistorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['request__request_type', 'status_code']
    ordering = ['-executed_at']
    pagination_class = StandardPagination
    # 第六轮批次2：接入统一租户隔离（走 request→collection→project→owner；execution.test_suite 可为空故不取该路径）
    org_field = 'request__collection__project__owner'

    def get_queryset(self):
        """获取用户有权限的历史记录"""
        user = self.request.user
        qs = PerformanceTestHistory.objects.filter(
            request__collection__project__in=PerformanceProject.objects.filter(
                models.Q(owner=user) | models.Q(members=user)
            )
        ).select_related(
            'request', 'environment', 'execution',
            'request__created_by', 'environment__created_by', 'environment__project'
        ).distinct()
        # 第六轮批次2：接入统一租户隔离
        return self._apply_tenant_scope(qs)


class PerformanceScheduledTaskViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    """性能测试定时任务视图集"""
    queryset = PerformanceScheduledTask.objects.all()
    serializer_class = PerformanceScheduledTaskSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'test_suite']
    ordering = ['-created_at']
    pagination_class = StandardPagination
    # 第六轮批次2：接入统一租户隔离（多跳 test_suite→project→owner，逐段已核对）
    org_field = 'test_suite__project__owner'

    def get_queryset(self):
        """获取用户有权限的定时任务"""
        user = self.request.user
        qs = PerformanceScheduledTask.objects.filter(
            test_suite__project__in=PerformanceProject.objects.filter(
                models.Q(owner=user) | models.Q(members=user)
            )
        ).distinct()
        # 第六轮批次2：接入统一租户隔离
        return self._apply_tenant_scope(qs)

    def perform_create(self, serializer):
        """创建定时任务时设置创建者"""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def toggle(self, request, pk=None):
        """切换定时任务状态"""
        task = self.get_object()
        task.status = 'ACTIVE' if task.status != 'ACTIVE' else 'INACTIVE'
        task.save()
        return Response({'status': task.status})


class PerformanceTaskExecutionLogViewSet(TenantAwareViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """性能测试定时任务执行日志视图集"""
    queryset = PerformanceTaskExecutionLog.objects.all()
    serializer_class = PerformanceTaskExecutionLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['task', 'status']
    ordering = ['-created_at']
    pagination_class = StandardPagination
    # 第六轮批次2：接入统一租户隔离（多跳 task→test_suite→project→owner，逐段已核对）
    org_field = 'task__test_suite__project__owner'

    def get_queryset(self):
        """获取用户有权限的任务执行日志"""
        user = self.request.user
        qs = PerformanceTaskExecutionLog.objects.filter(
            task__test_suite__project__in=PerformanceProject.objects.filter(
                models.Q(owner=user) | models.Q(members=user)
            )
        ).distinct()
        # 第六轮批次2：接入统一租户隔离
        return self._apply_tenant_scope(qs)


class PerformanceDashboardViewSet(viewsets.ViewSet):
    """性能测试仪表板视图集"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """获取性能测试汇总数据"""
        user = self.request.user
        
        # 获取用户有权限的项目
        projects = PerformanceProject.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        
        # 计算统计数据
        total_projects = projects.count()
        total_collections = PerformanceCollection.objects.filter(
            project__in=projects
        ).count()
        total_requests = PerformanceRequest.objects.filter(
            collection__project__in=projects
        ).count()
        total_test_suites = PerformanceTestSuite.objects.filter(
            project__in=projects
        ).count()
        total_executions = PerformanceTestExecution.objects.filter(
            test_suite__project__in=projects
        ).count()
        
        # 获取最近的执行记录
        recent_executions = PerformanceTestExecution.objects.filter(
            test_suite__project__in=projects
        ).order_by('-start_time')[:5]
        
        return Response({
            'total_projects': total_projects,
            'total_collections': total_collections,
            'total_requests': total_requests,
            'total_test_suites': total_test_suites,
            'total_executions': total_executions,
            'recent_executions': PerformanceTestExecutionSerializer(recent_executions, many=True).data
        })
