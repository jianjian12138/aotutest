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
import re
from django.utils import timezone

from apps.core_platform.permissions import TenantAwareViewSetMixin
from apps.tenant_features.models import FeatureCode
from apps.tenant_features.permissions import HasTenantFeature

from . import graders, agents
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

    @action(detail=True, methods=['get'])
    def report(self, request, pk=None):
        """M5 报告看板数据：数据集下全部运行的趋势 + 聚合概览 + 各评分器维度汇总。

        供前端绘制分数趋势图与概览卡片（对齐 Opik 生产监控看板），
        使非技术同事也能看懂评测结论。仅读取，不产生副作用。
        租户隔离经 _EvalBase 的 organization 过滤（他租户数据集 → 404）。
        """
        dataset = self.get_object()
        runs = (
            EvalRun.objects.filter(dataset=dataset)
            .select_related('grader')
            .order_by('created_at')
        )
        runs_data = EvalRunSerializer(runs, many=True).data
        total = len(runs_data)
        if total:
            mean_scores = [r['mean_score'] for r in runs_data if r['mean_score'] is not None]
            pass_rates = [r['pass_rate'] for r in runs_data if r['pass_rate'] is not None]
            avg_mean = round(sum(mean_scores) / len(mean_scores), 3) if mean_scores else None
            avg_pass = round(sum(pass_rates) / len(pass_rates), 3) if pass_rates else None
            latest = runs_data[-1]
            best = max(
                runs_data,
                key=lambda r: r['mean_score'] if r['mean_score'] is not None else -1,
            )
            worst = min(
                runs_data,
                key=lambda r: r['mean_score'] if r['mean_score'] is not None else 2,
            )
            by_grader = {}
            for r in runs:
                gt = r.grader.grader_type
                d = by_grader.setdefault(gt, {'count': 0, 'scores': []})
                d['count'] += 1
                if r.mean_score is not None:
                    d['scores'].append(r.mean_score)
            grader_breakdown = [
                {
                    'grader_type': gt,
                    'run_count': d['count'],
                    'avg_mean_score': (
                        round(sum(d['scores']) / len(d['scores']), 3)
                        if d['scores'] else None
                    ),
                }
                for gt, d in by_grader.items()
            ]
        else:
            latest = best = worst = None
            avg_mean = avg_pass = None
            grader_breakdown = []
        return Response({
            'dataset': EvalDatasetSerializer(dataset).data,
            'total_runs': total,
            'latest': latest,
            'best': best,
            'worst': worst,
            'avg_mean_score': avg_mean,
            'avg_pass_rate': avg_pass,
            'grader_breakdown': grader_breakdown,
            'runs': runs_data,
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def clone_version(self, request, pk=None):
        """A3 数据集版本化：基于当前数据集（base）创建同组织/同名的新版本并复制全部用例。

        历史版本保留可查（EvalDataset 按 (organization, name, version) 唯一）。
        body 可选 {"new_version": "v2", "description": "..."}；缺省自动 bump 版本号。
        复制用例时保留 code（保证跨版本 diff 对应），原 code 为空则派生 case-<id>。
        """
        base = self.get_object()
        new_version = request.data.get('new_version') or self._next_version(base)
        if EvalDataset.objects.filter(
            organization=base.organization, name=base.name, version=new_version
        ).exists():
            return Response(
                {'detail': f'版本 {new_version} 已存在'}, status=status.HTTP_400_BAD_REQUEST
            )
        new_ds = EvalDataset.objects.create(
            organization=base.organization,
            name=base.name,
            version=new_version,
            description=request.data.get('description') or base.description,
            created_by=request.user,
        )
        for c in base.cases.all():
            EvalCase.objects.create(
                dataset=new_ds,
                code=c.code or f'case-{c.id}',
                input_text=c.input_text,
                expected=c.expected,
                is_edge=c.is_edge,
                meta=c.meta,
            )
        return Response(EvalDatasetSerializer(new_ds).data, status=status.HTTP_201_CREATED)

    @staticmethod
    def _next_version(base):
        """同 (organization, name) 下最大尾随数字版本号 +1（v1→v2）；非数字版本回退 {version}-v2。"""
        siblings = EvalDataset.objects.filter(
            organization=base.organization, name=base.name
        ).values_list('version', flat=True)
        max_n = 0
        for v in siblings:
            m = re.search(r'(\d+)', str(v))
            if m:
                max_n = max(max_n, int(m.group(1)))
        return f'v{max_n + 1}' if max_n else f'{base.version}-v2'

    @action(detail=False, methods=['get'])
    def diff(self, request):
        """A3 数据集 Diff：对比 base/target 两个数据集（同租户）的用例级差异。

        query: ?base=<id>&target=<id>
        按 case.code 对应（空 code 派生 case-<id>），返回 added/removed/changed/unchanged
        及每条 changed 的字段级差异（input_text/expected/is_edge）。严格租户隔离（他租户 → 404）。
        """
        base_id = request.query_params.get('base')
        target_id = request.query_params.get('target')
        if not base_id or not target_id:
            return Response(
                {'detail': '需提供 base 与 target 数据集 id'}, status=status.HTTP_400_BAD_REQUEST
            )
        org = request.user.organization
        base = EvalDataset.objects.filter(id=base_id, organization=org).first()
        target = EvalDataset.objects.filter(id=target_id, organization=org).first()
        if not base or not target:
            return Response(
                {'detail': '数据集不存在或不属于本租户'}, status=status.HTTP_404_NOT_FOUND
            )

        def key(c):
            return c.code or f'case-{c.id}'

        base_map = {key(c): c for c in base.cases.all()}
        target_map = {key(c): c for c in target.cases.all()}
        added, removed, changed, unchanged = [], [], [], []
        for k, tc in target_map.items():
            if k not in base_map:
                added.append({'code': k, 'input_text': tc.input_text, 'expected': tc.expected})
            else:
                bc = base_map[k]
                diffs = {}
                if bc.input_text != tc.input_text:
                    diffs['input_text'] = {'base': bc.input_text, 'target': tc.input_text}
                if bc.expected != tc.expected:
                    diffs['expected'] = {'base': bc.expected, 'target': tc.expected}
                if bc.is_edge != tc.is_edge:
                    diffs['is_edge'] = {'base': bc.is_edge, 'target': tc.is_edge}
                if diffs:
                    changed.append({'code': k, 'diffs': diffs})
                else:
                    unchanged.append({'code': k})
        for k, bc in base_map.items():
            if k not in target_map:
                removed.append({'code': k, 'input_text': bc.input_text, 'expected': bc.expected})
        return Response({
            'base': {'id': base.id, 'name': base.name, 'version': base.version, 'case_count': len(base_map)},
            'target': {'id': target.id, 'name': target.name, 'version': target.version, 'case_count': len(target_map)},
            'summary': {
                'added': len(added), 'removed': len(removed),
                'changed': len(changed), 'unchanged': len(unchanged),
            },
            'added': added, 'removed': removed, 'changed': changed, 'unchanged': unchanged,
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def generate_cases(self, request, pk=None):
        """B1 用例生成 Agent：需求/接口描述 → 稳定中间格式 EvalCase，批量写入本数据集。

        body: {"req_text": "...", "mode": "offline"|"llm" 默认 offline}
        - offline：零外送、确定性启发式；
        - llm：调用本租户激活的 AIModelConfig.for_tenant(org) 生成更丰富用例，
               失败自动降级 offline（数据不出域）。
        生成后可直接经 EvalRunViewSet.run 复用执行设施（B2）批量评测。
        """
        dataset = self.get_object()
        req_text = (request.data.get('req_text') or '').strip()
        if not req_text:
            return Response(
                {'detail': 'req_text 不能为空'}, status=status.HTTP_400_BAD_REQUEST
            )
        mode = request.data.get('mode') or 'offline'

        llm_config = None
        call_fn = None
        if mode == 'llm':
            from apps.requirement_analysis.models import AIModelConfig
            llm_config = AIModelConfig.for_tenant(dataset.organization)
            if llm_config:
                call_fn = agents.default_llm_call

        cases = agents.generate_cases(req_text, mode=mode, llm_config=llm_config, call_fn=call_fn)
        created = []
        for c in cases:
            ec = EvalCase.objects.create(
                dataset=dataset,
                code=c.get('code') or None,
                input_text=c['input_text'],
                expected=c.get('expected', ''),
                is_edge=bool(c.get('is_edge', False)),
                meta=c.get('meta', {}),
            )
            created.append(EvalCaseSerializer(ec).data)
        return Response({
            'generated_count': len(created),
            'mode': mode,
            'llm_used': bool(llm_config),
            'cases': created,
        }, status=status.HTTP_201_CREATED)


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
            # A2 数据不出域：LLM 裁判只取「本租户」激活的模型配置；
            # 无则 llm_config=None → 评估引擎确定性降级为启发式（零外送）。
            from apps.requirement_analysis.models import AIModelConfig
            llm_config = AIModelConfig.for_tenant(run.dataset.organization)

        try:
            summary = graders.grade_run(run, outputs, llm_config=llm_config)
        except Exception as exc:  # noqa: BLE001
            run.status = 'FAILED'
            run.save()
            return Response(
                {'detail': f'评测执行失败：{exc}'}, status=status.HTTP_400_BAD_REQUEST
            )

        run.status = 'DONE'
        run.model_config = llm_config  # A4 溯源：记录本次运行使用的模型
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

    @action(detail=False, methods=['get'])
    def leaderboard(self, request):
        """A4 全局/跨数据集榜单（租户内）：模型排名 + 数据集排名。

        复用 report 的聚合思路，但跨数据集横向比较：
        - model_ranking：按 model_config.model_name 分组（含「无 LLM/启发式」组），
          返回 avg_mean_score / avg_pass_rate / run_count，按分数降序；
        - dataset_ranking：按 dataset 分组，返回 avg_mean_score / run_count。
        只读、无副作用；严格按 request.user.organization 隔离。
        """
        org = request.user.organization
        runs = (
            EvalRun.objects.filter(organization=org, status='DONE')
            .select_related('grader', 'dataset', 'model_config')
            .order_by('created_at')
        )

        by_model = {}
        for r in runs:
            key = r.model_config.model_name if r.model_config else '（无 LLM / 启发式）'
            d = by_model.setdefault(key, {'run_count': 0, 'scores': [], 'pass_rates': []})
            d['run_count'] += 1
            if r.mean_score is not None:
                d['scores'].append(r.mean_score)
            if r.pass_rate is not None:
                d['pass_rates'].append(r.pass_rate)
        model_ranking = [
            {
                'model': k,
                'run_count': d['run_count'],
                'avg_mean_score': round(sum(d['scores']) / len(d['scores']), 3) if d['scores'] else None,
                'avg_pass_rate': round(sum(d['pass_rates']) / len(d['pass_rates']), 3) if d['pass_rates'] else None,
            }
            for k, d in by_model.items()
        ]
        model_ranking.sort(key=lambda x: (x['avg_mean_score'] or 0), reverse=True)

        by_ds = {}
        for r in runs:
            d = by_ds.setdefault(r.dataset_id, {'name': r.dataset.name, 'scores': [], 'run_count': 0})
            d['run_count'] += 1
            if r.mean_score is not None:
                d['scores'].append(r.mean_score)
        dataset_ranking = [
            {
                'dataset_id': did,
                'dataset_name': d['name'],
                'run_count': d['run_count'],
                'avg_mean_score': round(sum(d['scores']) / len(d['scores']), 3) if d['scores'] else None,
            }
            for did, d in by_ds.items()
        ]
        dataset_ranking.sort(key=lambda x: (x['avg_mean_score'] or 0), reverse=True)

        return Response({
            'model_ranking': model_ranking,
            'dataset_ranking': dataset_ranking,
            'total_runs': len(runs),
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def set_baseline(self, request, pk=None):
        """B4 标记当前 run 为其数据集的确定性基线（同 dataset 仅保留一个基线）。

        基线用于后续 compare（B4 劣化定位）与 gate（C1 回归拦截）。
        仅已完成(DONE)的运行可设为基线。
        """
        run = self.get_object()
        if run.status != 'DONE':
            return Response(
                {'detail': '仅已完成(DONE)的运行可设为基线'}, status=status.HTTP_400_BAD_REQUEST
            )
        EvalRun.objects.filter(dataset=run.dataset, is_baseline=True).update(is_baseline=False)
        run.is_baseline = True
        run.save()
        return Response(self.get_serializer(run).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def compare(self, request, pk=None):
        """B4 当前 run 与基线 run 对比（同 dataset 的 is_baseline 运行）。

        query: ?regress_delta=0.05
        返回各指标 current/baseline/delta 与是否 regressed。
        """
        run = self.get_object()
        baseline = EvalRun.objects.filter(dataset=run.dataset, is_baseline=True).first()
        if not baseline:
            return Response(
                {'detail': '该数据集尚未设置基线运行'}, status=status.HTTP_404_NOT_FOUND
            )
        regress_delta = float(request.query_params.get('regress_delta', 0.05))
        result = agents.compare_to_baseline(run, baseline, regress_delta=regress_delta)
        return Response({
            'current_run': run.id,
            'baseline_run': baseline.id,
            'baseline_mean_score': baseline.mean_score,
            **result,
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def analyze(self, request, pk=None):
        """B3 分析 Agent：跨用例模式识别（系统性失败定位），复用已有评分结果。

        返回 total 与 patterns（按 judge 类型归类的失败率 ≥0.5 的系统性风险）。
        """
        run = self.get_object()
        return Response(agents.analyze_run(run), status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def gate(self, request, pk=None):
        """C1 质量门禁：阈值 + 回归拦截，指出掉哪个指标（复用基线对比）。

        body: {"thresholds": {"mean_score": 0.7, "pass_rate": 0.8},
               "regress_delta": 0.05}
        基线自动取同 dataset 的 is_baseline 运行（若有）。返回 passed / 掉点明细。
        供 CI（C3 eval-gate.yml）调用做合并门禁。
        """
        run = self.get_object()
        thresholds = request.data.get('thresholds') or {}
        regress_delta = float(request.data.get('regress_delta', 0.05))
        baseline = EvalRun.objects.filter(dataset=run.dataset, is_baseline=True).first()
        result = agents.eval_gate(run, thresholds, baseline_run=baseline, regress_delta=regress_delta)
        return Response({
            'run': run.id,
            'baseline_run': baseline.id if baseline else None,
            **result,
        }, status=status.HTTP_200_OK)


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

    @action(detail=False, methods=['get'])
    def export(self, request):
        """C2 Trace 可观测导出：Langfuse / OTel 风格 JSON。

        query: ?run=<id>&case=<id>（可选，复用 get_queryset 过滤）。
        对齐 Langfuse ingestion 形态（trace + observations），便于导入外部可观测平台
        或本地回放（前端按 step 顺序渲染规划/工具/观察/输出）。
        租户隔离经 get_queryset 的 Org 过滤（非本租户 trace 不出现）。
        """
        traces = self.get_queryset()
        out = []
        for t in traces:
            out.append({
                'id': f'trace-{t.id}',
                'name': f'eval-run-{t.run_id}',
                'metadata': {
                    'run': t.run_id,
                    'case': t.case_id,
                    'dataset': t.run.dataset_id,
                    'status': t.status,
                    'total_latency_ms': t.total_latency_ms,
                },
                'timestamp': t.created_at.isoformat() if t.created_at else None,
                'observations': [
                    {
                        'id': f'step-{s.id}',
                        'type': s.step_type.lower(),
                        'name': s.name,
                        'input': s.input_data,
                        'output': s.output_data,
                        'metadata': {'latency_ms': s.latency_ms, 'error': s.error or None},
                    }
                    for s in t.steps.all()
                ],
            })
        return Response({
            'format': 'langfuse-otel-compatible',
            'trace_count': len(out),
            'traces': out,
        }, status=status.HTTP_200_OK)
