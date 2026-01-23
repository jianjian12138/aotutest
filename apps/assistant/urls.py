from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AssistantSessionViewSet, ChatViewSet, assistant_view, KnowledgeGraphViewSet
from .views_config import DifyConfigViewSet, AIWorkflowConfigViewSet

router = DefaultRouter()
router.register(r'sessions', AssistantSessionViewSet, basename='assistant-sessions')
router.register(r'chat', ChatViewSet, basename='chat')
router.register(r'config/dify', DifyConfigViewSet, basename='dify-config')
router.register(r'config/workflow', AIWorkflowConfigViewSet, basename='workflow-config')
router.register(r'api/documents', KnowledgeGraphViewSet, basename='knowledge-documents')

urlpatterns = [
    path('', include(router.urls)),
    path('view/', assistant_view, name='assistant-view'),
]
