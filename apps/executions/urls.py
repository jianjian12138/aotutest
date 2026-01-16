from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TestPlanViewSet, TestRunViewSet, TestRunCaseViewSet, TestRunCaseHistoryViewSet

router = DefaultRouter()
router.register(r'plans', TestPlanViewSet)
router.register(r'runs', TestRunViewSet)
router.register(r'run_cases', TestRunCaseViewSet)
router.register(r'history', TestRunCaseHistoryViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
