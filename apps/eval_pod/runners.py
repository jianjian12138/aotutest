"""P3-16 定时评测执行引擎。

- execute_run: 复用 grade_run + 结果持久化（与 EvalRunViewSet.run 同一套评分/复核逻辑）。
- run_scheduled_eval: 依据 EvalSchedule 自动产出被测 agent 的 outputs 并建一次运行。
  outputs 来源优先级：① agent_fn（注入，测试/生产真实调用封装）② schedule.agent_config
  （经 call_model_sync 同步调用 OpenAI 兼容端点）③ 均无则抛错（需在调度中配置）。
"""
from django.utils import timezone

from .models import EvalRun, EvalResult, EvalTrace, EvalTraceStep, SkillVersion
from . import graders


def _persist_run_summary(run, summary, agg_method='TRIMMED_MEAN', llm_config=None):
    """把 grade_run 的 summary 落库：更新 run 聚合字段 + 重建 EvalResult（含复核门）。

    被 execute_run 与 execute_harness_run 共用，保证评分/落库逻辑单一事实来源。
    """
    run.status = 'DONE'
    run.model_config = llm_config  # A4 溯源
    run.mean_score = summary['mean_score']
    run.pass_rate = summary['pass_rate']
    run.edge_pass_rate = summary['edge_pass_rate']
    run.capability_pass_rate = summary.get('capability_pass_rate')
    run.regression_pass_rate = summary.get('regression_pass_rate')
    run.pass_k_rate = summary['pass_k_rate']
    run.cost_tokens_total = summary.get('cost_tokens_total')
    run.cost_calls_total = summary.get('cost_calls_total')
    run.latency_avg = summary.get('latency_avg')
    run.latency_max = summary.get('latency_max')
    run.save()

    EvalResult.objects.filter(run=run).delete()
    for r in summary['results']:
        multi = r.get('judges') and any(len(j) > 1 for j in (r.get('judges') or []))
        if r['judge'] == 'RULE' and not multi:
            review_status = 'APPROVED'
        else:
            per = (r.get('judges') or [[]])[0]
            needs_review = multi and len({v.get('passed') for v in per}) > 1
            review_status = 'NEEDS_REVIEW' if needs_review else 'PENDING'
        conf = r.get('confidence')
        if (run.min_confidence is not None and conf is not None
                and conf < run.min_confidence):
            review_status = 'NEEDS_REVIEW'
        EvalResult.objects.create(
            run=run, case=r['case'], score=r['score'],
            passed=r['passed'], judge=r['judge'], reason=r['reason'],
            judges=r.get('judges', [[]])[0] if r.get('judges') else [],
            agg_method=agg_method,
            agg_score=r['score'], agg_passed=r['passed'],
            repeat_results=r.get('repeat_results', []),
            pass_k=r.get('pass_k'),
            faithfulness_score=r.get('faithfulness'),
            red_flags=r.get('red_flags', []),
            confidence=conf,
            cost_tokens=r.get('cost_tokens'),
            cost_calls=r.get('cost_calls'),
            latency_first=r.get('latency_first'),
            latency_total=r.get('latency_total'),
            review_status=review_status,
        )
    return run


def execute_run(run, outputs, llm_config=None, judge_configs=None,
                agg_method='TRIMMED_MEAN', repeat_k=1, min_confidence=None,
                skill_version=None):
    """评分并持久化一次运行（与 EvalRunViewSet.run 逻辑一致，单一事实来源）。

    返回更新后的 run 实例。skill_version 用于把本次运行绑定到具体技能版本
    （P3-4 可复现/审计）。
    """
    if repeat_k is not None:
        run.repeat_k = max(int(repeat_k), 1)
    if min_confidence is not None:
        run.min_confidence = float(min_confidence)
    if skill_version is not None:
        run.skill_version = skill_version

    summary = graders.grade_run(
        run, outputs, llm_config=llm_config,
        judge_configs=judge_configs, agg_method=agg_method,
    )
    return _persist_run_summary(run, summary, agg_method=agg_method, llm_config=llm_config)


