"""
评测舱 API（路线三 · Phase 1 契约 + Phase 2 核心）。

底座契约（Phase 1）：
- 鉴权：IsAuthenticated + HasTenantFeature(AGENT_EVAL) —— 未开通 agent 测评的租户
  所有评测 API 一律 403（功能开关门禁，与现有 RBAC 正交）。
- 隔离：继承 TenantAwareViewSetMixin 且显式 staff_has_full_access=False，
  平台管理员亦非"超级读者"，严格按 organization 隔离。
- EvalCase 经 dataset 关联租户 → org_field='dataset__organization'。

Phase 2 能力：
- 数据集 / 用例 / 评分器 / 运行 的 CRUD；
- run @action：提交各用例输出，调用评估引擎评分并落库结果 + 汇总指标。
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone

from apps.core_platform.permissions import TenantAwareViewSetMixin
from apps.tenant_features.models import FeatureCode
from apps.tenant_features.permissions import HasTenantFeature

from . import graders
from .models import EvalDataset, EvalCase, GraderConfig, EvalRun, EvalResult, EvalTrace
from .serializers import (
    EvalCaseSerializer,
    EvalDatasetSerializer,
    EvalRunSerializer,
    EvalResultSerializer,
    EvalTraceSerializer,
    GraderConfigSerializer,
)


class _EvalBase(TenantAwareViewSetMixin):
    # 评测舱严格隔离：平台管理员也非"超级读者"
    staff_has_full_access = False
    permission_classes = [IsAuthenticated, HasTenantFeature]
    required_feature = FeatureCode.AGENT_EVAL


class EvalDatasetViewSet(_EvalBase, viewsets.ModelViewSet):
    queryset = EvalDataset.objects.all()
    serializer_class = EvalDatasetSerializer


class EvalCaseViewSet(_EvalBase, viewsets.ModelViewSet):
    # 用例经 dataset 归属于租户
    org_field = 'dataset__organization'
    queryset = EvalCase.objects.all()
    serializer_class = EvalCaseSerializer


class GraderConfigViewSet(_EvalBase, viewsets.ModelViewSet):
    queryset = GraderConfig.objects.all()
    serializer_class = GraderConfigSerializer


class EvalRunViewSet(_EvalBase, viewsets.ModelViewSet):
    queryset = EvalRun.objects.all()
    serializer_class = EvalRunSerializer

    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        """执行一次评测：body 传 {"outputs": {case_id: output_text}}。

        评分器为 LLM_JUDGE 时，复用平台激活的 AIModelConfig；无配置或失败则
        确定性降级（HEURISTIC），绝不外送未配置租户的数据。
        """
        run = self.get_object()
        outputs = request.data.get('outputs', {}) or {}

        llm_config = None
        if run.grader.grader_type == 'LLM_JUDGE':
            from apps.requirement_analysis.models import AIModelConfig
            llm_config = AIModelConfig.objects.filter(is_active=True).first()

        try:
            summary = graders.grade_run(run, outputs, llm_config=llm_config)
        except Exception as exc:  # noqa: BLE001
            run.status = 'FAILED'
            run.save()
            return Response(
                {'detail': f'评测执行失败：{exc}'}, status=status.HTTP_400_BAD_REQUEST
            )

        run.status = 'DONE'
        run.mean_score = summary['mean_score']
        run.pass_rate = summary['pass_rate']
        run.edge_pass_rate = summary['edge_pass_rate']
        run.save()

        EvalResult.objects.filter(run=run).delete()
        for r in summary['results']:
            # 确定性 RULE 结果无需人工复核；LLM/启发式结果默认待复核（HITL 门）
            review_status = 'APPROVED' if r['judge'] == 'RULE' else 'PENDING'
            EvalResult.objects.create(
                run=run, case=r['case'], score=r['score'],
                passed=r['passed'], judge=r['judge'], reason=r['reason'],
                review_status=review_status,
            )

        return Response(self.get_serializer(run).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """人机协同复核门（HITL）：对单条结果人工确认/驳回。

        body: {"result_id": <int>, "review_status": "APPROVED|REJECTED",
               "review_note": "<可选>"}
        阻断"用例预期错误 → 分析误报"的静默传播：LLM 裁判类结果须人工确认方为可信。
        """
        run = self.get_object()
        result_id = request.data.get('result_id')
        review_status = request.data.get('review_status')
        note = request.data.get('review_note', '') or ''

        if review_status not in ('APPROVED', 'REJECTED'):
            return Response(
                {'detail': 'review_status 必须为 APPROVED 或 REJECTED'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = run.results.filter(id=result_id).first()
        if not result:
            return Response({'detail': '结果不存在或不属于该运行'}, status=status.HTTP_404_NOT_FOUND)

        result.review_status = review_status
        result.review_note = note
        result.reviewer = request.user
        result.reviewed_at = timezone.now()
        result.save()
        return Response(EvalResultSerializer(result).data, status=status.HTTP_200_OK)


class EvalTraceViewSet(_EvalBase, viewsets.ModelViewSet):
    """M4：步骤级 Trace 的存储与回放检索。

    - 创建：POST {"run":<id>,"case":<id>,"status":...,"total_latency_ms":...,
      "steps":[{step_index,step_type,name,input_data,output_data,latency_ms,error}]}
      步骤严格按 step_index 排序落库，支持回放与失败归因（规划弱 vs 工具错）。
    - 列表：?run=<id>&case=<id> 过滤，按 trace 创建时间倒序，steps 内按 step_index 升序。
    租户隔离经 run__organization（org_field）；越权创建由 serializer 拦截。
    """

    org_field = 'run__organization'
    queryset = EvalTrace.objects.all().prefetch_related('steps')
    serializer_class = EvalTraceSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        run = self.request.query_params.get('run')
        case = self.request.query_params.get('case')
        if run:
            qs = qs.filter(run_id=run)
        if case:
            qs = qs.filter(case_id=case)
        return qs
