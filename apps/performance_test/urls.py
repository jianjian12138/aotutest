from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PerformanceDashboardViewSet,
    PerformanceProjectViewSet,
    PerformanceCollectionViewSet,
    PerformanceRequestViewSet,
    PerformanceEnvironmentViewSet,
    PerformanceTestHistoryViewSet,
    PerformanceTestSuiteViewSet,
    PerformanceTestSuiteRequestViewSet,
    PerformanceTestExecutionViewSet,
    PerformanceScheduledTaskViewSet,
    PerformanceTaskExecutionLogViewSet
)

router = DefaultRouter()
router.register(r'dashboard', PerformanceDashboardViewSet, basename='performance-dashboard')
router.register(r'projects', PerformanceProjectViewSet, basename='performance-project')
router.register(r'collections', PerformanceCollectionViewSet, basename='performance-collection')
router.register(r'requests', PerformanceRequestViewSet, basename='performance-request')
router.register(r'environments', PerformanceEnvironmentViewSet, basename='performance-environment')
router.register(r'histories', PerformanceTestHistoryViewSet, basename='performance-history')
router.register(r'test-suites', PerformanceTestSuiteViewSet, basename='performance-test-suite')
router.register(r'test-suite-requests', PerformanceTestSuiteRequestViewSet, basename='performance-test-suite-request')
router.register(r'test-executions', PerformanceTestExecutionViewSet, basename='performance-test-execution')
router.register(r'scheduled-tasks', PerformanceScheduledTaskViewSet, basename='performance-scheduled-task')
router.register(r'task-execution-logs', PerformanceTaskExecutionLogViewSet, basename='performance-task-execution-log')

urlpatterns = [
    path('performance-testing/', include(router.urls)),
]
