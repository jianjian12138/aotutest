from apps.notifications.models import NotificationConfig, NotificationLog
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import ScheduledTask, TaskExecutionLog
from .serializers import ScheduledTaskSerializer, NotificationConfigSerializer, TaskExecutionLogSerializer

class ScheduledTaskViewSet(viewsets.ModelViewSet):
    queryset = ScheduledTask.objects.all()
    serializer_class = ScheduledTaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['project', 'task_type', 'status']
    search_fields = ['name', 'description']

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

class NotificationConfigViewSet(viewsets.ModelViewSet):
    queryset = NotificationConfig.objects.all()
    serializer_class = NotificationConfigSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['config_type', 'is_active']
    search_fields = ['name']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class TaskExecutionLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TaskExecutionLog.objects.all()
    serializer_class = TaskExecutionLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['task', 'status']
