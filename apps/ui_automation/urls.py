from apps.notifications.models import NotificationConfig, NotificationLog
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from apps.notifications.views import NotificationConfigViewSet, NotificationLogViewSet
from .views import (
    UiProjectViewSet,
    LocatorStrategyViewSet,
    ElementGroupViewSet,
    ElementViewSet,
    TestScriptViewSet,
    PageObjectViewSet,
    ScriptStepViewSet,
    TestSuiteViewSet,
    TestExecutionViewSet,
    ScreenshotViewSet,
    TestCaseViewSet,
    TestCaseStepViewSet,
    TestCaseExecutionViewSet,
    UiScheduledTaskViewSet,
    AIExecutionRecordViewSet,
    AICaseViewSet,
    OperationRecordViewSet,
    UiDashboardViewSet,
    UiDeviceViewSet,
    ExecutionNodeViewSet,
    UiTestCaseModuleViewSet
)
from .views_config import EnvironmentConfigViewSet, AIIntelligentModeConfigViewSet
from .debug_views import DebugFileViewSet

router = DefaultRouter()
router.register(r'debug-files', DebugFileViewSet, basename='debug-files')
router.register(r'dashboard', UiDashboardViewSet, basename='dashboard')
router.register(r'devices', UiDeviceViewSet)
router.register(r'execution-nodes', ExecutionNodeViewSet)
router.register(r'projects', UiProjectViewSet)
router.register(r'locator-strategies', LocatorStrategyViewSet)
router.register(r'element-groups', ElementGroupViewSet)
router.register(r'elements', ElementViewSet)
router.register(r'test-scripts', TestScriptViewSet)
router.register(r'page-objects', PageObjectViewSet)
router.register(r'steps', ScriptStepViewSet)
router.register(r'test-suites', TestSuiteViewSet)
router.register(r'test-executions', TestExecutionViewSet)
router.register(r'screenshots', ScreenshotViewSet)
router.register(r'test-cases', TestCaseViewSet)
router.register(r'test-case-modules', UiTestCaseModuleViewSet)
router.register(r'test-case-steps', TestCaseStepViewSet)
router.register(r'test-case-executions', TestCaseExecutionViewSet)
router.register(r'scheduled-tasks', UiScheduledTaskViewSet)
router.register(r'ai-execution-records', AIExecutionRecordViewSet)
router.register(r'ai-cases', AICaseViewSet, basename='ai-cases')
router.register(r'ai-case-generation', AICaseViewSet, basename='ai-case-generation')
router.register(r'notification-configs', NotificationConfigViewSet, basename='ui-notification-configs')
router.register(r'notification-logs', NotificationLogViewSet, basename='ui-notification-logs')
router.register(r'operation-records', OperationRecordViewSet)


# Configuration Center APIs
router.register(r'config/environment', EnvironmentConfigViewSet, basename='config-environment')
router.register(r'config/ai-mode', AIIntelligentModeConfigViewSet, basename='config-ai-mode')
router.register(r'ai-models', AIIntelligentModeConfigViewSet, basename='ai-models')

urlpatterns = [
    path('', include(router.urls)),
]

# 添加媒体文件路由
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)