"""
评测舱回归测试（路线三 · Phase 1 契约 + Phase 2 M2/M3）。

覆盖：
A. 评估引擎单元（离线）：
   - 规则评分（精确/包含/正则）
   - LLM-as-Judge 无配置 → 确定性降级 HEURISTIC（零外送）
   - LLM-as-Judge 注入 call_fn → LLM_JUDGE（JSON 解析、pass/score）
   - grade_run 汇总（含边缘用例通过率）
B. 底座契约（Phase 1）：
   - 功能开关门禁：未开通 AGENT_EVAL 的租户 → 403
   - 严格租户隔离：他租户数据集不可见（无超级读者）
   - RULE 评测 run @action 端到端落库汇总
"""
from django.test import TestCase

from rest_framework.test import APIClient

from apps.core_platform.models import Organization, User
from apps.tenant_features.models import FeatureCode, TenantFeature

from . import graders
from .models import EvalCase, EvalDataset, EvalResult, EvalRun, EvalTrace, EvalTraceStep, GraderConfig


class _DummyCase:
    def __init__(self, expected='', input_text='', is_edge=False):
        self.expected = expected
        self.input_text = input_text
        self.is_edge = is_edge


# ============================================================
# A. 评估引擎单元（不依赖 DB / 网络）
# ============================================================
class GraderUnitTest(TestCase):
    def test_rule_exact(self):
        case = _DummyCase(expected='hello')
        score, passed, _, judge = graders.rule_grade(case, 'hello', {'mode': 'exact'})
        self.assertEqual(judge, 'RULE')
        self.assertTrue(passed)
        self.assertEqual(score, 1.0)

    def test_rule_contains_fail(self):
        case = _DummyCase(expected='hello')
        score, passed, _, _ = graders.rule_grade(case, 'world', {'mode': 'contains'})
        self.assertFalse(passed)
        self.assertEqual(score, 0.0)

    def test_rule_regex(self):
        case = _DummyCase(expected=r'\d{3}')
        _, passed, _, _ = graders.rule_grade(case, 'abc123xyz', {'mode': 'regex'})
        self.assertTrue(passed)

    def test_llm_judge_degrades_without_config(self):
        """无 LLM 配置 → HEURISTIC 降级，不触达任何外部端点（零出域）。"""
        case = _DummyCase(expected='success', input_text='q')
        score, passed, reason, judge = graders.llm_judge_grade(case, 'success')
        self.assertEqual(judge, 'HEURISTIC')
        self.assertTrue(passed)

    def test_llm_judge_with_injected_call(self):
        """注入 call_fn 模拟 LLM 裁判返回，验证 JSON 解析与分值映射。"""

        def fake_call(config, messages):
            return {
                'choices': [{
                    'message': {
                        'content': '{"score": 0.9, "passed": true, "reason": "输出符合要求"}'
                    }
                }]
            }

        case = _DummyCase(expected='success', input_text='q')
        score, passed, reason, judge = graders.llm_judge_grade(
            case, 'some output', rubric={'pass_threshold': 0.6}, call_fn=fake_call
        )
        self.assertEqual(judge, 'LLM_JUDGE')
        self.assertEqual(score, 0.9)
        self.assertTrue(passed)
        self.assertIn('符合要求', reason)

    def test_llm_judge_call_failure_degrades(self):
        """LLM 调用抛错 → 降级 HEURISTIC，评测不中断。"""
        def boom(config, messages):
            raise RuntimeError('LLM boom')

        case = _DummyCase(expected='success', input_text='q')
        score, passed, reason, judge = graders.llm_judge_grade(
            case, 'success', call_fn=boom
        )
        self.assertEqual(judge, 'HEURISTIC')
        self.assertTrue(passed)


