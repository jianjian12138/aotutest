from rest_framework.routers import DefaultRouter

from .views import (
    EvalCaseViewSet,
    EvalDatasetViewSet,
    EvalRunViewSet,
    EvalTraceViewSet,
    GraderConfigViewSet,
)

router = DefaultRouter()
router.register(r'datasets', EvalDatasetViewSet, basename='eval-dataset')
router.register(r'cases', EvalCaseViewSet, basename='eval-case')
router.register(r'graders', GraderConfigViewSet, basename='eval-grader')
router.register(r'runs', EvalRunViewSet, basename='eval-run')
router.register(r'traces', EvalTraceViewSet, basename='eval-trace')

urlpatterns = router.urls
