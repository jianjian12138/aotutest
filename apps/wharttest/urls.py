from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    WHartTestConfigViewSet,
    WHartTestProjectViewSet,
    WHartTestExecutionViewSet,
    WHartTestTaskViewSet,
    WHartTestIntegrationLogViewSet,
    WHartTestDashboardViewSet
)

router = DefaultRouter()
router.register(r'configs', WHartTestConfigViewSet, basename='wharttest-config')
router.register(r'projects', WHartTestProjectViewSet, basename='wharttest-project')
router.register(r'executions', WHartTestExecutionViewSet, basename='wharttest-execution')
router.register(r'tasks', WHartTestTaskViewSet, basename='wharttest-task')
router.register(r'integration-logs', WHartTestIntegrationLogViewSet, basename='wharttest-integration-log')
router.register(r'dashboard', WHartTestDashboardViewSet, basename='wharttest-dashboard')

urlpatterns = [
    path('', include(router.urls)),
]
