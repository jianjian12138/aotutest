from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import KnowledgeDocumentViewSet, KnowledgeGraphVizViewSet

router = DefaultRouter()
router.register(r'documents', KnowledgeDocumentViewSet, basename='knowledge-document')
router.register(r'graph', KnowledgeGraphVizViewSet, basename='knowledge-graph-viz')

urlpatterns = [
    path('api/', include(router.urls)),
]
