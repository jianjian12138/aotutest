from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StrixConfigViewSet,
    SecurityTestProjectViewSet,
    SecurityTestExecutionViewSet,
    VulnerabilityViewSet,
    SecurityTestHistoryViewSet,
    SecurityTestDashboardViewSet
)

router = DefaultRouter()
router.register(r'configs', StrixConfigViewSet, basename='strix-config')
router.register(r'projects', SecurityTestProjectViewSet, basename='security-test-project')
router.register(r'executions', SecurityTestExecutionViewSet, basename='security-test-execution')
router.register(r'vulnerabilities', VulnerabilityViewSet, basename='vulnerability')
router.register(r'history', SecurityTestHistoryViewSet, basename='security-test-history')
router.register(r'dashboard', SecurityTestDashboardViewSet, basename='security-test-dashboard')

urlpatterns = [
    path('strix-security/', include(router.urls)),
]