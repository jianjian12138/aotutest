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
import requests
import time
import os
import json
import logging
import uuid
import subprocess
from datetime import datetime, timedelta

from .models import (
    WHartTestConfig,
    WHartTestProject,
    WHartTestExecution,
    WHartTestTask,
    WHartTestIntegrationLog
)

from .serializers import (
    WHartTestConfigSerializer,
    WHartTestProjectSerializer,
    WHartTestExecutionSerializer,
    WHartTestTaskSerializer,
    WHartTestIntegrationLogSerializer,
    UserSerializer
)

logger = logging.getLogger(__name__)

User = get_user_model()


class StandardPagination(viewsets.ModelViewSet.pagination_class):
    """标准分页类"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 1000


class WHartTestConfigViewSet(viewsets.ModelViewSet):
    """WHartTest配置视图集"""
    queryset = WHartTestConfig.objects.all()
    serializer_class = WHartTestConfigSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description', 'base_url']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']
    pagination_class = StandardPagination

    def perform_create(self, serializer):
        """创建配置时设置创建者"""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """测试WHartTest服务连接"""
        config = self.get_object()
        try:
            # 模拟测试连接
            # 实际应该调用WHartTest的健康检查API
            time.sleep(1)  # 模拟连接延迟
            return Response({'status': 'success', 'message': '连接成功'})
        except Exception as e:
            logger.error(f"测试WHartTest连接失败: {str(e)}")
            # 记录错误日志
            WHartTestIntegrationLog.objects.create(
                config=config,
                log_level='ERROR',
                message=f"测试连接失败: {str(e)}",
                request_data={'action': 'test_connection'},
                error_details=str(e)
            )
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def _log_integration(self, config, log_level, message, request_data=None, response_data=None, error_details=None):
        """记录集成日志"""
        try:
            WHartTestIntegrationLog.objects.create(
                config=config,
                log_level=log_level,
                message=message,
                request_data=request_data or {},
                response_data=response_data or {},
                error_details=error_details
            )
        except Exception as e:
            logger.error(f"记录集成日志失败: {str(e)}")


class WHartTestProjectViewSet(viewsets.ModelViewSet):
    """WHartTest项目关联视图集"""
    queryset = WHartTestProject.objects.all()
    serializer_class = WHartTestProjectSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['config', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']
    pagination_class = StandardPagination

    def perform_create(self, serializer):
        """创建项目关联时设置创建者"""
        serializer.save(created_by=self.request.user)


class WHartTestExecutionViewSet(viewsets.ModelViewSet):
    """WHartTest执行记录视图集"""
    queryset = WHartTestExecution.objects.all()
    serializer_class = WHartTestExecutionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project', 'status']
    search_fields = ['name', 'description']
    ordering_fields = ['start_time', 'status']
    ordering = ['-start_time']
    pagination_class = StandardPagination

    def perform_create(self, serializer):
        """创建执行记录时设置执行人"""
        serializer.save(executed_by=self.request.user)

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """执行WHartTest任务"""
        execution = self.get_object()
        try:
            # 模拟执行WHartTest任务
            # 实际应该调用WHartTest的执行API
            execution.status = 'RUNNING'
            execution.save()
            
            time.sleep(2)  # 模拟执行延迟
            
            # 模拟执行结果
            execution.status = 'SUCCESS'
            execution.execution_id = f'wharttest-exec-{uuid.uuid4().hex[:8]}'
            execution.result = {
                'passed': 15,
                'failed': 2,
                'total': 17,
                'duration': 120.5,
                'report_url': f'{execution.project.config.base_url}/reports/{execution.execution_id}'
            }
            execution.logs = '模拟WHartTest执行日志...'
            execution.end_time = timezone.now()
            execution.save()
            
            return Response(WHartTestExecutionSerializer(execution).data)
        except Exception as e:
            logger.error(f"执行WHartTest任务失败: {str(e)}")
            execution.status = 'FAILED'
            execution.logs = str(e)
            execution.end_time = timezone.now()
            execution.save()
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """停止WHartTest任务"""
        execution = self.get_object()
        if execution.status != 'RUNNING':
            return Response({'error': '只有运行中的任务才能停止'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 模拟停止WHartTest任务
            # 实际应该调用WHartTest的停止API
            execution.status = 'STOPPED'
            execution.end_time = timezone.now()
            execution.save()
            return Response({'status': 'success', 'message': '任务已停止'})
        except Exception as e:
            logger.error(f"停止WHartTest任务失败: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class WHartTestTaskViewSet(viewsets.ModelViewSet):
    """WHartTest任务视图集"""
    queryset = WHartTestTask.objects.all()
    serializer_class = WHartTestTaskSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project', 'task_type', 'status']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']
    pagination_class = StandardPagination

    def perform_create(self, serializer):
        """创建任务时设置创建者"""
        serializer.save(created_by=self.request.user)


class WHartTestIntegrationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """WHartTest集成日志视图集"""
    queryset = WHartTestIntegrationLog.objects.all()
    serializer_class = WHartTestIntegrationLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['config', 'log_level']
    search_fields = ['message']
    ordering_fields = ['created_at', 'log_level']
    ordering = ['-created_at']
    pagination_class = StandardPagination


class WHartTestDashboardViewSet(viewsets.ViewSet):
    """WHartTest仪表板视图集"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """获取WHartTest汇总数据（默认动作）"""
        # 计算统计数据
        total_projects = WHartTestProject.objects.count()
        total_executions = WHartTestExecution.objects.filter(status='RUNNING').count()
        # 计算成功率
        total_success = WHartTestExecution.objects.filter(status='SUCCESS').count()
        total_all = WHartTestExecution.objects.count()
        success_rate = (total_success / total_all) * 100 if total_all > 0 else 0
        
        return Response({
            'project_count': total_projects,
            'execution_count': total_executions,
            'success_rate': round(success_rate, 2)
        })
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """获取WHartTest汇总数据"""
        # 计算统计数据
        total_configs = WHartTestConfig.objects.count()
        total_projects = WHartTestProject.objects.count()
        total_executions = WHartTestExecution.objects.count()
        recent_executions = WHartTestExecution.objects.order_by('-start_time')[:5]
        
        return Response({
            'total_configs': total_configs,
            'total_projects': total_projects,
            'total_executions': total_executions,
            'recent_executions': WHartTestExecutionSerializer(recent_executions, many=True).data
        })
