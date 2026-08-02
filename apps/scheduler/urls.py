from apps.notifications.models import NotificationConfig, NotificationLog
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ScheduledTaskViewSet, NotificationConfigViewSet, TaskExecutionLogViewSet

router = DefaultRouter()
router.register(r'tasks', ScheduledTaskViewSet, basename='scheduled-tasks')
router.register(r'notifications', NotificationConfigViewSet, basename='notification-configs')
router.register(r'logs', TaskExecutionLogViewSet, basename='task-execution-logs')

urlpatterns = [
    path('', include(router.urls)),
]
