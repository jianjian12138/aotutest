from apps.core_platform.permissions import TenantAwareViewSetMixin
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db import models
from django.conf import settings
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
    MidsceneConfig,
    MidsceneTask,
    MidsceneExecutionLog
)

from .serializers import (
    MidsceneConfigSerializer,
    MidsceneTaskSerializer,
    MidsceneExecutionLogSerializer,
    UserSerializer
)

logger = logging.getLogger(__name__)

User = get_user_model()


class StandardPagination(PageNumberPagination):
    """标准分页类"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 1000


class MidsceneConfigViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    """Midscene.js配置视图集"""
    queryset = MidsceneConfig.objects.all()
    # 第六轮批次2：接入统一租户隔离——MidsceneConfig 含 api_key 敏感配置，
    # 无 organization/project 字段，租户锚点为创建人（与 MidsceneTaskViewSet 口径一致，仅创建者可见）
    org_field = 'created_by'
    serializer_class = MidsceneConfigSerializer
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
        """测试Midscene API连接（真实连接能力本期未交付）"""
        self.get_object()
        return Response(
            {'error': '该能力本期未交付', 'status': 'not_implemented'},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )


class MidsceneTaskViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    """Midscene.js任务视图集"""
    queryset = MidsceneTask.objects.all()
    # MidsceneTask/MidsceneConfig 均无 organization/project 字段，租户锚点为创建人
    org_field = 'created_by'
    serializer_class = MidsceneTaskSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['config', 'status']
    search_fields = ['name', 'description', 'natural_language']
    ordering_fields = ['start_time', 'status']
    ordering = ['-start_time']
    pagination_class = StandardPagination

    def perform_create(self, serializer):
        """创建任务时设置创建者"""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """执行Midscene.js任务"""
        task = self.get_object()
        try:
            task.status = 'RUNNING'
            task.save()
            
            # 准备执行环境
            script_path = os.path.join(settings.BASE_DIR, 'scripts', 'midscene_runner.js')
            output_dir = os.path.join(settings.MEDIA_ROOT, 'midscene_screenshots')
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # 构建 Node.js 命令
            # 注意：需要确保 node 在环境变量中，或者指定完整路径
            # 这里的 cwd 设置为 frontend 目录，因为 node_modules 在那里
            frontend_dir = os.path.join(settings.BASE_DIR, 'frontend')
            node_modules_path = os.path.join(frontend_dir, 'node_modules')
            
            # 设置 NODE_PATH 环境变量，以便脚本能找到 frontend/node_modules 下的依赖
            env = os.environ.copy()
            env['NODE_PATH'] = node_modules_path + os.pathsep + env.get('NODE_PATH', '')
            
            cmd = [
                'node', 
                script_path, 
                task.natural_language, 
                output_dir, 
                str(task.id)
            ]
            
            logger.info(f"开始执行Midscene任务: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=frontend_dir, # 在 frontend 目录下运行
                env=env # 使用包含 NODE_PATH 的环境变量
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Midscene执行失败: {stderr}")
                task.status = 'FAILED'
                task.logs = stderr or "未知错误"
                task.end_time = timezone.now()
                task.save()
                return Response({'error': '执行失败', 'details': stderr}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # 解析输出
            # 输出可能包含多行 JSON，我们需要找到最后一行 type='result' 的
            lines = stdout.strip().split('\n')
            result_data = {}
            logs = []
            
            for line in lines:
                try:
                    data = json.loads(line)
                    if data.get('type') == 'log':
                        logs.append(f"[{data.get('level', 'info').upper()}] {data.get('message')}")
                    elif data.get('type') == 'result':
                        result_data = data
                except json.JSONDecodeError:
                    logs.append(line)
            
            task.logs = '\n'.join(logs)
            
            if result_data.get('status') == 'success':
                task.status = 'SUCCESS'
                task.result = {
                    'screenshot_url': result_data.get('screenshot_url'),
                    'video_url': result_data.get('video_url'),
                    'steps': [] # 暂时简化
                }
            else:
                task.status = 'FAILED'
                task.result = {
                    'error': result_data.get('error'),
                    'screenshot_url': result_data.get('screenshot_url')
                }
                
            task.end_time = timezone.now()
            task.save()
            
            return Response(MidsceneTaskSerializer(task).data)

        except Exception as e:
            logger.error(f"执行Midscene任务异常: {str(e)}")
            task.status = 'FAILED'
            task.logs = str(e)
            task.end_time = timezone.now()
            task.save()
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """停止Midscene.js任务"""
        task = self.get_object()
        if task.status != 'RUNNING':
            return Response({'error': '只有运行中的任务才能停止'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 模拟停止Midscene任务
            # 实际应该调用Midscene API停止任务
            task.status = 'STOPPED'
            task.end_time = timezone.now()
            task.save()
            return Response({'status': 'success', 'message': '任务已停止'})
        except Exception as e:
            logger.error(f"停止Midscene任务失败: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def execute_quick(self, request):
        """快速执行自然语言指令"""
        config_id = request.data.get('config_id')
        natural_language = request.data.get('natural_language')
        name = request.data.get('name', f'快速任务-{datetime.now().strftime("%Y%m%d%H%M%S")}')
        
        if not config_id or not natural_language:
            return Response({'error': '缺少必要参数'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 按租户校验配置归属（MidsceneConfig 无 organization 字段，锚点为创建人）
            config = self.scoped_get(MidsceneConfig, org_field='created_by',
                                     id=config_id, is_active=True)

            # 创建任务：config 已完成归属校验，经其关系访问创建
            task = config.midscenetask_set.create(
                name=name,
                natural_language=natural_language,
                status='RUNNING',
                created_by=request.user
            )
            
            # 准备执行环境
            script_path = os.path.join(settings.BASE_DIR, 'scripts', 'midscene_runner.js')
            output_dir = os.path.join(settings.MEDIA_ROOT, 'midscene_screenshots')
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # 构建 Node.js 命令
            frontend_dir = os.path.join(settings.BASE_DIR, 'frontend')
            node_modules_path = os.path.join(frontend_dir, 'node_modules')
            
            # 设置 NODE_PATH 环境变量
            env = os.environ.copy()
            env['NODE_PATH'] = node_modules_path + os.pathsep + env.get('NODE_PATH', '')
            
            cmd = [
                'node', 
                script_path, 
                task.natural_language, 
                output_dir, 
                str(task.id)
            ]
            
            logger.info(f"开始快速执行Midscene任务: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=frontend_dir, # 在 frontend 目录下运行
                env=env
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Midscene执行失败: {stderr}")
                task.status = 'FAILED'
                task.logs = stderr or "未知错误"
                task.end_time = timezone.now()
                task.save()
                return Response({'error': '执行失败', 'details': stderr}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # 解析输出
            lines = stdout.strip().split('\n')
            result_data = {}
            logs = []
            
            for line in lines:
                try:
                    data = json.loads(line)
                    if data.get('type') == 'log':
                        logs.append(f"[{data.get('level', 'info').upper()}] {data.get('message')}")
                    elif data.get('type') == 'result':
                        result_data = data
                except json.JSONDecodeError:
                    logs.append(line)
            
            task.logs = '\n'.join(logs)
            
            if result_data.get('status') == 'success':
                task.status = 'SUCCESS'
                task.result = {
                    'screenshot_url': result_data.get('screenshot_url'),
                    'video_url': result_data.get('video_url'),
                    'steps': [] 
                }
            else:
                task.status = 'FAILED'
                task.result = {
                    'error': result_data.get('error'),
                    'screenshot_url': result_data.get('screenshot_url')
                }
                
            task.end_time = timezone.now()
            task.save()
            
            return Response(MidsceneTaskSerializer(task).data)
        except MidsceneConfig.DoesNotExist:
            return Response({'error': '有效的Midscene配置不存在'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"快速执行Midscene任务失败: {str(e)}")
            # 如果任务已创建，更新其状态
            if 'task' in locals():
                task.status = 'FAILED'
                task.logs = str(e)
                task.end_time = timezone.now()
                task.save()
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MidsceneExecutionLogViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    """Midscene.js执行日志视图集"""
    queryset = MidsceneExecutionLog.objects.all()
    # 第六轮批次2：接入统一租户隔离——日志本身无租户字段，经 task 外键
    # 回溯创建人（MidsceneExecutionLog.task → MidsceneTask.created_by，路径逐段核对存在）
    org_field = 'task__created_by'
    serializer_class = MidsceneExecutionLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['task', 'log_level']
    search_fields = ['message']
    ordering_fields = ['created_at', 'log_level']
    ordering = ['-created_at']
    pagination_class = StandardPagination
    http_method_names = ['get', 'delete', 'head', 'options']


class MidsceneDashboardViewSet(viewsets.ViewSet):
    """Midscene.js仪表板视图集"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """获取Midscene.js汇总数据（租户安全整改：非管理员仅看自己创建的配置/任务）"""
        user = request.user
        is_privileged = user.is_staff or user.is_superuser
        cfg_qs = MidsceneConfig.objects if is_privileged else MidsceneConfig.objects.filter(created_by=user)
        task_qs = MidsceneTask.objects if is_privileged else MidsceneTask.objects.filter(created_by=user)
        total_configs = cfg_qs.count()
        total_tasks = task_qs.count()
        recent_tasks = task_qs.order_by('-start_time')[:5]

        return Response({
            'total_configs': total_configs,
            'total_tasks': total_tasks,
            'recent_tasks': MidsceneTaskSerializer(recent_tasks, many=True).data
        })
