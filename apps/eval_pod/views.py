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

from . import graders, agents, runners, notifiers, cold_start, otel, edge_cases, judges
from .models import (
    EvalDataset, EvalCase, GraderConfig, EvalRun, EvalResult, EvalTrace,
    BenchmarkTemplate, EvalEloRating, EvalPlan, KnowledgeDoc, EvalSchedule,
    SkillVersion, EdgeCaseRule, JudgeStrengthRecord,
)
from .serializers import (
    EvalCaseSerializer,
    EvalDatasetSerializer,
    EvalRunSerializer,
    EvalResultSerializer,
    EvalTraceSerializer,
    EvalPlanSerializer,
    KnowledgeDocSerializer,
    EvalScheduleSerializer,
    SkillVersionSerializer, EdgeCaseRuleSerializer,
    GraderConfigSerializer, JudgeStrengthRecordSerializer,
)


def _report_enrichment(runs):
    """E4 看板富化：校准卡（预测分→实际通过率）+ 成功率热力图（模型×场景）。

    纯只读聚合，不触外部依赖。runs 为 EvalRun queryset（已 DONE）。
    """
    results = []
    for r in runs:
        model = r.model_config.model_name if r.model_config else '（无 LLM / 启发式）'
        for res in r.results.all():
            results.append({
                'score': res.score, 'passed': res.passed,
                'is_edge': res.case.is_edge, 'model': model,
            })
    # 校准卡：按分数分桶，统计实际通过率
    buckets = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)]
    calibration = []
    for lo, hi in buckets:
        grp = [x for x in results if lo <= (x['score'] or 0) < hi]
        if grp:
            calibration.append({
                'score_range': f'{lo:.1f}-{hi:.1f}',
                'count': len(grp),
                'actual_pass_rate': round(sum(1 for x in grp if x['passed']) / len(grp), 3),
            })
    # 热力图：模型 × 场景（边缘 / 常规）成功率
    heat = {}
    for x in results:
        d = heat.setdefault(x['model'], {'edge': [0, 0], 'normal': [0, 0]})
        cell = 'edge' if x['is_edge'] else 'normal'
        d[cell][0] += 1
        if x['passed']:
            d[cell][1] += 1
    heatmap = []
    for model, d in heat.items():
        heatmap.append({
            'model': model,
            'edge_pass_rate': round(d['edge'][1] / d['edge'][0], 3) if d['edge'][0] else None,
            'normal_pass_rate': round(d['normal'][1] / d['normal'][0], 3) if d['normal'][0] else None,
        })
    return calibration, heatmap


