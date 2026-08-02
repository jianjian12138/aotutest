from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (TestPlanViewSet, TestRunViewSet, TestRunCaseViewSet, 
                    TestRunCaseHistoryViewSet, K8sRunnerViewSet)

router = DefaultRouter()
router.register(r'plans', TestPlanViewSet)
router.register(r'runs', TestRunViewSet)
router.register(r'run_cases', TestRunCaseViewSet)
router.register(r'history', TestRunCaseHistoryViewSet)
router.register(r'k8s-runners', K8sRunnerViewSet, basename='k8s-runners')

urlpatterns = [
    path('', include(router.urls)),
]
