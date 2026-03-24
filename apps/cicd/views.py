from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
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

class PipelineViewSet(viewsets.ViewSet):
    """Mock Pipeline 视图集"""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        mock_pipelines = [
            {
                "id": 101,
                "name": "Platform Nightly Core Regression",
                "description": "每天凌晨2点定时触发的 API + UI 自动化全链路回归流水线",
                "is_active": True,
                "updated_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "id": 102,
                "name": "性能压测预热管道 (Staging Environment)",
                "description": "部署前对测试环境进行基准 QPS 并发轰炸评估",
                "is_active": True,
                "updated_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "id": 103,
                "name": "安全漏洞主动探底调度流",
                "description": "联动 Strix 工具进行平台源码级深度 SAST 审计与污点扫描",
                "is_active": False,
                "updated_at": timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        ]
        return Response({"results": mock_pipelines, "count": len(mock_pipelines)})
        
    def create(self, request):
        data = request.data
        data['id'] = 1
        data['is_active'] = True
        return Response(data, status=status.HTTP_201_CREATED)
        
    def retrieve(self, request, pk=None):
        return Response({
            "id": pk,
            "name": "Mock Pipeline",
            "description": "Mock description",
            "is_active": True
        })
        
    def destroy(self, request, pk=None):
        return Response(status=status.HTTP_204_NO_CONTENT)
        
    @action(detail=True, methods=['post'], url_path='trigger')
    def trigger(self, request, pk=None):
        """触发Pipeline"""
        return Response({'message': 'Pipeline triggered successfully'}, status=status.HTTP_200_OK)

class CICDServerViewSet(viewsets.ModelViewSet):
    """CI/CD服务器视图集"""
    queryset = CICDServer.objects.all()
    serializer_class = CICDServerSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save()


class CICDJobViewSet(viewsets.ModelViewSet):
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
        build_info = jenkins_server.get_build_info(job.job_name, build_number)
        
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


class CICDExecutionViewSet(viewsets.ModelViewSet):
    """CI/CD执行记录视图集"""
    queryset = CICDExecution.objects.all()
    serializer_class = CICDExecutionSerializer
    permission_classes = [IsAuthenticated]

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


class CICDLogViewSet(viewsets.ModelViewSet):
    """CI/CD执行日志视图集"""
    queryset = CICDLog.objects.all()
    serializer_class = CICDLogSerializer
    permission_classes = [IsAuthenticated]


class GitLabRepositoryViewSet(viewsets.ModelViewSet):
    """GitLab仓库视图集"""
    queryset = GitLabRepository.objects.all()
    serializer_class = GitLabRepositorySerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save()


class CICDTriggerViewSet(viewsets.ModelViewSet):
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