def build_layered_report(run):
    """P3-17 分层报告产物：L0 总览 + L1 分类 + L2 逐用例失败 TopN。

    纯只读，从 run.results 实时聚合（零外送、与落库一致）。
    - L0：run 级总览（状态 / 计数 / 各维度通过率 / 红线命中）；
    - L1：按用例角色(case_role) / 边缘(is_edge) / 评分器(judge) 三维分类，每维
          给出 count/passed/failed/pass_rate；
    - L2：失败用例按 score 升序（最差在前）输出 TopN（默认 50），供快速归因。
    用于 run/dataset 报告端点，前端按层展示（解决"非技术同事看不懂评测结论"）。
    """
    results = list(run.results.select_related('case').all())
    total = len(results)
    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed]
    mean_score = round(sum(r.score for r in results) / total, 3) if total else None
    pass_rate = round(len(passed) / total, 3) if total else None

    def _grp(key_fn):
        groups = {}
        for r in results:
            k = key_fn(r)
            g = groups.setdefault(k, {'count': 0, 'passed': 0})
            g['count'] += 1
            if r.passed:
                g['passed'] += 1
        for k, g in groups.items():
            g['failed'] = g['count'] - g['passed']
            g['pass_rate'] = round(g['passed'] / g['count'], 3) if g['count'] else None
        return groups

    by_role = _grp(lambda r: getattr(r.case, 'case_role', 'CAPABILITY'))
    by_edge = _grp(lambda r: 'edge' if r.case.is_edge else 'normal')
    by_judge = _grp(lambda r: r.judge)

    # L2：失败 TopN（按 score 升序，最差在前；平分按 id 稳定排）
    TOP_N = 50
    failed_sorted = sorted(failed, key=lambda r: (r.score, r.id))
    failed_top = [{
        'case_id': r.case_id,
        'code': r.case.code,
        'input_text': r.case.input_text,
        'expected': r.case.expected,
        'score': r.score,
        'passed': r.passed,
        'judge': r.judge,
        'reason': r.reason,
        'red_flags': r.red_flags or [],
        'faithfulness_score': r.faithfulness_score,
        'confidence': r.confidence,
    } for r in failed_sorted[:TOP_N]]

    red_line_hits = sum(1 for r in results if r.red_flags)

    l0 = {
        'status': run.status,
        'is_baseline': run.is_baseline,
        'model_name': (
            run.model_config.model_name if run.model_config
            else '（无 LLM / 启发式）'
        ),
        'total': total,
        'passed': len(passed),
        'failed': len(failed),
        'mean_score': mean_score,
        'pass_rate': pass_rate,
        'edge_pass_rate': run.edge_pass_rate,
        'capability_pass_rate': run.capability_pass_rate,
        'regression_pass_rate': run.regression_pass_rate,
        'pass_k_rate': run.pass_k_rate,
        'red_line_hits': red_line_hits,
    }
    return {
        'run_id': run.id,
        'L0': l0,
        'L1': {
            'by_role': by_role,
            'by_edge': by_edge,
            'by_judge': by_judge,
        },
        'L2': {
            'failed_count': len(failed),
            'limit': TOP_N,
            'failed': failed_top,
        },
    }


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
            # E4：校准卡（预测分 vs 实际通过率）+ 热力图（模型 × 场景）+ Elo
            calibration, heatmap = _report_enrichment(runs)
        else:
            latest = best = worst = None
            avg_mean = avg_pass = None
            grader_breakdown = []
            calibration, heatmap = [], []
        # E4：组织级 Elo 排名
        _, org_ratings = agents.recompute_elo(request.user.organization)
        elo_ranking = [
            {'model_name': m, 'rating': rt}
            for m, rt in sorted(org_ratings.items(), key=lambda kv: kv[1], reverse=True)
        ]
        return Response({
            'dataset': EvalDatasetSerializer(dataset).data,
            'total_runs': total,
            'latest': latest,
            'best': best,
            'worst': worst,
            'avg_mean_score': avg_mean,
            'avg_pass_rate': avg_pass,
            'grader_breakdown': grader_breakdown,
            'calibration': calibration,
            'heatmap': heatmap,
            'elo_ranking': elo_ranking,
            'saturation': agents.dataset_saturation(dataset),
            'runs': runs_data,
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def report_layered(self, request, pk=None):
        """P3-17 分层报告产物：取本数据集最近一次 DONE 运行，输出 L0/L1/L2 分层结构。

        区别于 report（全运行趋势/聚合），本端点聚焦「单一运行的分层结论」，
        直接给出可下钻的 L0 总览 + L1 分类（角色/边缘/评分器）+ L2 失败 TopN，
        便于非技术同事一眼看懂本次评测成败分布。若数据集尚无 DONE 运行，
        返回空结构（L0=None）。租户隔离经 _EvalBase（他租户数据集 → 404）。
        """
        dataset = self.get_object()
        latest = EvalRun.objects.filter(
            dataset=dataset, status='DONE'
        ).order_by('-created_at').first()
        if latest is None:
            return Response({
                'dataset': EvalDatasetSerializer(dataset).data,
                'run_id': None,
                'L0': None, 'L1': None, 'L2': None,
            }, status=status.HTTP_200_OK)
        return Response({
            'dataset': EvalDatasetSerializer(dataset).data,
            **build_layered_report(latest),
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

        # P3-13：知识中枢 RAG 上下文（可选）
        knowledge_ids = request.data.get('knowledge_ids') or None
        if knowledge_ids:
            knowledge_ids = [int(x) for x in knowledge_ids]

        cases = agents.generate_cases(
            req_text, mode=mode, llm_config=llm_config, call_fn=call_fn,
            knowledge_ids=knowledge_ids, org=dataset.organization,
        )
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

    @action(detail=False, methods=['post'])
    def from_template(self, request):
        """E7 基于标准 Benchmark 模板生成数据集 + 用例骨架。

        body: {"key": "tau-bench", "name": "<可选>", "version": "<可选>"}
        模板来源：平台级目录（organization=None，由 ensure_benchmark_catalog 播种）
        + 本租户私有模板。生成的 EvalDataset 归属当前租户，可直接进入 run 评测。
        专测 Pass^k 的模板（如 τ-bench）在生成时一并提示 measures_pass_k。
        """
        from django.db.models import Q

        from .benchmarks import ensure_benchmark_catalog

        ensure_benchmark_catalog()
        key = (request.data.get('key') or '').strip()
        if not key:
            return Response(
                {'detail': '需提供模板 key'}, status=status.HTTP_400_BAD_REQUEST
            )
        org = request.user.organization
        tpl = BenchmarkTemplate.objects.filter(
            (Q(organization__isnull=True) | Q(organization=org)) & Q(key=key)
        ).first()
        if not tpl:
            return Response(
                {'detail': f'模板 {key} 不存在'}, status=status.HTTP_404_NOT_FOUND
            )

        name = request.data.get('name') or f'{tpl.name}'
        version = request.data.get('version') or 'v1'
        if EvalDataset.objects.filter(organization=org, name=name, version=version).exists():
            return Response(
                {'detail': f'数据集 {name}@{version} 已存在'}, status=status.HTTP_400_BAD_REQUEST
            )
        ds = EvalDataset.objects.create(
            organization=org, name=name, version=version,
            description=tpl.description,
            created_by=request.user,
        )
        created = []
        for sk in tpl.case_skeleton:
            ec = EvalCase.objects.create(
                dataset=ds,
                input_text=sk.get('input_text', ''),
                expected=sk.get('expected', ''),
                is_edge=bool(sk.get('is_edge', False)),
                meta=sk.get('meta', {}),
            )
            created.append(EvalCaseSerializer(ec).data)
        return Response({
            'dataset': EvalDatasetSerializer(ds).data,
            'source': tpl.source,
            'measures_pass_k': tpl.measures_pass_k,
            'dimensions': tpl.dimensions,
            'generated_cases': len(created),
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
        """执行一次评测：body 传 {"outputs": {case_id: output_text | [out,...] | {output,tool_outputs}}}。

        升级（E1/E2）：
        - judge_configs: 评分器配置 id 列表（多裁判 PoLL）；缺省 [run.grader]。
        - agg_method: TRIMMED_MEAN / MAJORITY / PANEL_DISAGREE（默认截尾均值）。
        - repeat_k: 可靠性重复次数（Pass^k），覆盖 run.repeat_k。
        评分器为 LLM_JUDGE 时，复用平台激活的 AIModelConfig；无配置或失败则
        确定性降级（HEURISTIC），绝不外送未配置租户的数据。
        """
        run = self.get_object()
        outputs = request.data.get('outputs', {}) or {}

        # —— E2：可靠性重复次数（覆盖）——
        repeat_k = request.data.get('repeat_k')
        if repeat_k is not None:
            run.repeat_k = max(int(repeat_k), 1)
        # —— P3-3：置信度门阈值（覆盖，持久化到 run）——
        mc = request.data.get('min_confidence')
        if mc is not None:
            run.min_confidence = float(mc)
        # —— E1：多裁判配置 ——
        judge_ids = request.data.get('judge_configs') or []
        agg_method = request.data.get('agg_method') or 'TRIMMED_MEAN'
        judge_configs = []
        if judge_ids:
            judge_configs = list(
                GraderConfig.objects.filter(id__in=judge_ids, organization=run.organization)
            )
        if not judge_configs:
            judge_configs = None  # grade_run 退化为 [run.grader]

        llm_config = None
        if run.grader.grader_type == 'LLM_JUDGE':
            # A2 数据不出域：LLM 裁判只取「本租户」激活的模型配置；
            # 无则 llm_config=None → 评估引擎确定性降级为启发式（零外送）。
            from apps.requirement_analysis.models import AIModelConfig
            llm_config = AIModelConfig.for_tenant(run.dataset.organization)

        # 单一事实来源：复用 runners.execute_run（含 grade_run + _persist_run_summary），
        # 不再内联重写评分/落库逻辑，避免与 harness / 调度路径各自维护导致漂移（P3 根基加固）。
        from . import runners
        skill_version = SkillVersion.active_for(run.organization, 'eval-flow')
        try:
            runners.execute_run(
                run, outputs, llm_config=llm_config,
                judge_configs=judge_configs, agg_method=agg_method,
                repeat_k=run.repeat_k, min_confidence=run.min_confidence,
                skill_version=skill_version,
            )
        except Exception as exc:  # noqa: BLE001
            run.status = 'FAILED'
            run.save()
            return Response(
                {'detail': f'评测执行失败：{exc}'}, status=status.HTTP_400_BAD_REQUEST
            )

        # P3-5 冷启动基线策略：数据集首个 DONE 运行自动设为基线（幂等），
        # 使冷启动租户也能立即获得「首个运行即基线」的回归对比锚点（无需手工 set_baseline）。
        if not EvalRun.objects.filter(dataset=run.dataset, is_baseline=True).exists():
            run.is_baseline = True
            run.save(update_fields=['is_baseline'])

        return Response(self.get_serializer(run).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def run_harness(self, request, pk=None):
        """P3-6 E2E Harness：经 MockHarness / RealHarness 端到端驱动被测 agent 并评测。

        body: {"harness": "mock"|"real", "mock_mode": "expected"|"echo"|"fail",
               "agent_config_id": <int 可选，real 模式>}
        - mock：确定性零外送（三种模式），适合 CI 冒烟与回归基线。
        - real：HTTP 无状态无法注入 agent_fn，改用 AIModelConfig 同步调用：
          优先 agent_config_id，否则取本租户激活配置（A2 数据不出域）；
          无配置 → 400（绝不外送租户数据到未配置端点）。
        返回 run 序列化（含聚合指标），并落 EvalTrace/EvalTraceStep（M4 归因）。
        """
        from .harness import MockHarness, RealHarness
        from . import runners

        run = self.get_object()
        harness_kind = (request.data.get('harness') or 'mock').lower()
        mock_mode = (request.data.get('mock_mode') or 'expected').lower()

        llm_config = None
        harness = None
        try:
            if harness_kind == 'mock':
                harness = MockHarness(mock_mode=mock_mode)
            elif harness_kind == 'real':
                from apps.requirement_analysis.models import AIModelConfig
                config = None
                agent_config_id = request.data.get('agent_config_id')
                if agent_config_id is not None:
                    config = AIModelConfig.objects.filter(
                        id=agent_config_id, organization=run.organization
                    ).first()
                if config is None:
                    config = AIModelConfig.for_tenant(run.dataset.organization)
                if config is None:
                    return Response(
                        {'detail': 'real 模式需要配置被评测 agent'
                                   '（agent_config_id 或本租户激活的 AIModelConfig）'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                # real 评测若评分器为 LLM_JUDGE，裁判同样仅取本租户模型（数据不出域）
                if run.grader.grader_type == 'LLM_JUDGE':
                    llm_config = config
                harness = RealHarness(config=config)
            else:
                return Response(
                    {'detail': "harness 必须为 'mock' 或 'real'"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            run.repeat_k = max(int(request.data.get('repeat_k', run.repeat_k) or 1), 1)
            mc = request.data.get('min_confidence')
            if mc is not None:
                run.min_confidence = float(mc)
            run.save(update_fields=['repeat_k', 'min_confidence'])

            runners.execute_harness_run(
                run, harness, agent_fn=None, llm_config=llm_config,
                agg_method=request.data.get('agg_method') or 'TRIMMED_MEAN',
                repeat_k=run.repeat_k, min_confidence=run.min_confidence,
            )
        except Exception as exc:  # noqa: BLE001
            run.status = 'FAILED'
            run.save()
            return Response(
                {'detail': f'harness 评测执行失败：{exc}'},
                status=status.HTTP_400_BAD_REQUEST,
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
            d = by_model.setdefault(
                key, {'run_count': 0, 'scores': [], 'pass_rates': [],
                      'cost_tokens': [], 'cost_calls': []}
            )
            d['run_count'] += 1
            if r.mean_score is not None:
                d['scores'].append(r.mean_score)
            if r.pass_rate is not None:
                d['pass_rates'].append(r.pass_rate)
            if r.cost_tokens_total is not None:
                d['cost_tokens'].append(r.cost_tokens_total)
            if r.cost_calls_total is not None:
                d['cost_calls'].append(r.cost_calls_total)
        model_ranking = [
            {
                'model': k,
                'run_count': d['run_count'],
                'avg_mean_score': round(sum(d['scores']) / len(d['scores']), 3) if d['scores'] else None,
                'avg_pass_rate': round(sum(d['pass_rates']) / len(d['pass_rates']), 3) if d['pass_rates'] else None,
                'avg_cost_tokens': round(sum(d['cost_tokens']) / len(d['cost_tokens']), 3) if d['cost_tokens'] else None,
                'avg_cost_calls': round(sum(d['cost_calls']) / len(d['cost_calls']), 3) if d['cost_calls'] else None,
            }
            for k, d in by_model.items()
        ]
        # P3-2：支持按成本升序排序（?sort=cost，越便宜越靠前）
        if request.query_params.get('sort') == 'cost':
            model_ranking.sort(key=lambda x: (x['avg_cost_tokens'] or float('inf')))
        else:
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

        resp = {
            'model_ranking': model_ranking,
            'dataset_ranking': dataset_ranking,
            'total_runs': len(runs),
        }
        # E3：组织级 Elo 排名（?with_elo=1）
        if request.query_params.get('with_elo') == '1':
            _, org_ratings = agents.recompute_elo(org)
            elo_ranking = [
                {'model_name': m, 'rating': rt}
                for m, rt in sorted(org_ratings.items(), key=lambda kv: kv[1], reverse=True)
            ]
            resp['elo_ranking'] = elo_ranking
        return Response(resp, status=status.HTTP_200_OK)

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
        aux_thresholds = request.data.get('aux_thresholds') or {}
        aux_metrics = request.data.get('aux_metrics') or None
        regress_delta = float(request.data.get('regress_delta', 0.05))
        mc = request.data.get('min_confidence')
        min_confidence = float(mc) if mc is not None else None
        baseline = EvalRun.objects.filter(dataset=run.dataset, is_baseline=True).first()
        result = agents.eval_gate(
            run, thresholds, aux_thresholds=aux_thresholds, baseline_run=baseline,
            regress_delta=regress_delta, min_confidence=min_confidence,
            aux_metrics=aux_metrics,
        )
        return Response({
            'run': run.id,
            'baseline_run': baseline.id if baseline else None,
            **result,
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def elo(self, request, pk=None):
        """E3 Pairwise + Elo：重算并返回本运行所属数据集的模型 Elo 排名 + 本运行模型评分。

        幂等：基于同数据集全部 DONE runs 做 round-robin 两两比较（按 mean_score 定胜负），
        用标准 Elo 公式更新；位置交换消偏（同对 (A,B) 与 (B,A) 对称）。
        """
        run = self.get_object()
        org = request.user.organization
        _, org_ratings = agents.recompute_elo(org, dataset=run.dataset)
        rows = (
            EvalEloRating.objects.filter(organization=org, dataset=run.dataset)
            .select_related('dataset').order_by('-rating')
        )
        ranking = [
            {
                'model_name': r.model_name,
                'rating': r.rating,
                'dataset': r.dataset.name if r.dataset else None,
            }
            for r in rows
        ]
        my_model = run.model_config.model_name if run.model_config else '（无 LLM / 启发式）'
        return Response({
            'dataset': run.dataset.name,
            'elo_ranking': ranking,
            'my_model': my_model,
            'my_rating': org_ratings.get(my_model),
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def case_traces(self, request, pk=None):
        """P3-15 辅助：返回本运行各用例结果 + Trace 可用性，便于「失败 case 回放」聚焦。

        返回 {run, total, failed_count, cases:[{case_id, code, input_text, expected,
        passed, score, judge, red_flags, has_trace, trace_id, trace_status}]}。
        cases 按「未通过优先」排序，方便快速定位需回放的失败用例。
        """
        run = self.get_object()
        results = (
            EvalResult.objects.filter(run=run)
            .select_related('case').order_by('case_id')
        )
        trace_map = {
            t.case_id: t for t in EvalTrace.objects.filter(run=run).only('id', 'case_id', 'status')
        }
        cases = []
        failed = 0
        for r in results:
            has_trace = r.case_id in trace_map
            passed = bool(r.passed)
            if not passed:
                failed += 1
            cases.append({
                'case_id': r.case_id,
                'code': r.case.code,
                'input_text': r.case.input_text,
                'expected': r.case.expected,
                'passed': passed,
                'score': r.score,
                'judge': r.judge,
                'red_flags': r.red_flags or [],
                'has_trace': has_trace,
                'trace_id': trace_map[r.case_id].id if has_trace else None,
                'trace_status': trace_map[r.case_id].status if has_trace else None,
            })
        # 未通过 + 有 trace 的排前
        cases.sort(key=lambda c: (not (not c['passed'] and c['has_trace']), c['case_id']))
        return Response({
            'run': run.id,
            'total': len(cases),
            'failed_count': failed,
            'cases': cases,
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def report_layered(self, request, pk=None):
        """P3-17 分层报告产物：本运行 L0 总览 + L1 分类 + L2 逐用例失败 TopN。

        纯只读，从 run.results 实时聚合（零外送、与落库一致）；
        前端按层展示（L0 概览 / L1 角色·边缘·评分器分组 / L2 失败 TopN）。
        租户隔离经 _EvalBase（他租户运行 → 404）。
        """
        run = self.get_object()
        return Response(build_layered_report(run), status=status.HTTP_200_OK)


class KnowledgeDocViewSet(_EvalBase, viewsets.ModelViewSet):
    """P3-13 知识中枢：租户内知识库 CRUD + RAG 检索。

    - content 写入即自动分块（KnowledgeDoc.save → agents.build_chunks），chunks 只读；
    - search：POST {query, top_k?, knowledge_ids?} → 词法重叠排序的命中片段（零外送）。
    严格租户隔离（org_field='organization'）。
    """

    queryset = KnowledgeDoc.objects.all()
    serializer_class = KnowledgeDocSerializer

    @action(detail=False, methods=['post'])
    def search(self, request):
        """RAG 检索：在 org 的知识文档 chunks 上做词法重叠排序，返回 top_k 命中。

        body: {"query": "...", "top_k": 4, "knowledge_ids": [1,2] 可选}
        返回 {query, count, hits:[{doc_id,doc_title,source_type,chunk_idx,text,score}]}
        """
        query = (request.data.get('query') or '').strip()
        if not query:
            return Response(
                {'detail': 'query 不能为空'}, status=status.HTTP_400_BAD_REQUEST
            )
        top_k = int(request.data.get('top_k') or 4)
        knowledge_ids = request.data.get('knowledge_ids') or None
        if knowledge_ids:
            knowledge_ids = [int(x) for x in knowledge_ids]
        hits = agents.retrieve_knowledge(
            query, request.user.organization, top_k=top_k, knowledge_ids=knowledge_ids
        )
        return Response({'query': query, 'count': len(hits), 'hits': hits})


class EvalPlanViewSet(_EvalBase, viewsets.ModelViewSet):
    """P3-14 Copilot 评测方案：自然语言 → 结构化方案草稿 → 确认落地为运行。

    - design：调 agents.plan_eval（离线启发式 / 可选 LLM 降级），存 EvalPlan(DRAFT)。
    - confirm：为每个 dataset 创建 EvalRun（复用 run 设施），状态 PENDING，待用户喂入 outputs。
    严格租户隔离（org_field='organization'）。
    """

    queryset = EvalPlan.objects.all()
    serializer_class = EvalPlanSerializer

    @action(detail=False, methods=['post'])
    def design(self, request):
        """Copilot：自然语言 → 结构化评测方案（并存草稿）。

        body: {"req_text": "...", "mode": "offline"|"llm" 默认 offline}
        - offline：确定性规则模板，零外送；
        - llm：调用本租户激活模型生成，失败自动降级 offline（数据不出域）。
        返回 {plan_id, title, summary, dataset_ids, metrics, gate_thresholds,
              baseline_run_id, repeat_k, mode, llm_used}。
        """
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
            llm_config = AIModelConfig.for_tenant(request.user.organization)
            if llm_config:
                call_fn = agents.default_llm_call

        plan = agents.plan_eval(
            req_text, request.user.organization,
            mode=mode, llm_config=llm_config, call_fn=call_fn,
        )
        ep = EvalPlan.objects.create(
            organization=request.user.organization,
            title=plan.get('title', '评测方案'),
            req_text=req_text,
            plan_json=plan,
            status='DRAFT',
            created_by=request.user,
        )
        return Response(
            {'plan_id': ep.id, **plan}, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """确认方案 → 为每个 dataset 创建 EvalRun（复用 run 设施），状态 PENDING。

        指标的每个 grader_type 解析为 GraderConfig（组织内查重，缺失自动建 auto-<type>）；
        首个作为 run.grader，其余记入 plan_json.resolved_grader_ids 供执行时作多裁判。
        返回 {plan_id, run_ids, status}。严格租户隔离。
        """
        plan = self.get_object()
        if plan.status == 'CONFIRMED':
            return Response(
                {'detail': '该方案已确认，不可重复落地'}, status=status.HTTP_400_BAD_REQUEST
            )
        pj = plan.plan_json or {}
        org = request.user.organization
        dataset_ids = [int(x) for x in (pj.get('dataset_ids') or [])]
        metric_types = [str(x) for x in (pj.get('metrics') or [])]
        repeat_k = int(pj.get('repeat_k') or 1)

        # 解析 grader（查重 + 缺失自建）
        resolved_grader_ids = []
        grader_cfgs = []
        for gt in metric_types or ['LLM_JUDGE']:
            gc = GraderConfig.objects.filter(organization=org, grader_type=gt).first()
            if not gc:
                gc = GraderConfig.objects.create(
                    organization=org, name=f'auto-{gt}-{org.code}', grader_type=gt,
                    created_by=request.user,
                )
            grader_cfgs.append(gc)
            resolved_grader_ids.append(gc.id)

        created_runs = []
        for ds_id in dataset_ids:
            ds = EvalDataset.objects.filter(id=ds_id, organization=org).first()
            if not ds:
                continue
            run = EvalRun.objects.create(
                organization=org,
                dataset=ds,
                grader=grader_cfgs[0],
                repeat_k=repeat_k,
                created_by=request.user,
            )
            created_runs.append(run.id)

        plan.plan_json = {**pj, 'resolved_grader_ids': resolved_grader_ids}
        plan.resolved_run_ids = created_runs
        plan.status = 'CONFIRMED'
        plan.save()
        return Response(
            {
                'plan_id': plan.id,
                'run_ids': created_runs,
                'status': 'CONFIRMED',
                'grader_ids': resolved_grader_ids,
            },
            status=status.HTTP_200_OK,
        )


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

    @action(detail=False, methods=['get'])
    def playback(self, request):
        """P3-15 失败 case Trace 回放：返回单条 trace 的逐步重放结构（对标 UI 视频回放）。

        query: ?run=<id>&case=<id>（复用 get_queryset 过滤，取最新一条 trace）。
        返回 steps 已按 step_index 升序，并富化：cumulative_ms（累计时延）、type_label、
        is_error、is_failure_point（失败归因高亮：错误步骤 / 末步且 trace 失败）。
        租户隔离经 get_queryset 的 Org 过滤。
        """
        trace = self.get_queryset().order_by('-created_at').first()
        if not trace:
            return Response({'detail': '未找到对应 Trace'}, status=status.HTTP_404_NOT_FOUND)
        return Response(_trace_replay(trace), status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def replay(self, request, pk=None):
        """P3-15 逐条 trace 重放（按 trace id 直接定位）。"""
        trace = self.get_object()
        return Response(_trace_replay(trace), status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def ingest(self, request):
        """P3-8 OTel 回流：接收 OTLP/JSON trace（或简化结构）落库为 EvalTrace。

        与 `export`（内部→外部）互补，形成 trace 导入闭环（对标 One-Eval / Opik）。

        body: {"run":<id>, "case":<id>, "payload":<OTLP/JSON 或 {"spans":[...]} 或 裸列表>}
              （兼容 "otlp" / "spans" 作为 payload 的同义键）
        返回: {"trace_id", "status", "total_latency_ms", "step_count"}

        租户隔离（严格 fail-closed）：
          - run 经 scoped_get（直接 organization 字段）→ 跨租户 404；
          - case 经 scoped_get(org_field='dataset__organization') → 跨租户 404；
          - case.dataset_id 必须等于 run.dataset_id，否则 400（防止把任意 case 的轨迹
            挂到 run 上造成评测污染 / 「借壳」注入）。
        本动作只做「写」，不调用任何 LLM（零外送）。
        """
        run_id = request.data.get('run')
        case_id = request.data.get('case')
        payload = (
            request.data.get('payload')
            or request.data.get('otlp')
            or request.data.get('spans')
        )
        if run_id is None or case_id is None or payload is None:
            return Response(
                {'detail': 'run / case / payload(otlp) 均为必填'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # —— 租户校验：run（直接 organization）——
        try:
            run = self.scoped_get(EvalRun, id=run_id)
        except EvalRun.DoesNotExist:
            return Response(
                {'detail': '评测运行不存在或不在本租户'}, status=status.HTTP_404_NOT_FOUND
            )
        # —— 租户校验：case（经 dataset__organization 多跳）——
        try:
            case = self.scoped_get(EvalCase, org_field='dataset__organization', id=case_id)
        except EvalCase.DoesNotExist:
            return Response(
                {'detail': '用例不存在或不在本租户'}, status=status.HTTP_404_NOT_FOUND
            )
        # —— 归属校验：case 必须属于 run 的数据集 ——
        if case.dataset_id != run.dataset_id:
            return Response(
                {'detail': '用例不属于该运行的数据集，拒绝导入'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            trace = otel.ingest_otlp(run, case, payload)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                'trace_id': trace.id,
                'status': trace.status,
                'total_latency_ms': trace.total_latency_ms,
                'step_count': trace.steps.count(),
            },
            status=status.HTTP_201_CREATED,
        )


def _trace_replay(trace):
    """将 EvalTrace 转为回放结构（步骤按序，富化时序与失败点）。"""
    _TYPE_LABEL = {
        'PLAN': '规划', 'TOOL': '工具调用', 'OBSERVE': '观察',
        'OUTPUT': '最终输出', 'ERROR': '错误',
    }
    steps = list(trace.steps.all().order_by('step_index'))
    cum = 0
    has_explicit_error = False
    enriched = []
    for s in steps:
        lat = s.latency_ms or 0
        cum += lat
        is_err = s.step_type == 'ERROR' or bool(s.error)
        if is_err:
            has_explicit_error = True
        enriched.append({
            'step_index': s.step_index,
            'step_type': s.step_type,
            'type_label': _TYPE_LABEL.get(s.step_type, s.step_type),
            'name': s.name,
            'input_data': s.input_data,
            'output_data': s.output_data,
            'latency_ms': s.latency_ms,
            'cumulative_ms': cum,
            'error': s.error or None,
            'is_error': is_err,
            'is_failure_point': False,  # 失败点标记在下方统一判定
        })
    # 失败点：① 显式错误步骤；② 无显式错误但 trace 整体失败 → 末步高亮
    if has_explicit_error:
        for st in enriched:
            if st['is_error']:
                st['is_failure_point'] = True
    elif trace.status == 'ERROR' and enriched:
        enriched[-1]['is_failure_point'] = True
    return {
        'trace_id': trace.id,
        'run': trace.run_id,
        'case': trace.case_id,
        'status': trace.status,
        'total_latency_ms': trace.total_latency_ms,
        'step_count': len(enriched),
        'steps': enriched,
    }


class EvalScheduleViewSet(_EvalBase, viewsets.ModelViewSet):
    """P3-16 定时评测调度 + IM 通知。

    - CRUD：调度定义数据化（DB 模型），create 经序列化器注入 organization/created_by；
      next_run_at 由 model.save 自动计算。
    - fire_now：立即对该调度触发一次评测运行（不经 tick 的到期判断），返回运行摘要。
    - notify_test：向给定渠道发送一条测试通知，校验 webhook/签名是否可用。
    严格租户隔离（org_field='organization'）。
    """

    queryset = EvalSchedule.objects.all()
    serializer_class = EvalScheduleSerializer

    @action(detail=True, methods=['post'])
    def fire_now(self, request, pk=None):
        """立即执行一次调度（跳过到期判断），返回本次运行的摘要。"""
        sched = self.get_object()
        try:
            run = runners.run_scheduled_eval(sched)
        except Exception as exc:  # noqa: BLE001
            return Response(
                {'detail': f'调度执行失败：{exc}'}, status=status.HTTP_400_BAD_REQUEST
            )
        sched.last_run_at = timezone.now()
        sched.last_run_id = run.id
        sched.last_status = 'OK'
        sched.last_error = ''
        sched.next_run_at = sched.compute_next_run(timezone.now())
        sched.save()
        return Response({
            'run_id': run.id,
            'status': run.status,
            'mean_score': run.mean_score,
            'pass_rate': run.pass_rate,
            'next_run_at': sched.next_run_at,
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def notify_test(self, request):
        """发送测试通知：body {"channels":[{type,webhook,secret?}]} 或 {"channel":{...}}。"""
        channels = request.data.get('channels') or []
        single = request.data.get('channel')
        if single:
            channels = [single]
        if not channels:
            return Response(
                {'detail': 'channels 不能为空'}, status=status.HTTP_400_BAD_REQUEST
            )
        results = notifiers.notify_im(
            channels, '评测平台通知测试', '这是一条来自评测平台的测试消息 ✅'
        )
        return Response({'results': results})


class SkillVersionViewSet(_EvalBase, viewsets.ModelViewSet):
    """P3-4 评测技能版本化。

    - CRUD：版本快照列表/详情（租户隔离，org_field='organization'）。
    - publish：发布新版本。body {skill_key, version?, content?, note?}；
      content 缺省则从磁盘 skills/<skill_key>/SKILL.md 快照；version 缺省自动建议。
      内容重复（同 hash）则拒绝重复发布（409）。
    - set_active：将某版本设为当前生效（同 scope+key 互斥）。
    - diff：与另一版本或磁盘当前内容做统一差异。
    - current：取某 skill_key 的当前生效版本。
    """

    queryset = SkillVersion.objects.all()
    serializer_class = SkillVersionSerializer

    @action(detail=False, methods=['post'])
    def publish(self, request):
        skill_key = (request.data.get('skill_key') or 'eval-flow').strip()
        content = request.data.get('content')
        if not content:
            content = SkillVersion.disk_content(skill_key)
        if not content:
            return Response(
                {'detail': f'未提供 content 且磁盘无 skills/{skill_key}/SKILL.md'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        content_hash = SkillVersion._hash(content)
        dup = SkillVersion.objects.filter(
            organization=request.user.organization, skill_key=skill_key,
            content_hash=content_hash,
        ).first()
        if dup:
            return Response(
                {'detail': f'该内容已存在于版本 {dup.version}，无需重复发布',
                 'exists_version': dup.version},
                status=status.HTTP_409_CONFLICT,
            )
        version = (request.data.get('version') or '').strip() or \
            SkillVersion.suggest_version(request.user.organization, skill_key)
        try:
            sv = SkillVersion.objects.create(
                organization=request.user.organization,
                skill_key=skill_key,
                version=version,
                content=content,
                content_hash=content_hash,
                note=request.data.get('note') or '',
                created_by=request.user,
            )
        except Exception as exc:  # noqa: BLE001  (unique_together 冲突等)
            return Response(
                {'detail': f'发布失败（版本号可能已存在）：{exc}'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(SkillVersionSerializer(sv).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def set_active(self, request, pk=None):
        sv = self.get_object()
        sv.set_active()
        return Response({'id': sv.id, 'skill_key': sv.skill_key,
                         'version': sv.version, 'is_active': sv.is_active})

    @action(detail=True, methods=['get'])
    def diff(self, request, pk=None):
        sv = self.get_object()
        other_id = request.query_params.get('other')
        if other_id == 'disk':
            other_content = SkillVersion.disk_content(sv.skill_key) or ''
            other_label = 'disk'
        else:
            other = SkillVersion.objects.filter(
                id=other_id, organization=sv.organization
            ).first()
            other_content = other.content if other else ''
            other_label = other.version if other else '?'
        import difflib
        diff = '\n'.join(difflib.unified_diff(
            other_content.splitlines(), sv.content.splitlines(),
            fromfile=f'{sv.skill_key}@{other_label}',
            tofile=f'{sv.skill_key}@{sv.version}',
            lineterm='',
        ))
        return Response({'from': other_label, 'to': sv.version, 'diff': diff})

    @action(detail=False, methods=['get'])
    def current(self, request):
        skill_key = request.query_params.get('skill_key') or 'eval-flow'
        sv = SkillVersion.active_for(request.user.organization, skill_key)
        if not sv:
            return Response({'detail': '当前无生效版本', 'skill_key': skill_key},
                            status=status.HTTP_404_NOT_FOUND)
        return Response(SkillVersionSerializer(sv).data)


class ColdStartViewSet(viewsets.ViewSet):
    """P3-5 冷启动标准：状态查询 + 默认评分器模板一键种子。

    - status：GET，返回当前租户冷启动状态（是否已有评分器/缺失模板/是否有基线/
      推荐默认门阈值）；前端据此展示首次运行引导。
    - apply：POST，幂等地把平台默认评分器模板种子到该租户（已存在同名模板跳过）。
    按当前用户所属租户作用域（数据不出域）；本视图不暴露跨租户资源，
    故无需 TenantAwareViewSetMixin 的 queryset 解析（避免非 Model ViewSet 取 queryset）。
    """

    permission_classes = [IsAuthenticated, HasTenantFeature]
    required_feature = FeatureCode.AGENT_EVAL

    @action(detail=False, methods=['get'])
    def status(self, request):
        return Response(
            cold_start.cold_start_status(request.user.organization),
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['post'])
    def apply(self, request):
        res = cold_start.apply_cold_start(
            request.user.organization, created_by=request.user
        )
        return Response(res, status=status.HTTP_200_OK)


class EdgeCaseRuleViewSet(_EvalBase, viewsets.ModelViewSet):
    """P3-9 边缘用例规则。

    - CRUD：规则列表/创建/更新/删除（租户隔离，org_field='organization'）。
      创建时 organization / created_by 由 perform_create 注入，请求体不写。
    - seed_defaults：POST，按租户幂等播种平台默认规则库（已存在同名 code 跳过），
      返回本租户全部规则；前端「一键应用默认规则」调用。
    - apply：POST，body {dataset_id, rule_ids?}；经 scoped_get(EvalDataset) 严格隔离，
      对数据集中的普通用例按（指定或全部启用的）规则派生边缘用例（is_edge=True，
      meta 标记来源），返回 {created, per_rule, skipped}。幂等（同 seed+rule 不重复）。
    """

    queryset = EdgeCaseRule.objects.all().order_by('id')
    serializer_class = EdgeCaseRuleSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.user.organization,
            created_by=self.request.user,
        )

    @action(detail=False, methods=['post'])
    def seed_defaults(self, request):
        """按租户幂等播种平台默认边缘用例规则，返回本租户全部规则。"""
        edge_cases.ensure_default_edge_rules(
            request.user.organization, created_by=request.user
        )
        rules = EdgeCaseRule.objects.filter(
            organization=request.user.organization
        ).order_by('id')
        return Response(
            EdgeCaseRuleSerializer(rules, many=True).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['post'])
    def apply(self, request):
        """对指定数据集生成边缘用例变体（租户隔离 + 幂等）。"""
        dataset_id = request.data.get('dataset_id')
        if not dataset_id:
            return Response(
                {'detail': '需提供 dataset_id'}, status=status.HTTP_400_BAD_REQUEST
            )
        # 严格隔离：数据集必须经当前租户作用域（org_field='organization'）
        try:
            dataset = self.scoped_get(EvalDataset, id=dataset_id)
        except EvalDataset.DoesNotExist:
            return Response(
                {'detail': '数据集不存在或越权'}, status=status.HTTP_404_NOT_FOUND
            )
        rule_ids = request.data.get('rule_ids') or None
        rules = EdgeCaseRule.objects.filter(
            organization=request.user.organization, enabled=True
        )
        if rule_ids:
            rules = rules.filter(id__in=rule_ids)
        rules = list(rules)
        if not rules:
            return Response(
                {'detail': '无可用的边缘用例规则（请先 seed_defaults 或创建规则）'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = edge_cases.apply_edge_rules(dataset, rules, org=request.user.organization)
        return Response(result, status=status.HTTP_200_OK)


class JudgeStrengthViewSet(_EvalBase, viewsets.ModelViewSet):
    """P3-11 评判模型强度自校准。

    - list：本租户历史校准记录（org_field='organization'，严格隔离）。
    - assess：POST，对当前租户激活的评判模型（AIModelConfig.for_tenant）跑金标准校准集
      （judges.assess_judge_strength），落一条 JudgeStrengthRecord 并返回。
      未配置评判模型 → 400。call_fn 由 agents.default_llm_call 提供（生产走本租户模型，
      数据不出域）；测试可注入（见 tests）。
    """

    queryset = JudgeStrengthRecord.objects.all().order_by('-created_at')
    serializer_class = JudgeStrengthRecordSerializer

    @action(detail=False, methods=['post'])
    def assess(self, request):
        from apps.requirement_analysis.models import AIModelConfig

        config = AIModelConfig.for_tenant(request.user.organization)
        if config is None:
            return Response(
                {'detail': '本租户未配置评判模型（AIModelConfig），无法校准裁判强度'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = judges.assess_judge_strength(
            llm_config=config, call_fn=agents.default_llm_call
        )
        if result is None:
            return Response(
                {'detail': '无法对评判模型进行校准（缺少可调用来源）'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        record = JudgeStrengthRecord.objects.create(
            organization=request.user.organization,
            model_name=config.model_name,
            strength_score=result['strength_score'],
            agreement=result['agreement'],
            sample_size=result['sample_size'],
        )
        return Response(
            JudgeStrengthRecordSerializer(record).data, status=status.HTTP_201_CREATED
        )
