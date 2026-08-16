from rest_framework.routers import DefaultRouter

from .views import (
    EvalCaseViewSet,
    EvalDatasetViewSet,
    EvalRunViewSet,
    EvalTraceViewSet,
    EvalPlanViewSet,
    KnowledgeDocViewSet,
    EvalScheduleViewSet,
    SkillVersionViewSet,
    GraderConfigViewSet,
    ColdStartViewSet,
    EdgeCaseRuleViewSet,
    JudgeStrengthViewSet,
)

router = DefaultRouter()
router.register(r'datasets', EvalDatasetViewSet, basename='eval-dataset')
router.register(r'cases', EvalCaseViewSet, basename='eval-case')
router.register(r'graders', GraderConfigViewSet, basename='eval-grader')
router.register(r'runs', EvalRunViewSet, basename='eval-run')
router.register(r'traces', EvalTraceViewSet, basename='eval-trace')
router.register(r'plans', EvalPlanViewSet, basename='eval-plan')
router.register(r'knowledge', KnowledgeDocViewSet, basename='eval-knowledge')
router.register(r'schedules', EvalScheduleViewSet, basename='eval-schedule')
router.register(r'skill-versions', SkillVersionViewSet, basename='eval-skill-version')
router.register(r'cold-start', ColdStartViewSet, basename='eval-cold-start')
router.register(r'edge-rules', EdgeCaseRuleViewSet, basename='eval-edge-rule')
router.register(r'judge-strengths', JudgeStrengthViewSet, basename='eval-judge-strength')

urlpatterns = router.urls