# ============================================================
# B. 底座契约（Phase 1）：门禁 + 隔离 + 端到端
# ============================================================
class EvalPodContractTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org_a = Organization.objects.create(name='甲方A', code='org-a')
        cls.org_b = Organization.objects.create(name='甲方B', code='org-b')

        cls.user_a = User.objects.create_user('ua', password='x')
        cls.user_a.organization = cls.org_a
        cls.user_a.save()
        cls.user_b = User.objects.create_user('ub', password='x')
        cls.user_b.organization = cls.org_b
        cls.user_b.save()

        # 两租户均开通 agent 测评，以便分别验证"隔离"而非被门禁挡掉
        TenantFeature.objects.create(
            tenant=cls.org_a, feature_code=FeatureCode.AGENT_EVAL, enabled=True
        )
        TenantFeature.objects.create(
            tenant=cls.org_b, feature_code=FeatureCode.AGENT_EVAL, enabled=True
        )

        cls.client_a = APIClient()
        cls.client_a.force_authenticate(cls.user_a)
        cls.client_b = APIClient()
        cls.client_b.force_authenticate(cls.user_b)

    def test_gate_blocks_tenant_without_feature(self):
        """未开通 AGENT_EVAL 的租户访问评测 API → 403。"""
        org_c = Organization.objects.create(name='甲方C', code='org-c')
        user_c = User.objects.create_user('uc', password='x')
        user_c.organization = org_c
        user_c.save()
        # 注意：org_c 未创建 TenantFeature → 门禁应拒绝
        c = APIClient()
        c.force_authenticate(user_c)
        resp = c.post('/api/eval/datasets/', {'name': 'x', 'version': 'v1'}, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_create_dataset_respects_organization(self):
        """创建数据集时 organization 取自当前用户，不可越权指定。"""
        resp = self.client_a.post(
            '/api/eval/datasets/', {'name': 'ds-a', 'version': 'v1'}, format='json'
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        # 响应经 StandardResponseMiddleware 统一包裹，真实负载在 data['data']
        self.assertEqual(resp.data['data']['organization'], self.org_a.id)
        self.assertEqual(EvalDataset.objects.get(name='ds-a').organization_id, self.org_a.id)

    def test_tenant_isolation_datasets(self):
        """他租户数据集对当前租户不可见（无超级读者）。"""
        EvalDataset.objects.create(organization=self.org_a, name='ds-a1', version='v1')
        EvalDataset.objects.create(organization=self.org_b, name='ds-b1', version='v1')

        resp_a = self.client_a.get('/api/eval/datasets/')
        self.assertEqual(resp_a.status_code, 200)
        payload_a = resp_a.data['data']
        items_a = payload_a['results'] if isinstance(payload_a, dict) and 'results' in payload_a else payload_a
        names = {d['name'] for d in items_a}
        self.assertIn('ds-a1', names)
        self.assertNotIn('ds-b1', names)

        resp_b = self.client_b.get('/api/eval/datasets/')
        payload_b = resp_b.data['data']
        items_b = payload_b['results'] if isinstance(payload_b, dict) and 'results' in payload_b else payload_b
        names_b = {d['name'] for d in items_b}
        self.assertIn('ds-b1', names_b)
        self.assertNotIn('ds-a1', names_b)

    def test_rule_run_end_to_end(self):
        """RULE 评测 run @action 端到端：评分并落库汇总指标。"""
        ds = EvalDataset.objects.create(organization=self.org_a, name='ds-run', version='v1')
        c1 = EvalCase.objects.create(dataset=ds, input_text='q1', expected='ok', is_edge=False)
        c2 = EvalCase.objects.create(dataset=ds, input_text='q2', expected='edge', is_edge=True)
        grader = GraderConfig.objects.create(
            organization=self.org_a, name='g-rule', grader_type='RULE',
            rubric={'mode': 'contains'},
        )
        run = EvalRun.objects.create(organization=self.org_a, dataset=ds, grader=grader)

        resp = self.client_a.post(
            f'/api/eval/runs/{run.id}/run/',
            {'outputs': {str(c1.id): 'ok', str(c2.id): 'nomatch'}},
            format='json',
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        payload = resp.data['data']
        self.assertEqual(payload['status'], 'DONE')
        # c1 contains 'ok' → 通过；c2 不含 'edge' → 不通过
        self.assertEqual(payload['mean_score'], 0.5)
        self.assertEqual(payload['pass_rate'], 0.5)
        self.assertEqual(payload['edge_pass_rate'], 0.0)
        self.assertEqual(EvalResult.objects.filter(run=run).count(), 2)

    def test_hitl_review_gate(self):
        """LLM/启发式结果默认待复核；经人工确认后 review_status=APPROVED 且记录复核人。"""
        ds = EvalDataset.objects.create(organization=self.org_a, name='ds-hitl', version='v1')
        c1 = EvalCase.objects.create(dataset=ds, input_text='q1', expected='ok', is_edge=False)
        grader = GraderConfig.objects.create(
            organization=self.org_a, name='g-faith', grader_type='FAITHFULNESS',
        )
        run = EvalRun.objects.create(organization=self.org_a, dataset=ds, grader=grader)

        resp = self.client_a.post(
            f'/api/eval/runs/{run.id}/run/',
            {'outputs': {str(c1.id): 'ok'}}, format='json',
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        result = EvalResult.objects.get(run=run, case=c1)
        # 无 LLM 配置 → HEURISTIC 降级 → 默认待复核（HITL 门，阻断静默误报）
        self.assertEqual(result.judge, 'HEURISTIC')
        self.assertEqual(result.review_status, 'PENDING')

        r2 = self.client_a.post(
            f'/api/eval/runs/{run.id}/review/',
            {'result_id': result.id, 'review_status': 'APPROVED', 'review_note': '人工确认通过'},
            format='json',
        )
        self.assertEqual(r2.status_code, 200, r2.content)
        result.refresh_from_db()
        self.assertEqual(result.review_status, 'APPROVED')
        self.assertEqual(result.reviewer_id, self.user_a.id)
        self.assertIsNotNone(result.reviewed_at)

    def test_review_rejects_bad_status(self):
        """复核状态非法（既非 APPROVED 也非 REJECTED）→ 400。"""
        ds = EvalDataset.objects.create(organization=self.org_a, name='ds-hitl2', version='v1')
        c1 = EvalCase.objects.create(dataset=ds, input_text='q1', expected='ok', is_edge=False)
        grader = GraderConfig.objects.create(
            organization=self.org_a, name='g-faith2', grader_type='FAITHFULNESS',
        )
        run = EvalRun.objects.create(organization=self.org_a, dataset=ds, grader=grader)
        self.client_a.post(
            f'/api/eval/runs/{run.id}/run/',
            {'outputs': {str(c1.id): 'ok'}}, format='json',
        )
        result = EvalResult.objects.get(run=run, case=c1)
        r = self.client_a.post(
            f'/api/eval/runs/{run.id}/review/',
            {'result_id': result.id, 'review_status': 'NONSENSE'}, format='json',
        )
        self.assertEqual(r.status_code, 400)


class MetricUnitTest(TestCase):
    """指标类离线启发式（零外送、确定性）。"""

    def test_bias_heuristic_flags_profanity(self):
        case = _DummyCase(expected='x', input_text='q')
        score, passed, reason, judge = graders.metric_grade(case, '你这个废物', 'BIAS')
        self.assertEqual(judge, 'HEURISTIC')
        self.assertFalse(passed)
        self.assertLess(score, 0.5)
        self.assertTrue(reason)  # reason 强制非空（Giskard 原则）

    def test_toxicity_heuristic_flags(self):
        case = _DummyCase(expected='x', input_text='q')
        score, passed, reason, judge = graders.metric_grade(case, '滚蛋', 'TOXICITY')
        self.assertEqual(judge, 'HEURISTIC')
        self.assertFalse(passed)
        self.assertTrue(reason)

    def test_metric_offline_uses_heuristic(self):
        case = _DummyCase(expected='北京 上海', input_text='中国城市')
        for gt in ('FAITHFULNESS', 'ANSWER_RELEVANCY', 'TOOL_CORRECTNESS', 'PLAN_ADHERENCE'):
            score, passed, reason, judge = graders.metric_grade(case, '北京 上海', gt)
            self.assertEqual(judge, 'HEURISTIC')
            self.assertTrue(reason)


# ============================================================
# C. M4 Trace 回放（步骤级观测 + 失败归因 + 租户隔离）
# ============================================================
class EvalTraceTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org_a = Organization.objects.create(name='甲方A', code='org-a')
        cls.org_b = Organization.objects.create(name='甲方B', code='org-b')
        cls.user_a = User.objects.create_user('ua', password='x')
        cls.user_a.organization = cls.org_a
        cls.user_a.save()
        cls.user_b = User.objects.create_user('ub', password='x')
        cls.user_b.organization = cls.org_b
        cls.user_b.save()
        TenantFeature.objects.create(
            tenant=cls.org_a, feature_code=FeatureCode.AGENT_EVAL, enabled=True
        )
        TenantFeature.objects.create(
            tenant=cls.org_b, feature_code=FeatureCode.AGENT_EVAL, enabled=True
        )
        cls.client_a = APIClient()
        cls.client_a.force_authenticate(cls.user_a)
        cls.client_b = APIClient()
        cls.client_b.force_authenticate(cls.user_b)

        cls.ds = EvalDataset.objects.create(organization=cls.org_a, name='ds-tr', version='v1')
        cls.c1 = EvalCase.objects.create(dataset=cls.ds, input_text='q1', expected='ok')
        cls.grader = GraderConfig.objects.create(
            organization=cls.org_a, name='g-rule', grader_type='RULE', rubric={'mode': 'contains'}
        )
        cls.eval_run = EvalRun.objects.create(organization=cls.org_a, dataset=cls.ds, grader=cls.grader)

    def test_trace_create_and_step_ordering(self):
        """创建带 3 个步骤的 Trace，检索时步骤按 step_index 升序、支持回放。"""
        resp = self.client_a.post(
            '/api/eval/traces/',
            {
                'run': self.eval_run.id, 'case': self.c1.id, 'status': 'OK',
                'total_latency_ms': 1200,
                'steps': [
                    {'step_index': 2, 'step_type': 'OUTPUT', 'name': '最终输出', 'output_data': {'text': 'ok'}},
                    {'step_index': 0, 'step_type': 'PLAN', 'name': '规划', 'input_data': {'goal': 'q1'}},
                    {'step_index': 1, 'step_type': 'TOOL', 'name': 'search', 'latency_ms': 300},
                ],
            },
            format='json',
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        payload = resp.data['data']
        self.assertEqual(len(payload['steps']), 3)
        # 步骤按 step_index 升序返回（回放顺序正确）
        orders = [s['step_index'] for s in payload['steps']]
        self.assertEqual(orders, [0, 1, 2])
        # 落库条数正确
        self.assertEqual(EvalTrace.objects.filter(run=self.eval_run).count(), 1)
        self.assertEqual(EvalTraceStep.objects.filter(trace_id=payload['id']).count(), 3)

    def test_trace_list_filter_by_run(self):
        EvalTrace.objects.create(run=self.eval_run, case=self.c1, status='OK')
        resp = self.client_a.get(f'/api/eval/traces/?run={self.eval_run.id}')
        self.assertEqual(resp.status_code, 200)
        payload = resp.data['data']
        items = payload['results'] if isinstance(payload, dict) and 'results' in payload else payload
        self.assertEqual(len(items), 1)

    def test_trace_tenant_isolation(self):
        """他租户 Trace 不可见（经 run__organization 隔离），即使知道 run id。"""
        EvalTrace.objects.create(run=self.eval_run, case=self.c1, status='OK')
        resp = self.client_b.get(f'/api/eval/traces/?run={self.eval_run.id}')
        self.assertEqual(resp.status_code, 200)
        payload = resp.data['data']
        items = payload['results'] if isinstance(payload, dict) and 'results' in payload else payload
        self.assertEqual(len(items), 0)

    def test_trace_cross_tenant_create_blocked(self):
        """越权：乙方尝试把 Trace 挂到甲方的 run 上 → 400。"""
        resp = self.client_b.post(
            '/api/eval/traces/',
            {'run': self.eval_run.id, 'case': self.c1.id, 'status': 'OK', 'steps': []},
            format='json',
        )
        self.assertEqual(resp.status_code, 400)
