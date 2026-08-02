from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MidsceneConfigViewSet,
    MidsceneTaskViewSet,
    MidsceneExecutionLogViewSet,
    MidsceneDashboardViewSet
)

router = DefaultRouter()
router.register(r'configs', MidsceneConfigViewSet, basename='midscene-config')
router.register(r'tasks', MidsceneTaskViewSet, basename='midscene-task')
router.register(r'execution-logs', MidsceneExecutionLogViewSet, basename='midscene-execution-log')
router.register(r'dashboard', MidsceneDashboardViewSet, basename='midscene-dashboard')

urlpatterns = [
    path('midscene/', include(router.urls)),
]
