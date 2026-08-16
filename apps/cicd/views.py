from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.core_platform.permissions import TenantAwareViewSetMixin
from .models import CICDServer, CICDJob, CICDExecution, CICDLog, GitLabRepository, CICDTrigger
from .serializers import (
    CICDServerSerializer, CICDJobSerializer, CICDExecutionSerializer,
    CICDLogSerializer, GitLabRepositorySerializer, CICDTriggerSerializer,
    TriggerExecutionSerializer
)
import jenkins
import requests
import json
from django.utils import timezone

NOT_IMPLEMENTED_BODY = {
    'status': 'not_implemented',
    'message': 'CI/CD 流水线编排与触发能力本期未交付，敬请期待。',
    'planned': [
        {'key': 'PIPELINE', 'name': '流水线管理', 'desc': 'Pipeline 编排与触发'},
        {'key': 'BUILD', 'name': '构建记录', 'desc': '构建历史与产物'},
        {'key': 'STAGE', 'name': '阶段编排', 'desc': '原生流水线阶段管理'},
    ],
    'eta': '规划中',
}


class PipelineViewSet(viewsets.ViewSet):
    """Pipeline 视图集（真实执行能力本期未交付）。

    返回 200 + 结构化 not_implemented 负载（含 planned 规划项），
    前端据此渲染友好占位，避免 api.js 拦截器把 5xx 当作「服务器错误」弹红条。
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        return Response(NOT_IMPLEMENTED_BODY, status=status.HTTP_200_OK)

    def create(self, request):
        return Response(NOT_IMPLEMENTED_BODY, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        return Response(NOT_IMPLEMENTED_BODY, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        return Response(NOT_IMPLEMENTED_BODY, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='trigger')
    def trigger(self, request, pk=None):
        """触发Pipeline（本期未交付）"""
        return Response(NOT_IMPLEMENTED_BODY, status=status.HTTP_200_OK)

class CICDServerViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    """CI/CD服务器视图集"""
    queryset = CICDServer.objects.all()
    serializer_class = CICDServerSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save()


class CICDJobViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    """CI/CD任务视图集"""
    queryset = CICDJob.objects.all()
    serializer_class = CICDJobSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save()

    @action(detail=True, methods=['post'], url_path='trigger', url_name='trigger')
    def trigger_job(self, request, pk=None):
        """触发CI/CD任务执行"""
        job = self.get_object()
        serializer = TriggerExecutionSerializer(data=request.data)
        
        if serializer.is_valid():
            parameters = serializer.validated_data.get('parameters', {})
            
            try:
                # 根据服务器类型选择不同的触发方式
                if job.server.server_type == 'JENKINS':
                    # Jenkins触发逻辑
                    execution = self._trigger_jenkins_job(job, parameters)
                elif job.server.server_type == 'GITLAB':
                    # GitLab触发逻辑（后续实现）
                    return Response({'error': 'GitLab触发功能尚未实现'}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({'error': '不支持的服务器类型'}, status=status.HTTP_400_BAD_REQUEST)
                
                return Response(CICDExecutionSerializer(execution).data, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _trigger_jenkins_job(self, job, parameters):
        """触发Jenkins任务"""
        # 创建Jenkins连接
        jenkins_server = jenkins.Jenkins(
            job.server.url,
            username=job.server.username,
            password=job.server.password or job.server.token
        )
        
        # 触发构建
        if parameters:
            build_number = jenkins_server.build_job(job.job_name, parameters=parameters)
        else:
            build_number = jenkins_server.build_job(job.job_name)
        
        # 获取构建信息
        jenkins_server.get_build_info(job.job_name, build_number)
        
        # 创建执行记录
        execution = CICDExecution.objects.create(
            job=job,
            execution_id=str(build_number),
            build_number=build_number,
            status='RUNNING',
            parameters=parameters,
            start_time=timezone.now(),
            triggered_by=self.request.user
        )
        
        return execution

    @action(detail=True, methods=['get'], url_path='executions', url_name='executions')
    def list_executions(self, request, pk=None):
        """获取任务的执行记录列表"""
        job = self.get_object()
        executions = job.executions.all().order_by('-created_at')
        serializer = CICDExecutionSerializer(executions, many=True)
        return Response(serializer.data)


class CICDExecutionViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    """CI/CD执行记录视图集"""
    queryset = CICDExecution.objects.all()
    serializer_class = CICDExecutionSerializer
    permission_classes = [IsAuthenticated]
    # CICDExecution 经 job 外键归属 -> job.created_by 为创建者，按当前用户过滤
    org_field = 'job__created_by'

    @action(detail=True, methods=['get'], url_path='logs', url_name='logs')
    def get_logs(self, request, pk=None):
        """获取执行日志"""
        execution = self.get_object()
        logs = execution.logs.all().order_by('created_at')
        serializer = CICDLogSerializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='refresh', url_name='refresh')
    def refresh_status(self, request, pk=None):
        """刷新执行状态"""
        execution = self.get_object()
        job = execution.job
        
        try:
            if job.server.server_type == 'JENKINS':
                # Jenkins刷新逻辑
                self._refresh_jenkins_execution(execution)
            elif job.server.server_type == 'GITLAB':
                # GitLab刷新逻辑（后续实现）
                pass
            
            return Response(CICDExecutionSerializer(execution).data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _refresh_jenkins_execution(self, execution):
        """刷新Jenkins执行状态"""
        job = execution.job
        jenkins_server = jenkins.Jenkins(
            job.server.url,
            username=job.server.username,
            password=job.server.password or job.server.token
        )
        
        try:
            build_info = jenkins_server.get_build_info(job.job_name, execution.build_number)
            
            # 更新执行状态
            status_map = {
                'SUCCESS': 'SUCCESS',
                'FAILURE': 'FAILURE',
                'ABORTED': 'CANCELLED',
                'IN_PROGRESS': 'RUNNING',
                'QUEUED': 'PENDING'
            }
            
            jenkins_status = build_info['result'] or 'IN_PROGRESS'
            execution.status = status_map.get(jenkins_status, 'PENDING')
            
            # 更新时间和时长
            if build_info['timestamp']:
                execution.start_time = timezone.datetime.fromtimestamp(build_info['timestamp'] / 1000)
            
            if build_info['duration'] > 0:
                execution.duration = build_info['duration'] / 1000  # 转换为秒
                if build_info['timestamp']:
                    execution.end_time = execution.start_time + timezone.timedelta(seconds=execution.duration)
            
            execution.save()
            
            # 获取并保存日志
            if execution.status in ['SUCCESS', 'FAILURE', 'CANCELLED']:
                log_content = jenkins_server.get_build_console_output(job.job_name, execution.build_number)
                CICDLog.objects.create(
                    execution=execution,
                    log_content=log_content,
                    log_url=f"{job.job_url}{execution.build_number}/console"
                )
        except Exception as e:
            print(f"刷新Jenkins执行状态失败: {e}")
            # 不抛出异常，仅打印日志


class CICDLogViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    """CI/CD执行日志视图集"""
    queryset = CICDLog.objects.all()
    serializer_class = CICDLogSerializer
    permission_classes = [IsAuthenticated]
    # CICDLog 经 execution -> job 外键归属 -> job.created_by，按当前用户过滤
    org_field = 'execution__job__created_by'


class GitLabRepositoryViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    """GitLab仓库视图集"""
    queryset = GitLabRepository.objects.all()
    serializer_class = GitLabRepositorySerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save()


class CICDTriggerViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    """CI/CD触发配置视图集"""
    queryset = CICDTrigger.objects.all()
    serializer_class = CICDTriggerSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save()


@action(detail=True, methods=['get'], url_path='job-info', url_name='job-info')
def get_job_info(self, request, pk=None):
    """获取Jenkins任务信息"""
    job = self.get_object()
    
    if job.server.server_type != 'JENKINS':
        return Response({'error': '仅支持Jenkins服务器'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        jenkins_server = jenkins.Jenkins(
            job.server.url,
            username=job.server.username,
            password=job.server.password or job.server.token
        )
        
        # 获取任务信息
        job_info = jenkins_server.get_job_info(job.job_name)
        return Response(job_info)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
