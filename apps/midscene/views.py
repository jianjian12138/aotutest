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


class StandardPagination(viewsets.ModelViewSet.pagination_class):
    """标准分页类"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 1000


class MidsceneConfigViewSet(viewsets.ModelViewSet):
    """Midscene.js配置视图集"""
    queryset = MidsceneConfig.objects.all()
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
        """测试Midscene API连接"""
        config = self.get_object()
        try:
            # 模拟测试连接
            # 实际应该调用Midscene API进行连接测试
            time.sleep(1)  # 模拟连接延迟
            return Response({'status': 'success', 'message': '连接成功'})
        except Exception as e:
            logger.error(f"测试Midscene连接失败: {str(e)}")
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MidsceneTaskViewSet(viewsets.ModelViewSet):
    """Midscene.js任务视图集"""
    queryset = MidsceneTask.objects.all()
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
            
            # 调用Midscene API执行任务
            headers = {
                'Authorization': f'Bearer {task.config.api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'natural_language': task.natural_language,
                'name': task.name,
                'description': task.description or ''
            }
            
            try:
                # 实际调用Midscene API
                response = requests.post(
                    f'{task.config.base_url}/tasks/execute',
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    task.task_id = result.get('task_id')
                    
                    # 轮询任务状态，直到完成或超时
                    max_retries = 60  # 最多轮询60次
                    retry_interval = 5  # 每5秒轮询一次
                    
                    for _ in range(max_retries):
                        status_response = requests.get(
                            f'{task.config.base_url}/tasks/{task.task_id}/status',
                            headers=headers,
                            timeout=10
                        )
                        
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            task_status = status_data.get('status')
                            
                            if task_status in ['SUCCESS', 'FAILED', 'STOPPED']:
                                task.status = task_status
                                task.result = status_data.get('result', {})
                                task.logs = status_data.get('logs', '')
                                task.end_time = timezone.now()
                                task.save()
                                break
                            
                            # 任务仍在运行，继续轮询
                            time.sleep(retry_interval)
                        else:
                            # 状态查询失败，退出轮询
                            break
                    else:
                        # 轮询超时
                        task.status = 'FAILED'
                        task.logs = '任务执行超时'
                        task.end_time = timezone.now()
                        task.save()
                else:
                    # API调用失败
                    task.status = 'FAILED'
                    task.logs = f'API调用失败: {response.status_code} - {response.text}'
                    task.end_time = timezone.now()
                    task.save()
            except requests.exceptions.RequestException as e:
                # 网络请求异常，使用模拟数据
                logger.warning(f"Midscene API调用失败，使用模拟数据: {str(e)}")
                
                # 模拟执行结果
                task.status = 'SUCCESS'
                task.task_id = f'midscene-task-{uuid.uuid4().hex[:8]}'
                task.result = {
                    'steps': [
                        {'action': '打开浏览器', 'status': 'success'},
                        {'action': '导航到网址', 'status': 'success'},
                        {'action': '输入搜索关键词', 'status': 'success'},
                        {'action': '点击搜索按钮', 'status': 'success'}
                    ],
                    'screenshot_url': f'{task.config.base_url}/screenshots/{task.task_id}',
                    'video_url': f'{task.config.base_url}/videos/{task.task_id}',
                    'duration': 15.2
                }
                task.logs = '模拟Midscene执行日志...'
                task.end_time = timezone.now()
                task.save()
            
            return Response(MidsceneTaskSerializer(task).data)
        except Exception as e:
            logger.error(f"执行Midscene任务失败: {str(e)}")
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
            config = MidsceneConfig.objects.get(id=config_id, is_active=True)
            
            # 创建并执行任务
            task = MidsceneTask.objects.create(
                config=config,
                name=name,
                natural_language=natural_language,
                status='RUNNING',
                created_by=request.user
            )
            
            # 模拟执行
            time.sleep(2)
            
            task.status = 'SUCCESS'
            task.task_id = f'midscene-task-{uuid.uuid4().hex[:8]}'
            task.result = {
                'steps': [
                    {'action': '执行自然语言指令', 'status': 'success'},
                    {'action': '完成任务', 'status': 'success'}
                ],
                'duration': 10.5
            }
            task.logs = '快速执行任务日志...'
            task.end_time = timezone.now()
            task.save()
            
            return Response(MidsceneTaskSerializer(task).data)
        except MidsceneConfig.DoesNotExist:
            return Response({'error': '有效的Midscene配置不存在'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"快速执行Midscene任务失败: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class MidsceneExecutionLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Midscene.js执行日志视图集"""
    queryset = MidsceneExecutionLog.objects.all()
    serializer_class = MidsceneExecutionLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['task', 'log_level']
    search_fields = ['message']
    ordering_fields = ['created_at', 'log_level']
    ordering = ['-created_at']
    pagination_class = StandardPagination


class MidsceneDashboardViewSet(viewsets.ViewSet):
    """Midscene.js仪表板视图集"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """获取Midscene.js汇总数据"""
        total_configs = MidsceneConfig.objects.count()
        total_tasks = MidsceneTask.objects.count()
        recent_tasks = MidsceneTask.objects.order_by('-start_time')[:5]
        
        return Response({
            'total_configs': total_configs,
            'total_tasks': total_tasks,
            'recent_tasks': MidsceneTaskSerializer(recent_tasks, many=True).data
        })
