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

from apps.core_platform.permissions import TenantAwareViewSetMixin

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


class StrixConfigViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    """Strix安全测试配置视图集"""
    queryset = StrixConfig.objects.all()
    serializer_class = StrixConfigSerializer
    permission_classes = [IsAuthenticated]
    org_field = 'created_by'
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
        """测试Strix服务连接（真实连接能力本期未交付）"""
        self.get_object()
        return Response(
            {
                'status': 'not_implemented',
                'module': 'Strix 连接测试',
                'message': 'Strix 服务真实连接能力本期未交付',
                'planned': ['Strix 服务连通性校验', '配置健康探测'],
            },
            status=status.HTTP_200_OK,
        )


class SecurityTestProjectViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    """安全测试项目视图集"""
    queryset = SecurityTestProject.objects.all()
    serializer_class = SecurityTestProjectSerializer
    permission_classes = [IsAuthenticated]
    org_field = 'created_by'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description', 'target_url']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']
    pagination_class = StandardPagination

    def perform_create(self, serializer):
        """创建项目时设置创建者"""
        serializer.save(created_by=self.request.user)


class SecurityTestExecutionViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    """安全测试执行记录视图集"""
    queryset = SecurityTestExecution.objects.all()
    serializer_class = SecurityTestExecutionSerializer
    permission_classes = [IsAuthenticated]
    org_field = 'project__created_by'
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
        """执行安全测试（真实扫描能力本期未交付）"""
        self.get_object()
        return Response(
            {
                'status': 'not_implemented',
                'module': '安全测试执行',
                'message': '安全测试真实扫描能力本期未交付',
                'planned': ['漏洞扫描引擎对接', '扫描任务编排', '结果归一化'],
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """停止安全测试（真实执行能力本期未交付）"""
        self.get_object()
        return Response(
            {
                'status': 'not_implemented',
                'module': '安全测试停止',
                'message': '安全测试停止能力本期未交付',
                'planned': ['扫描任务中断控制', '资源回收'],
            },
            status=status.HTTP_200_OK,
        )


class VulnerabilityViewSet(TenantAwareViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """漏洞记录视图集"""
    queryset = Vulnerability.objects.all()
    serializer_class = VulnerabilitySerializer
    permission_classes = [IsAuthenticated]
    org_field = 'execution__project__created_by'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['execution', 'severity']
    search_fields = ['name', 'description', 'url']
    ordering_fields = ['severity', 'cvss_score', 'created_at']
    ordering = ['-severity', '-cvss_score', '-created_at']
    pagination_class = StandardPagination


class SecurityTestHistoryViewSet(TenantAwareViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """安全测试历史记录视图集"""
    queryset = SecurityTestHistory.objects.all()
    serializer_class = SecurityTestHistorySerializer
    permission_classes = [IsAuthenticated]
    org_field = 'created_by'
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
        """获取安全测试汇总数据（租户安全整改：非管理员仅统计自己创建的安全项目）"""
        user = request.user
        is_privileged = user.is_staff or user.is_superuser
        proj_filter = {} if is_privileged else {'project__created_by': user}
        total_projects = SecurityTestProject.objects.filter(
            **({} if is_privileged else {'created_by': user})).count()
        total_executions = SecurityTestExecution.objects.filter(**proj_filter).count()
        total_vulnerabilities = Vulnerability.objects.filter(**proj_filter).count()
        critical_vulnerabilities = Vulnerability.objects.filter(severity='CRITICAL', **proj_filter).count()
        high_vulnerabilities = Vulnerability.objects.filter(severity='HIGH', **proj_filter).count()
        medium_vulnerabilities = Vulnerability.objects.filter(severity='MEDIUM', **proj_filter).count()
        low_vulnerabilities = Vulnerability.objects.filter(severity='LOW', **proj_filter).count()
        info_vulnerabilities = Vulnerability.objects.filter(severity='INFO', **proj_filter).count()

        recent_executions = SecurityTestExecution.objects.filter(**proj_filter).order_by('-start_time')[:5]
        top_vulnerabilities = Vulnerability.objects.filter(**proj_filter).order_by('-severity', '-cvss_score')[:10]

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