def call_model_sync(config, prompt):
    """同步调用 OpenAI 兼容端点产出单个 case 的 agent 输出（生产 agent 接线缝）。

    仅当调度配置了 agent_config 且未注入 agent_fn 时启用；失败返回错误文本。
    """
    import requests
    try:
        messages = [{'role': 'user', 'content': prompt}]
        resp = requests.post(
            config.base_url,
            json={
                'model': config.model_name,
                'messages': messages,
                'max_tokens': config.max_tokens,
                'temperature': config.temperature,
                'top_p': config.top_p,
            },
            headers={'Authorization': f'Bearer {config.api_key}', 'Content-Type': 'application/json'},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data['choices'][0]['message']['content']
    except Exception as exc:  # noqa: BLE001
        return f'[agent 调用失败] {exc}'


def run_scheduled_eval(schedule, agent_fn=None):
    """按调度配置自动产出 outputs 并执行一次评测运行，返回 EvalRun。

    agent_fn(case_input_text) -> output_text 可注入（测试/生产真实 agent 封装）。
    """
    cases = list(schedule.dataset.cases.all())
    if not cases:
        raise ValueError('数据集为空，无法调度评测')

    outputs = {}
    if agent_fn is not None:
        for c in cases:
            outputs[str(c.id)] = agent_fn(c.input_text)
    elif schedule.agent_config is not None:
        for c in cases:
            outputs[str(c.id)] = call_model_sync(schedule.agent_config, c.input_text)
    else:
        raise ValueError('调度未配置 agent_config 或 agent_fn，无法自动产出 outputs')

    llm_config = None
    if schedule.grader.grader_type == 'LLM_JUDGE':
        from apps.requirement_analysis.models import AIModelConfig
        llm_config = AIModelConfig.for_tenant(schedule.organization)

    skill_version = SkillVersion.active_for(schedule.organization, 'eval-flow')

    run = EvalRun.objects.create(
        organization=schedule.organization,
        dataset=schedule.dataset,
        grader=schedule.grader,
        model_config=schedule.agent_config,
        status='PENDING',
        repeat_k=schedule.repeat_k,
        min_confidence=schedule.min_confidence,
        created_by=schedule.created_by,
    )
    return execute_run(
        run, outputs, llm_config=llm_config,
        repeat_k=schedule.repeat_k, min_confidence=schedule.min_confidence,
        skill_version=skill_version,
    )


def execute_harness_run(run, harness, agent_fn=None, llm_config=None,
                        agg_method='TRIMMED_MEAN', repeat_k=None, min_confidence=None,
                        skill_version=None):
    """P3-6 端到端编排：reset → 逐用例 run → grade_run 落库 → 冷启动基线 → 写 EvalTrace。

    harness 可为 MockHarness / RealHarness（见 harness.py）。复用 _persist_run_summary
    与 EvalRunViewSet.run 同一套评分/落库逻辑（单一事实来源），额外把 harness 产出的
    步骤级 trace 固化为 EvalTrace/EvalTraceStep（M4 回放 + E5 崩溃归因）。
    返回更新后的 run 实例。
    """
    cases = list(run.dataset.cases.all())
    if not cases:
        raise ValueError('数据集为空，无法执行 harness 评测')

    if repeat_k is not None:
        run.repeat_k = max(int(repeat_k), 1)
    if min_confidence is not None:
        run.min_confidence = float(min_confidence)
    if skill_version is not None:
        run.skill_version = skill_version

    env = {'organization_id': run.organization_id, 'dataset_id': run.dataset_id}
    state = harness.reset(env)

    outputs = {}
    traces = {}  # case_id -> steps
    for case in cases:
        output, steps = harness.run(state, agent_fn, case)
        outputs[str(case.id)] = output
        traces[case.id] = steps

    summary = graders.grade_run(run, outputs, llm_config=llm_config, agg_method=agg_method)
    _persist_run_summary(run, summary, agg_method=agg_method, llm_config=llm_config)

    # P3-5 冷启动基线策略：数据集首个 DONE 运行自动设为基线（幂等）。
    if not EvalRun.objects.filter(dataset=run.dataset, is_baseline=True).exists():
        run.is_baseline = True
        run.save(update_fields=['is_baseline'])

    # P3-4：绑定当前生效的评测技能版本（可复现/审计）。
    sv = SkillVersion.active_for(run.organization, 'eval-flow')
    if sv is not None:
        run.skill_version = sv
        run.save(update_fields=['skill_version'])

    # 写 EvalTrace（M4 归因）：每条 (run, case) 一条，步骤对齐 EvalTraceStep。
    EvalTrace.objects.filter(run=run).delete()
    for case in cases:
        steps = traces.get(case.id, [])
        total_ms = sum(int(s.get('latency_ms') or 0) for s in steps)
        has_err = any(s.get('step_type') == 'ERROR' or s.get('error') for s in steps)
        trace = EvalTrace.objects.create(
            run=run, case=case,
            status='ERROR' if has_err else 'OK',
            total_latency_ms=total_ms,
            finished_at=timezone.now(),
        )
        for s in steps:
            EvalTraceStep.objects.create(
                trace=trace,
                step_index=s.get('step_index', 0),
                step_type=s.get('step_type', 'OBSERVE'),
                name=s.get('name', ''),
                input_data=s.get('input_data', {}),
                output_data=s.get('output_data', {}),
                latency_ms=s.get('latency_ms'),
                error=s.get('error', ''),
            )
    return run
