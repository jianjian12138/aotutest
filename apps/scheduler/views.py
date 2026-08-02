from apps.notifications.models import NotificationConfig, NotificationLog
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from apps.core_platform.permissions import TenantAwareViewSetMixin
from .models import ScheduledTask, TaskExecutionLog
from .serializers import ScheduledTaskSerializer, NotificationConfigSerializer, TaskExecutionLogSerializer

class ScheduledTaskViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    queryset = ScheduledTask.objects.all()
    serializer_class = ScheduledTaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['project', 'task_type', 'status']
    search_fields = ['name', 'description']
    # 第六轮批次2：接入统一租户隔离——ScheduledTask.project 可为空（还有 api_project 分支），
    # 走自动解析 project__organization 会把无 project 的任务全部隐藏；
    # created_by 非空必填，是唯一稳定租户锚点，按创建人隔离。
    org_field = 'created_by'

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def run_once(self, request, pk=None):
        """立即执行一次任务"""
        task = self.get_object()
        
        from django_q.tasks import async_task
        from .tasks import execute_scheduled_task
        
        async_task(
            execute_scheduled_task,
            task.id,
            task_name=f"scheduled_task_{task.id}"
        )
        
        return Response({'status': 'Task execution started', 'task_id': task.id}, status=status.HTTP_200_OK)

class NotificationConfigViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    queryset = NotificationConfig.objects.all()
    serializer_class = NotificationConfigSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['config_type', 'is_active']
    search_fields = ['name']
    # 第六轮批次2：接入统一租户隔离——通知配置含 webhook 密钥，按创建人严格隔离
    # （与 apps/notifications 的 NotificationConfigViewSet 口径一致，宁可收紧）
    org_field = 'created_by'

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class TaskExecutionLogViewSet(TenantAwareViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = TaskExecutionLog.objects.all()
    serializer_class = TaskExecutionLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['task', 'status']
    # 第六轮批次2：接入统一租户隔离——日志无租户字段，经 task 外键回溯创建人
    # （TaskExecutionLog.task → ScheduledTask.created_by，路径逐段核对存在，与父任务口径一致）
    org_field = 'task__created_by'
