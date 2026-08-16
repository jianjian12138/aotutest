"""
端到端演示命令：需求 → 生成 → 评测 → 门禁（路线三 · B1/B4/C1，全程离线零外送）。

运行：
    python manage.py demo_eval_flow
    python manage.py demo_eval_flow --thresholds-mean-score 0.5 --thresholds-pass-rate 0.5
    python manage.py demo_eval_flow --org-code my-org --clean   # 用指定租户并重建演示数据

演示在「独立演示租户」内完成，默认幂等（同 code/name 复用，重复运行不污染）。
不依赖任何外部 LLM：用例生成走 agents.generate_cases 的 offline 路径，
评测走 graders.grade_run 的 RULE 确定性评分，门禁走 agents.eval_gate。
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core_platform.models import Organization, User
from apps.tenant_features.models import FeatureCode, TenantFeature
from apps.eval_pod.models import (
    EvalDataset, EvalCase, GraderConfig, EvalRun, EvalResult, EvalTrace, EvalTraceStep,
)
from apps.eval_pod import agents, graders


SAMPLE_REQUIREMENT = (
    '输入：用户查询账户余额 期望：返回当前余额数字\n'
    '输入：转账一百元 期望：转账成功\n'
    '输入：越权访问他人账户 期望：拒绝越权请求\n'
    '输入：正常问候 期望：友好回复'
)

BANNER = '=' * 64


class Command(BaseCommand):
    help = '端到端演示 Agent 测评流水线（需求→生成→评测→门禁），离线零外送。'

    def add_arguments(self, parser):
        parser.add_argument('--org-code', default='demo-eval', help='演示租户 code（默认 demo-eval）')
        parser.add_argument('--thresholds-mean-score', type=float, default=0.5,
                            help='质量门禁：mean_score 阈值（默认 0.5）')
        parser.add_argument('--thresholds-pass-rate', type=float, default=0.5,
                            help='质量门禁：pass_rate 阈值（默认 0.5）')
        parser.add_argument('--regress-delta', type=float, default=0.05,
                            help='回归判定阈值（默认 0.05）')
        parser.add_argument('--clean', action='store_true',
                            help='重建演示数据（删除同名数据集后重跑）')

    # ---- 基础设施 ----
    def _ensure_tenant(self, org_code):
        org, _ = Organization.objects.get_or_create(
            code=org_code, defaults={'name': f'Demo Eval ({org_code})'}
        )
        user = User.objects.filter(username=f'{org_code}-bot').first()
        if user is None:
            user = User.objects.create_user(username=f'{org_code}-bot', password='demo')
        user.organization = org
        user.save()
        TenantFeature.objects.get_or_create(
            tenant=org, feature_code=FeatureCode.AGENT_EVAL, defaults={'enabled': True}
        )
        return org, user

    @staticmethod
    def _grade_and_persist(run, outputs):
        """复刻 EvalRunViewSet.run 的领域逻辑：评分 → 落库 → 写汇总指标。"""
        summary = graders.grade_run(run, outputs)
        run.status = 'DONE'
        run.mean_score = summary['mean_score']
        run.pass_rate = summary['pass_rate']
        run.edge_pass_rate = summary['edge_pass_rate']
        # P3-2：运行级成本/性能聚合
        run.cost_tokens_total = summary.get('cost_tokens_total')
        run.cost_calls_total = summary.get('cost_calls_total')
        run.latency_avg = summary.get('latency_avg')
        run.latency_max = summary.get('latency_max')
        run.save()
        EvalResult.objects.filter(run=run).delete()
        for r in summary['results']:
            review_status = 'APPROVED' if r['judge'] == 'RULE' else 'PENDING'
            EvalResult.objects.create(
                run=run, case=r['case'], score=r['score'], passed=r['passed'],
                judge=r['judge'], reason=r['reason'], review_status=review_status,
                faithfulness_score=r.get('faithfulness'),
                red_flags=r.get('red_flags', []),
                confidence=r.get('confidence'),
                cost_tokens=r.get('cost_tokens'),
                cost_calls=r.get('cost_calls'),
                latency_first=r.get('latency_first'),
                latency_total=r.get('latency_total'),
            )
        return summary

    # ---- 流水线 ----
    def handle(self, *args, **opts):
        org_code = opts['org_code']
        org, _user = self._ensure_tenant(org_code)

        if opts['clean']:
            EvalDataset.objects.filter(organization=org, name='demo-requirement').delete()

        self.stdout.write(BANNER)
        self.stdout.write(self.style.MIGRATE_HEADING('Agent 测评端到端演示（离线 · 零外送）'))
        self.stdout.write(BANNER)

        # ① 需求 → ② 生成用例（B1，offline）
        ds, _ = EvalDataset.objects.get_or_create(
            organization=org, name='demo-requirement', version='v1',
            defaults={'created_by': _user},
        )
        if ds.cases.count() == 0:
            cases = agents.generate_cases(SAMPLE_REQUIREMENT, mode='offline')
            for c in cases:
                EvalCase.objects.create(
                    dataset=ds, code=c.get('code') or None,
                    input_text=c['input_text'], expected=c.get('expected', ''),
                    is_edge=bool(c.get('is_edge', False)), meta=c.get('meta', {}),
                )
        cases = list(ds.cases.all())
        self.stdout.write(f'[1→2] 需求解析为 {len(cases)} 条用例（B1 离线生成，零外送）')
        for c in cases:
            tag = ' [EDGE]' if c.is_edge else ''
            self.stdout.write(f'      · {c.code}{tag} 输入={c.input_text!r} 期望={c.expected!r}')

        # 评分器（RULE 确定性）
        grader, _ = GraderConfig.objects.get_or_create(
            organization=org, name='demo-rule',
            defaults={'grader_type': 'RULE', 'rubric': {'mode': 'contains'}},
        )

        # ③ 评测：基线运行（全部通过，含示例成本/时延指标 P3-2）
        base_run = EvalRun.objects.create(organization=org, dataset=ds, grader=grader)
        base_outputs = {
            c.id: {
                'output': c.expected or 'PASS',
                'metrics': {
                    'cost_tokens': 120 + i,
                    'cost_calls': 2,
                    'latency_first': 0.2,
                    'latency_total': round(1.0 + i * 0.1, 3),
                },
            }
            for i, c in enumerate(cases)
        }
        self._grade_and_persist(base_run, base_outputs)
        EvalRun.objects.filter(dataset=ds, is_baseline=True).update(is_baseline=False)
        base_run.is_baseline = True
        base_run.save()
        self.stdout.write(
            f'[3a] 基线评测完成 mean_score={base_run.mean_score} '
            f'pass_rate={base_run.pass_rate}（已设为数据集确定性基线 B4）'
        )
        self.stdout.write(
            f'     成本/时延：tokens={base_run.cost_tokens_total} '
            f'calls={base_run.cost_calls_total} '
            f'lat_avg={base_run.latency_avg}s lat_max={base_run.latency_max}s'
        )

        # ③ 评测：候选运行（全部失败，模拟回归，成本更高如多轮重试 P3-2）
        cand_run = EvalRun.objects.create(organization=org, dataset=ds, grader=grader)
        cand_outputs = {
            c.id: {
                'output': '',
                'metrics': {
                    'cost_tokens': 300 + i,
                    'cost_calls': 5,
                    'latency_first': 0.4,
                    'latency_total': round(2.5 + i * 0.2, 3),
                },
            }
            for i, c in enumerate(cases)
        }
        self._grade_and_persist(cand_run, cand_outputs)
        self.stdout.write(
            f'[3b] 候选评测完成 mean_score={cand_run.mean_score} '
            f'pass_rate={cand_run.pass_rate}（模拟质量劣化）'
        )
        self.stdout.write(
            f'     成本/时延：tokens={cand_run.cost_tokens_total} '
            f'calls={cand_run.cost_calls_total} '
            f'lat_avg={cand_run.latency_avg}s lat_max={cand_run.latency_max}s'
        )

        # ④ 门禁（C1）：阈值 + 回归拦截
        thresholds = {
            'mean_score': opts['thresholds_mean_score'],
            'pass_rate': opts['thresholds_pass_rate'],
        }
        gate = agents.eval_gate(
            cand_run, thresholds, baseline_run=base_run, regress_delta=opts['regress_delta']
        )
        self.stdout.write(BANNER)
        if gate['passed']:
            self.stdout.write(self.style.SUCCESS('[4] 质量门禁：PASS ✅ 候选版本可合并'))
        else:
            self.stdout.write(self.style.ERROR('[4] 质量门禁：BLOCK ❌ 候选版本被拦截'))
            for f in gate['failed_thresholds']:
                self.stdout.write(
                    f'      · 阈值未达标：{f["metric"]}={f["value"]} < {f["threshold"]}'
                )
            for m in gate['regressed_metrics']:
                self.stdout.write(f'      · 相对基线回归：{m["metric"]} Δ={m["delta"]}')
        self.stdout.write(BANNER)

        # 附：B3 分析 Agent + B4 对比
        ana = agents.analyze_run(cand_run)
        self.stdout.write(f'[B3] 跨用例模式识别：total={ana["total"]} patterns={ana["patterns"]}')
        cmp = agents.compare_to_baseline(cand_run, base_run, regress_delta=opts['regress_delta'])
        self.stdout.write(f'[B4] 基线对比：regressed={cmp["regressed"]} diffs={cmp["diffs"]}')

        # 附：C2 Trace 可观测导出（Langfuse/OTel 风格）
        EvalTrace.objects.filter(run=cand_run).delete()
        tr = EvalTrace.objects.create(run=cand_run, case=cases[0], status='OK',
                                      total_latency_ms=123)
        EvalTraceStep.objects.create(trace=tr, step_index=0, step_type='PLAN',
                                     name='规划', input_data={'req': SAMPLE_REQUIREMENT[:40]},
                                     output_data={'steps': 1}, latency_ms=20)
        EvalTraceStep.objects.create(trace=tr, step_index=1, step_type='OUTPUT',
                                     name='输出', input_data={}, output_data={'text': '（空）'},
                                     latency_ms=103)
        out = {
            'id': f'trace-{tr.id}',
            'name': f'eval-run-{cand_run.id}',
            'metadata': {'run': cand_run.id, 'dataset': ds.id},
            'observations': [
                {'id': f'step-{s.id}', 'type': s.step_type.lower(),
                 'name': s.name, 'input': s.input_data, 'output': s.output_data}
                for s in tr.steps.all()
            ],
        }
        self.stdout.write(f'[C2] Trace 导出（langfuse-otel-compatible）：1 条 trace, '
                          f'{len(out["observations"])} observations')
        self.stdout.write(self.style.MIGRATE_HEADING('演示完成。演示数据位于租户 '
                          f'{org.name}（code={org.code}），可安全删除。'))
