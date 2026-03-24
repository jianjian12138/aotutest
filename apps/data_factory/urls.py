from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    VannaConfigViewSet,
    SqlGenerationViewSet,
    DataFactoryProjectViewSet,
    SavedQueryViewSet,
    QueryHistoryViewSet,
    TableMetadataViewSet,
    DataFactoryDashboardViewSet,
    TestDataGeneratorViewSet,
    DataSourceViewSet,
    DataPoolViewSet
)

router = DefaultRouter()
router.register(r'vanna-configs', VannaConfigViewSet, basename='vanna-config')
router.register(r'sql-generations', SqlGenerationViewSet, basename='sql-generation')
router.register(r'projects', DataFactoryProjectViewSet, basename='data-factory-project')
router.register(r'saved-queries', SavedQueryViewSet, basename='saved-query')
router.register(r'query-histories', QueryHistoryViewSet, basename='query-history')
router.register(r'table-metadata', TableMetadataViewSet, basename='table-metadata')
router.register(r'dashboard', DataFactoryDashboardViewSet, basename='data-factory-dashboard')
router.register(r'data-generator', TestDataGeneratorViewSet, basename='data-generator')
router.register(r'data-sources', DataSourceViewSet, basename='data-source')
router.register(r'data-pools', DataPoolViewSet, basename='data-pool')

urlpatterns = [
    path('data-factory/', include(router.urls)),
]
