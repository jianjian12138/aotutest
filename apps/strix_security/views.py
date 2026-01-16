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
    StrixConfig,
    SecurityTestProject,
    SecurityTestExecution,
    Vulnerability,
    SecurityTestHistory
)

from .serializers import (
    StrixConfigSerializer,
    SecurityTestProjectSerializer,
    SecurityTestExecutionSerializer,
    VulnerabilitySerializer,
    SecurityTestHistorySerializer,
    UserSerializer
)

logger = logging.getLogger(__name__)

User = get_user_model()


class StandardPagination(viewsets.ModelViewSet.pagination_class):
    """标准分页类"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 1000


class StrixConfigViewSet(viewsets.ModelViewSet):
    """Strix安全测试配置视图集"""
    queryset = StrixConfig.objects.all()
    serializer_class = StrixConfigSerializer
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
        """测试Strix服务连接"""
        config = self.get_object()
        try:
            # 模拟测试连接
            # 实际应该调用Strix API进行连接测试
            time.sleep(1)  # 模拟连接延迟
            return Response({'status': 'success', 'message': '连接成功'})
        except Exception as e:
            logger.error(f"测试Strix连接失败: {str(e)}")
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SecurityTestProjectViewSet(viewsets.ModelViewSet):
    """安全测试项目视图集"""
    queryset = SecurityTestProject.objects.all()
    serializer_class = SecurityTestProjectSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description', 'target_url']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']
    pagination_class = StandardPagination

    def perform_create(self, serializer):
        """创建项目时设置创建者"""
        serializer.save(created_by=self.request.user)


class SecurityTestExecutionViewSet(viewsets.ModelViewSet):
    """安全测试执行记录视图集"""
    queryset = SecurityTestExecution.objects.all()
    serializer_class = SecurityTestExecutionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project', 'status', 'scan_type']
    search_fields = ['name', 'description']
    ordering_fields = ['start_time', 'status']
    ordering = ['-start_time']
    pagination_class = StandardPagination

    def perform_create(self, serializer):
        """创建执行记录时设置执行人"""
        serializer.save(executed_by=self.request.user)

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """执行安全测试"""
        execution = self.get_object()
        try:
            execution.status = 'RUNNING'
            execution.save()
            
            # 模拟执行安全测试
            # 实际应该调用Strix API执行安全测试
            time.sleep(2)  # 模拟执行延迟
            
            # 模拟执行结果
            execution.status = 'SUCCESS'
            execution.execution_id = f'strix-exec-{uuid.uuid4().hex[:8]}'
            execution.result = {
                'total_vulnerabilities': 12,
                'critical': 2,
                'high': 4,
                'medium': 3,
                'low': 2,
                'info': 1,
                'scan_duration': 180.5
            }
            execution.vulnerabilities = [
                {
                    'id': f'vuln-{uuid.uuid4().hex[:8]}',
                    'name': 'SQL注入漏洞',
                    'severity': 'CRITICAL',
                    'cvss_score': 9.8,
                    'url': f'{execution.project.target_url}/api/v1/users?id=1'
                },
                {
                    'id': f'vuln-{uuid.uuid4().hex[:8]}',
                    'name': '跨站脚本漏洞',
                    'severity': 'HIGH',
                    'cvss_score': 8.6,
                    'url': f'{execution.project.target_url}/search?q=<script>alert(1)</script>'
                }
            ]
            execution.logs = '模拟Strix执行日志...'
            execution.end_time = timezone.now()
            execution.save()
            
            # 创建漏洞记录
            for vuln_data in execution.vulnerabilities:
                Vulnerability.objects.create(
                    execution=execution,
                    vuln_id=vuln_data['id'],
                    name=vuln_data['name'],
                    description=f'{vuln_data["name"]}的详细描述',
                    severity=vuln_data['severity'],
                    cvss_score=vuln_data['cvss_score'],
                    url=vuln_data['url'],
                    method='GET',
                    fix_suggestion=f'修复{vuln_data["name"]}的建议'
                )
            
            # 创建历史记录
            SecurityTestHistory.objects.create(
                project=execution.project,
                execution=execution,
                created_by=request.user
            )
            
            return Response(SecurityTestExecutionSerializer(execution).data)
        except Exception as e:
            logger.error(f"执行安全测试失败: {str(e)}")
            execution.status = 'FAILED'
            execution.logs = str(e)
            execution.end_time = timezone.now()
            execution.save()
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """停止安全测试"""
        execution = self.get_object()
        if execution.status != 'RUNNING':
            return Response({'error': '只有运行中的任务才能停止'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 模拟停止安全测试
            # 实际应该调用Strix API停止测试
            execution.status = 'STOPPED'
            execution.end_time = timezone.now()
            execution.save()
            return Response({'status': 'success', 'message': '测试已停止'})
        except Exception as e:
            logger.error(f"停止安全测试失败: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class VulnerabilityViewSet(viewsets.ReadOnlyModelViewSet):
    """漏洞记录视图集"""
    queryset = Vulnerability.objects.all()
    serializer_class = VulnerabilitySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['execution', 'severity']
    search_fields = ['name', 'description', 'url']
    ordering_fields = ['severity', 'cvss_score', 'created_at']
    ordering = ['-severity', '-cvss_score', '-created_at']
    pagination_class = StandardPagination


class SecurityTestHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """安全测试历史记录视图集"""
    queryset = SecurityTestHistory.objects.all()
    serializer_class = SecurityTestHistorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['project']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    pagination_class = StandardPagination


class SecurityTestDashboardViewSet(viewsets.ViewSet):
    """安全测试仪表板视图集"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """获取安全测试汇总数据"""
        total_projects = SecurityTestProject.objects.count()
        total_executions = SecurityTestExecution.objects.count()
        total_vulnerabilities = Vulnerability.objects.count()
        critical_vulnerabilities = Vulnerability.objects.filter(severity='CRITICAL').count()
        high_vulnerabilities = Vulnerability.objects.filter(severity='HIGH').count()
        medium_vulnerabilities = Vulnerability.objects.filter(severity='MEDIUM').count()
        low_vulnerabilities = Vulnerability.objects.filter(severity='LOW').count()
        info_vulnerabilities = Vulnerability.objects.filter(severity='INFO').count()
        
        recent_executions = SecurityTestExecution.objects.order_by('-start_time')[:5]
        top_vulnerabilities = Vulnerability.objects.order_by('-severity', '-cvss_score')[:10]
        
        return Response({
            'total_projects': total_projects,
            'total_executions': total_executions,
            'total_vulnerabilities': total_vulnerabilities,
            'vulnerability_stats': {
                'critical': critical_vulnerabilities,
                'high': high_vulnerabilities,
                'medium': medium_vulnerabilities,
                'low': low_vulnerabilities,
                'info': info_vulnerabilities
            },
            'recent_executions': SecurityTestExecutionSerializer(recent_executions, many=True).data,
            'top_vulnerabilities': VulnerabilitySerializer(top_vulnerabilities, many=True).data
        })
