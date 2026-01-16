from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CICDServerViewSet, CICDJobViewSet, CICDExecutionViewSet,
    CICDLogViewSet, GitLabRepositoryViewSet, CICDTriggerViewSet
)

# 创建路由实例
router = DefaultRouter()

# 注册视图集
router.register(r'servers', CICDServerViewSet, basename='cicd-server')
router.register(r'jobs', CICDJobViewSet, basename='cicd-job')
router.register(r'executions', CICDExecutionViewSet, basename='cicd-execution')
router.register(r'logs', CICDLogViewSet, basename='cicd-log')
router.register(r'gitlab-repos', GitLabRepositoryViewSet, basename='gitlab-repo')
router.register(r'triggers', CICDTriggerViewSet, basename='cicd-trigger')

# 定义应用级URL配置
urlpatterns = [
    path('', include(router.urls)),
]
