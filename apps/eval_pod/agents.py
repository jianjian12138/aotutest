"""
Phase B 智能体自动化辅舱（路线三 · 已批准方案 B1-B4）+ Phase C 门禁（C1）。

B1 用例生成 Agent：需求/API 文档 → 稳定中间格式 EvalCase JSON。
  离线启发式（零外送、确定性）+ 可选 LLM 升级（有租户模型时）。
B3 分析 Agent：复用 LLM-Judge 结果 + 跨用例模式识别（系统性失败定位）。
B4 确定性基线：当前 run 与 baseline run 对比，定位劣化指标。
C1 质量门禁：阈值 + 回归拦截，指出掉哪个指标（复用基线对比）。

所有离线路径不触达任何外部端点，契合「数据不出域」红线。
稳定中间格式（每条用例）：
  {code, input_text, expected, is_edge, meta}
对应公众号《多Agent协作测试系统实战》「用例生成」角色；分析 Agent 对应「结果分析」
角色（机械断言 + LLM-Judge + 模式识别），并接入已有 HITL 复核门。
"""
import hashlib
import json
import re

_EDGE_HINTS = re.compile(
    r'异常|错误|非法|边界|攻击|越权|对抗|拒绝|负面|无效|invalid|error|edge|adversarial',
    re.I,
)


def _is_edge(text):
    return bool(_EDGE_HINTS.search(text or ''))


def _normalize(text):
    """小写归一化（用于数据集/关键词匹配）。"""
    return (text or '').lower()


def _split_items(req_text):
    """按换行/分号/句号边界切分需求条目。"""
    parts = re.split(r'\n+|；|;|(?<=[。！？])', req_text or '')
    return [p.strip() for p in parts if p and p.strip()]


def _parse_item(item):
    """从单条需求解析 (input_text, expected)。无法解析出 expected 时返回开放式（expected=''）。"""
    m = re.search(
        r'(?:输入|当|给定|问|Q)[:：]?\s*(.+?)\s*'
        r'(?:期望|应该|应|需|返回|答|输出|A)[:：]?\s*(.+)', item)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    m = re.search(r'(.+?)\s*(?:->|=>|→)\s*(.+)', item)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return item, ''


def _offline_generate(req_text, knowledge_context=None):
    """离线启发式生成（零外送、确定性）。

    P3-13：当 knowledge_context（RAG 检索出的知识片段文本）非空时，
    额外从知识片段中抽取需求句作为补充生成源，使离线生成也能被知识库"接地"。
    """
    items = _split_items(req_text)
    if knowledge_context:
        items = items + _extract_requirement_sentences(knowledge_context)
    cases = []
    for item in items:
        input_text, expected = _parse_item(item)
        code = 'req-' + hashlib.md5(item.encode('utf-8')).hexdigest()[:8]
        cases.append({
            'code': code,
            'input_text': input_text,
            'expected': expected,
            'is_edge': _is_edge(item),
            'meta': {'source': 'offline', 'rag': bool(knowledge_context), 'raw': item[:200]},
        })
    return cases


def _llm_generate(req_text, llm_config, call_fn, knowledge_context=None):
    """可选 LLM 升级：调用租户模型生成更丰富用例，解析为稳定中间格式。

    P3-13：knowledge_context 非空时注入知识库片段，引导生成贴合业务的用例。
    调用失败或解析失败由调用方负责降级回离线（保证确定性、零外送）。
    """
    system = (
        '你是评测用例生成专家。根据需求生成结构化评测用例，'
        '仅返回 JSON 数组，每项含 input_text(输入/提示)、expected(期望输出)、'
        'is_edge(是否边缘/对抗用例)。不要输出解释。'
    )
    if knowledge_context:
        system += '\n参考以下知识库片段，生成贴合实际业务的评测用例：\n' + knowledge_context
    messages = [
        {'role': 'system', 'content': system},
        {'role': 'user', 'content': req_text},
    ]
    resp = call_fn(llm_config, messages)
    content = resp['choices'][0]['message']['content']
    arr = json.loads(content)
    out = []
    for i, c in enumerate(arr):
        out.append({
            'code': c.get('code') or f'llm-{i}',
            'input_text': c.get('input_text', ''),
            'expected': c.get('expected', ''),
            'is_edge': bool(c.get('is_edge', False)),
            'meta': {'source': 'llm', 'rag': bool(knowledge_context)},
        })
    return out


def default_llm_call(config, messages):
    """生产默认 LLM 调用：复用平台 AIModelService（租户 for_tenant 配置）。

    返回值形态对齐 graders 的约定：{'choices':[{'message':{'content':...}}]}，
    与 _llm_generate 的解析一致。仅在 LLM 升级路径（mode='llm'）下由视图注入。
    """
    from asgiref.sync import async_to_sync
    from apps.requirement_analysis.models import AIModelService
    return async_to_sync(AIModelService.call_openai_compatible_api)(config, messages)


def generate_cases(req_text, mode='offline', llm_config=None, call_fn=None,
                   knowledge_ids=None, org=None, knowledge_context=None):
    """B1 用例生成 Agent：需求 → 稳定中间格式 EvalCase 列表。

    离线（默认，零外送）或 LLM 升级；LLM 失败确定性降级离线。
    P3-13：可传入 knowledge_ids+org（自动检索）或直接 knowledge_context（已检索文本），
    将租户知识库片段作为 RAG 上下文注入生成，使用例"接地"到需求/接口文档。
    """
    if knowledge_context is None and knowledge_ids and org:
        knowledge_context, _ = retrieve_for_generation(
            req_text, org, knowledge_ids=knowledge_ids
        )
    if mode == 'llm' and (llm_config or call_fn):
        try:
            return _llm_generate(req_text, llm_config, call_fn, knowledge_context=knowledge_context)
        except Exception:
            return _offline_generate(req_text, knowledge_context=knowledge_context)
    return _offline_generate(req_text, knowledge_context=knowledge_context)


_JUDGE_HINTS = {
    'RULE': '规则用例存在结构性失败，检查 expected 与 rubric 是否匹配',
    'LLM_JUDGE': 'LLM 裁判类结果存在系统性偏差，建议复核评分提示',
    'HEURISTIC': '离线启发式结果需经 HITL 人工复核确认',
    'POLL': '多裁判聚合结果存在分歧，建议对黄金样本人工复核',
}


# ---------------------------------------------------------------------------
# E1 PoLL 多裁判聚合（文章一：trimmed_mean / majority / panel_disagree）
# ---------------------------------------------------------------------------
def aggregate_judges(votes, method='TRIMMED_MEAN'):
    """对多裁判逐裁决做聚合。

    votes: 列表，每项 {score(0-1), passed(bool), judge(str), reason(str)}
    返回 (agg_score, agg_passed, needs_review, per_judge)
    - TRIMMED_MEAN：样本数>=3 时去一个最高一个最低再取均值；通过=均值>=0.6。
    - MAJORITY：通过=过半数 passed；agg_score=通过比例。
    - PANEL_DISAGREE：均值通过，但若裁判间 passed 不一致→needs_review=True
      （标记黄金样本送人工复核，对标文章一 panel_disagree）。
    """
    per = [dict(v) for v in votes]
    scores = [float(v['score']) for v in votes]
    passeds = [bool(v['passed']) for v in votes]
    if not scores:
        return 0.0, False, False, per

    if method == 'MAJORITY':
        agg_passed = sum(passeds) > len(passeds) / 2
        agg_score = round(sum(passeds) / len(passeds), 3)
    elif method == 'PANEL_DISAGREE':
        agg_score = round(sum(scores) / len(scores), 3)
        agg_passed = agg_score >= 0.6
        needs_review = (len(set(passeds)) > 1)  # 裁判间结论不一致
        return agg_score, agg_passed, needs_review, per
    else:  # TRIMMED_MEAN
        s = sorted(scores)
        if len(s) >= 3:
            s = s[1:-1]  # 去极值
        agg_score = round(sum(s) / len(s), 3)
        agg_passed = agg_score >= 0.6

    needs_review = False
    return agg_score, agg_passed, needs_review, per


def analyze_run(run):
    """B3 分析 Agent：跨用例模式识别（系统性失败定位），复用已有评分结果。

    升级（E5）：对失败用例叠加**长程 4 崩溃模式**归因
    （错误累积 / 状态漂移 / 崩溃行为 / 工具退化），基于 M4 Trace 步骤。
    无 Trace 时给出 NO_TRACE 标记，不阻塞分析。
    """
    results = list(run.results.select_related('case').all())
    by_judge = {}
    for r in results:
        d = by_judge.setdefault(r.judge, {'n': 0, 'fail': 0})
        d['n'] += 1
        if not r.passed:
            d['fail'] += 1
    patterns = []
    for judge, d in by_judge.items():
        rate = d['fail'] / d['n'] if d['n'] else 0
        if rate >= 0.5:
            patterns.append({
                'judge': judge,
                'fail_rate': round(rate, 2),
                'hint': _JUDGE_HINTS.get(judge, '存在系统性失败，建议人工复核'),
            })

    crash = _crash_mode_attribution(run, results)
    # P3-3：低置信用例（置信度 < run.min_confidence 且已配置）汇总，提示人工复核。
    gate_mc = getattr(run, 'min_confidence', None)
    low_conf = [
        {'case_id': r.case_id, 'confidence': r.confidence}
        for r in results
        if r.confidence is not None and gate_mc is not None and r.confidence < gate_mc
    ]
    return {
        'total': len(results),
        'patterns': patterns,
        'crash_modes': crash['summary'],
        'crash_details': crash['details'],
        'low_confidence_count': len(low_conf),
        'low_confidence': low_conf,
    }


def _classify_crash_mode(trace, output):
    """对单条 trace 判定长程崩溃模式（离线启发式，文章二 4 崩溃模式）。"""
    if trace is None:
        return 'NO_TRACE', '无 M4 Trace，无法归因（建议评测时采集轨迹）'
    steps = list(trace.steps.all())
    err_steps = [s for s in steps if s.step_type == 'ERROR' or s.error]
    tool_steps = [s for s in steps if s.step_type == 'TOOL']
    obs_steps = [s for s in steps if s.step_type == 'OBSERVE']

    if trace.status == 'ERROR' or err_steps:
        if len(err_steps) >= 2:
            return 'CUMULATIVE_ERROR', f'多个连续错误步骤（{len(err_steps)} 处），疑似错误累积'
        return 'CATASTROPHIC', '存在执行错误/崩溃步骤，疑似崩溃行为'
    if tool_steps and (len(tool_steps) >= 3 or
                       any(s.error for s in tool_steps)):
        return 'TOOL_DEGRADATION', f'工具调用退化（{len(tool_steps)} 次调用或含失败调用）'
    if obs_steps and output:
        # 状态漂移：最终输出与中间观察严重不一致（token 重叠低）
        mid = ' '.join(str(s.output_data) for s in obs_steps[1:])
        if mid:
            overlap = len(set(output) & set(mid)) / max(len(set(mid)), 1)
            if overlap < 0.15:
                return 'STATE_DRIFT', '最终输出与中间观察严重不一致，疑似状态漂移'
    return 'UNKNOWN', '未能判定明确崩溃模式'


def _crash_mode_attribution(run, results):
    """汇总失败用例的崩溃模式分布。"""
    traces = {
        t.case_id: t for t in run.traces.select_related('case').prefetch_related('steps').all()
    }
    summary = {}
    details = []
    for r in results:
        if r.passed:
            continue
        trace = traces.get(r.case_id)
        mode, reason = _classify_crash_mode(trace, getattr(r.case, 'input_text', ''))
        summary[mode] = summary.get(mode, 0) + 1
        details.append({'case_id': r.case_id, 'crash_mode': mode, 'reason': reason})
    return {'summary': summary, 'details': details}


def compare_to_baseline(run, baseline_run, regress_delta=0.05, metrics=None):
    """B4 确定性基线对比：当前 run vs baseline（同 dataset）。定位劣化指标。

    metrics：参与对比的指标列表；None 用核心指标默认集
    （mean_score/pass_rate/edge_pass_rate，P3-7 核心指标）。
    """
    if metrics is None:
        metrics = ['mean_score', 'pass_rate', 'edge_pass_rate']
    diffs = {}
    regressed = False
    for m in metrics:
        cur = getattr(run, m)
        base = getattr(baseline_run, m)
        if cur is None or base is None:
            continue
        delta = round(cur - base, 3)
        diffs[m] = {'current': cur, 'baseline': base, 'delta': delta}
        if delta < -regress_delta:
            regressed = True
    return {'diffs': diffs, 'regressed': regressed}


# P3-7 核心指标默认集：相对基线跌 >5% 即硬阻断（阻断性指标）。
CORE_METRICS = ['mean_score', 'pass_rate', 'edge_pass_rate']


def eval_gate(run, thresholds=None, aux_thresholds=None, baseline_run=None,
              regress_delta=0.05, min_confidence=None, aux_metrics=None):
    """C1 质量门禁（P3-7 分层）：核心指标阻断，辅助指标仅告警。

    - thresholds（核心）/ 核心指标基线回归 → 阻断（failed_thresholds / regressed_metrics）
    - aux_thresholds（辅助）/ aux_metrics 基线回归 → 仅告警（aux_warnings / aux_regressed）
      辅助指标无论是否超标都**不阻断**合并，只提示需关注。
    - P3-1 死循环/幻觉红线、P3-3 置信度门始终为硬阻断项。
    """
    thresholds = thresholds or {}
    aux_thresholds = aux_thresholds or {}

    # 核心：阈值未达 → 阻断
    failed = []
    for metric, thr in thresholds.items():
        val = getattr(run, metric)
        if val is None:
            continue
        if val < thr:
            failed.append({'metric': metric, 'value': val, 'threshold': thr})

    # 辅助：阈值未达 → 仅告警（不阻断）
    aux_warnings = []
    for metric, thr in aux_thresholds.items():
        val = getattr(run, metric)
        if val is None:
            continue
        if val < thr:
            aux_warnings.append({'metric': metric, 'value': val, 'threshold': thr})

    # 基线回归：核心指标回归阻断；辅助指标回归仅告警
    regressed_metrics = []
    aux_regressed = []
    if baseline_run:
        core_metrics = list(thresholds.keys()) or CORE_METRICS
        cmp_core = compare_to_baseline(run, baseline_run, regress_delta, metrics=core_metrics)
        for m, d in cmp_core['diffs'].items():
            if d['delta'] < -regress_delta:
                regressed_metrics.append({'metric': m, 'delta': d['delta']})
        if aux_metrics:
            cmp_aux = compare_to_baseline(run, baseline_run, regress_delta, metrics=aux_metrics)
            for m, d in cmp_aux['diffs'].items():
                if d['delta'] < -regress_delta:
                    aux_regressed.append({'metric': m, 'delta': d['delta']})

    # P3-1：死循环/幻觉红线零容忍硬门（文章共识 =0%）；命中即阻断并精确指出用例。
    red_line_cases = [
        {'case_id': r.case_id, 'red_flags': r.red_flags}
        for r in run.results.all() if r.red_flags
    ]
    if red_line_cases:
        failed.append({
            'metric': 'red_line', 'value': len(red_line_cases), 'threshold': 0,
            'cases': red_line_cases,
        })

    # P3-3：置信度门（Agent-as-Judge 置信度 < 阈值 → 不自动过门）；
    # 阈值优先取入参，否则取 run.min_confidence（门禁 API 可省略）。
    gate_mc = min_confidence if min_confidence is not None else getattr(run, 'min_confidence', None)
    low_confidence = []
    if gate_mc is not None:
        low_confidence = [
            {'case_id': r.case_id, 'confidence': r.confidence}
            for r in run.results.all()
            if r.confidence is not None and r.confidence < gate_mc
        ]

    return {
        # 辅助告警不参与阻断判定
        'passed': not (failed or regressed_metrics or red_line_cases or low_confidence),
        'failed_thresholds': failed,
        'regressed_metrics': regressed_metrics,
        'aux_warnings': aux_warnings,
        'aux_regressed': aux_regressed,
        'red_line_cases': red_line_cases,
        'low_confidence': low_confidence,
    }


# ---------------------------------------------------------------------------
# E3 Pairwise + Elo（文章一：位置交换消偏的竞技排名）
# ---------------------------------------------------------------------------
def recompute_elo(org, dataset=None, k=32):
    """幂等重算组织内模型 Elo（round-robin 同数据集 runs 两两比较，按 mean_score 定胜负）。

    返回 {(model_name, dataset_id_or_None): rating}。同时落库 EvalEloRating
    （含跨数据集组织级聚合 dataset=None）。
    """
    from collections import defaultdict

    from apps.core_platform.models import Organization as Org
    from .models import EvalDataset, EvalEloRating, EvalRun

    if isinstance(org, Org):
        org_id = org.id
    else:
        org_id = org

    runs = EvalRun.objects.filter(organization_id=org_id, status='DONE')
    if dataset is not None:
        ds_id = dataset.id if hasattr(dataset, 'id') else dataset
        runs = runs.filter(dataset_id=ds_id)
    runs = list(runs.select_related('model_config', 'dataset'))

    # (player, dataset_id) -> rating；player = model_name 或「无LLM/启发式」
    ratings = defaultdict(float)
    players_by_ds = defaultdict(list)  # dataset_id -> [(player, run)]
    for r in runs:
        player = r.model_config.model_name if r.model_config else '（无 LLM / 启发式）'
        did = r.dataset_id
        players_by_ds[did].append((player, r))
        key = (player, did)
        if key not in ratings:
            ratings[key] = 1500.0

    # 组织级聚合（dataset=None）
    org_players = defaultdict(list)
    for did, lst in players_by_ds.items():
        for player, r in lst:
            org_players[player].append(r)

    def _round_robin(group_runs, scope_ds_id):
        n = len(group_runs)
        for i in range(n):
            for j in range(i + 1, n):
                pa, ra = group_runs[i][0], group_runs[i][1]
                pb, rb = group_runs[j][0], group_runs[j][1]
                if pa == pb:
                    continue
                sa = ra.mean_score or 0.0
                sb = rb.mean_score or 0.0
                if sa > sb:
                    sa_s, sb_s = 1.0, 0.0
                elif sb > sa:
                    sa_s, sb_s = 0.0, 1.0
                else:
                    sa_s, sb_s = 0.5, 0.5
                ka = ratings[(pa, scope_ds_id)]
                kb = ratings[(pb, scope_ds_id)]
                ea = 1 / (1 + 10 ** ((kb - ka) / 400))
                eb = 1 / (1 + 10 ** ((ka - kb) / 400))
                ratings[(pa, scope_ds_id)] = ka + k * (sa_s - ea)
                ratings[(pb, scope_ds_id)] = kb + k * (sb_s - eb)

    for did, lst in players_by_ds.items():
        _round_robin(lst, did)

    # 落库（含组织级聚合 dataset=None）
    saved = {}
    for (player, did), rating in ratings.items():
        ds = EvalDataset.objects.filter(id=did).first() if did is not None else None
        obj, _ = EvalEloRating.objects.update_or_create(
            organization_id=org_id, model_name=player, dataset=ds,
            defaults={'rating': round(rating, 2)},
        )
        saved[(player, did)] = obj.rating
    # 组织级：把各模型跨数据集的表现聚合成 dataset=None 一条
    org_ratings = {}
    for player, lst in org_players.items():
        org_ratings[player] = 1500.0
    # 用各数据集 Elo 的均值作为组织级初值再互相比（简化：直接取各 player 跨数据集均值）
    agg = defaultdict(list)
    for (player, did), rating in ratings.items():
        agg[player].append(rating)
    for player, vals in agg.items():
        rt = round(sum(vals) / len(vals), 2)
        obj, _ = EvalEloRating.objects.update_or_create(
            organization_id=org_id, model_name=player, dataset=None,
            defaults={'rating': rt},
        )
        org_ratings[player] = obj.rating
    return saved, org_ratings


# ---------------------------------------------------------------------------
# P3-7 评测集饱和监控（区分度低 → 标「饱和」，提示补充难例）
# ---------------------------------------------------------------------------
def dataset_saturation(dataset):
    """M5 看板饱和指数：基于同数据集多次运行 mean_score 的标准差评估区分度。

    区分度越低（运行间分数几乎一致、或普遍满分）→ 评测集已饱和，无法区分模型/运行。
    saturation_index ∈ [0,1]：std>=0.1 → 0（不饱和）；std=0 → 1（完全饱和）。
    确定性、零外送。返回 {saturated, saturation_index, score_std, pass_rate, reason}。
    """
    from .models import EvalRun

    runs = list(
        EvalRun.objects.filter(dataset=dataset, status='DONE')
        .order_by('-created_at')
    )
    if len(runs) < 2:
        return {
            'saturated': False, 'saturation_index': None, 'score_std': None,
            'pass_rate': (runs[0].pass_rate if runs else None),
            'reason': '运行样本不足（<2），无法评估区分度',
        }
    scores = [r.mean_score for r in runs if r.mean_score is not None]
    if len(scores) < 2:
        return {
            'saturated': False, 'saturation_index': None, 'score_std': None,
            'pass_rate': runs[0].pass_rate, 'reason': '有效分样本不足',
        }
    mean = sum(scores) / len(scores)
    var = sum((s - mean) ** 2 for s in scores) / len(scores)
    std = var ** 0.5
    # std>=0.1 视为不饱和(0)；std=0 完全饱和(1)
    saturation_index = round(1 - min(std / 0.1, 1.0), 3)
    latest = runs[0]
    pass_rate = latest.pass_rate
    # 饱和判定：指数高，或满分率极高且方差极小
    saturated = saturation_index >= 0.8 or (
        pass_rate is not None and pass_rate >= 0.98 and std < 0.03
    )
    if saturated:
        reason = '区分度低（运行间分数标准差 %.3f），评测集已饱和，建议补充难例/边缘用例' % std
    else:
        reason = '区分度正常（运行间分数标准差 %.3f）' % std
    return {
        'saturated': saturated,
        'saturation_index': saturation_index,
        'score_std': round(std, 4),
        'pass_rate': pass_rate,
        'reason': reason,
    }


# ---------------------------------------------------------------------------
# P3-14 Copilot 对话入口 + eval-plan-designer
#   自然语言 → 结构化评测方案（dataset_ids / metrics / gate_thresholds /
#   baseline_run_id / repeat_k）。离线确定性启发式（零外送），可选 LLM 升级。
# ---------------------------------------------------------------------------

# 指标关键词 → grader_type（从自然语言需求抽取「评什么维度」）
_METRIC_KEYWORDS = [
    (('工具', 'tool', '调用', 'function', 'api'), 'TOOL_CORRECTNESS'),
    (('计划', '步骤', '流程', 'plan', 'step', '顺序'), 'PLAN_ADHERENCE'),
    (('目标', '完成', '达成', 'goal', 'task', '成功'), 'GOAL_COMPLETION'),
    (('安全', '红队', '攻击', '越权', '注入', 'redteam', 'security'), 'REDTEAM'),
    (('忠实', '幻觉', '编造', 'faithful', 'hallucin'), 'FAITHFULNESS'),
    (('偏见', '歧视', 'bias'), 'BIAS'),
    (('毒性', '有害', '辱骂', 'toxic'), 'TOXICITY'),
    (('相关', '切题', 'relevan'), 'ANSWER_RELEVANCY'),
]

_DEFAULT_GATE = {'mean_score': 0.7, 'pass_rate': 0.8}
_METRIC_CN = {
    'TOOL_CORRECTNESS': '工具调用正确性', 'PLAN_ADHERENCE': '计划遵循度',
    'GOAL_COMPLETION': '目标达成度', 'REDTEAM': '红队/安全', 'FAITHFULNESS': '忠实度',
    'BIAS': '偏见检测', 'TOXICITY': '毒性检测', 'ANSWER_RELEVANCY': '答案相关性',
}


def _select_datasets(req_text, organization):
    """组织内数据集选择与需求最相关的一个（token 重叠），无重叠取最近创建。"""
    from .models import EvalDataset

    dss = list(EvalDataset.objects.filter(organization=organization))
    if not dss:
        return []
    low = _normalize(req_text)
    best, best_score = None, 0
    for d in dss:
        blob = _normalize(f'{d.name} {d.description}')
        score = 0
        # 中文 2 字片段命中
        for i in range(0, max(0, len(low) - 1)):
            if low[i:i + 2] in blob:
                score += 1
        # 整词（空格分隔）命中权重更高
        for tok in re.split(r'\s+', low):
            if len(tok) >= 2 and tok in blob:
                score += 3
        if score > best_score:
            best, best_score = d, score
    if best_score == 0:
        best = max(dss, key=lambda d: d.created_at)
    return [best.id]


def _select_metrics(req_text):
    """从需求抽取指标维度（grader_type）；命中关键词才选，避免过度配置。"""
    low = _normalize(req_text)
    return [gt for kws, gt in _METRIC_KEYWORDS if any(kw in low for kw in kws)]


def _plan_eval_heuristic(req_text, organization):
    """确定性规则模板（零外送）：需求 → 结构化方案。"""
    dataset_ids = _select_datasets(req_text, organization)
    metrics = _select_metrics(req_text)
    repeat_k = 3 if re.search(r'可靠|稳定|重复|多次|pass\^k|repeat|reliab', _normalize(req_text)) else 1

    dataset_names = []
    baseline_run_id = None
    if dataset_ids:
        from .models import EvalDataset, EvalRun
        dataset_names = [
            d.name for d in EvalDataset.objects.filter(id__in=dataset_ids, organization=organization)
        ]
        base = EvalRun.objects.filter(
            dataset_id=dataset_ids[0], organization=organization, is_baseline=True
        ).first()
        baseline_run_id = base.id if base else None

    title = '评测方案：' + ('、'.join(dataset_names) if dataset_names else '（请先创建数据集）')
    summary = (
        f'针对数据集【{("、".join(dataset_names) or "—")}】设计评测：'
        f'核心门禁指标 mean_score/pass_rate'
        + ('，叠加维度：' + '、'.join(_METRIC_CN.get(m, m) for m in metrics) if metrics else '')
        + ('；可靠性重复 %d 次（Pass^k）' % repeat_k if repeat_k > 1 else '；单次执行')
        + ('；已自动关联基线运行 #%d' % baseline_run_id if baseline_run_id
           else '；尚未设置基线（建议先跑一次基线）')
        + '。'
    )
    return {
        'title': title,
        'summary': summary,
        'dataset_ids': dataset_ids,
        'metrics': metrics,
        'gate_thresholds': dict(_DEFAULT_GATE),
        'baseline_run_id': baseline_run_id,
        'repeat_k': repeat_k,
        'mode': 'heuristic',
        'llm_used': False,
    }


def _plan_eval_llm(req_text, organization, llm_config, call_fn):
    """可选 LLM 升级：租户模型产出结构化方案；失败/解析失败降级启发式（数据不出域）。"""
    prompt = (
        '你是评测方案设计专家（eval-plan-designer）。根据需求设计评测方案，'
        '仅返回 JSON 对象，字段：'
        'dataset_ids(整数数组，从组织已有数据集中选最相关的 1 个，无法判断则空数组)、'
        'metrics(字符串数组，从 [TOOL_CORRECTNESS,PLAN_ADHERENCE,GOAL_COMPLETION,REDTEAM,'
        'FAITHFULNESS,BIAS,TOXICITY,ANSWER_RELEVANCY] 中选择相关维度，无则空)、'
        'gate_thresholds(对象，如 {"mean_score":0.7,"pass_rate":0.8})、'
        'repeat_k(整数，1 或 3)、title(中文短标题)、summary(中文一句话方案说明)。'
        f'需求：{req_text}'
    )
    messages = [{'role': 'user', 'content': prompt}]
    try:
        resp = call_fn(llm_config, messages)
        content = resp['choices'][0]['message']['content']
        data = json.loads(re.search(r'\{.*\}', content, re.S).group(0))
        plan = {
            'title': data.get('title') or '评测方案',
            'summary': data.get('summary') or '',
            'dataset_ids': [int(x) for x in (data.get('dataset_ids') or [])],
            'metrics': [str(x) for x in (data.get('metrics') or [])],
            'gate_thresholds': data.get('gate_thresholds') or dict(_DEFAULT_GATE),
            'baseline_run_id': None,
            'repeat_k': int(data.get('repeat_k') or 1),
            'mode': 'llm',
            'llm_used': True,
        }
        # 校验 dataset_ids 归属组织（防越权/幻觉）
        if plan['dataset_ids']:
            from .models import EvalDataset, EvalRun
            valid = set(EvalDataset.objects.filter(
                id__in=plan['dataset_ids'], organization=organization
            ).values_list('id', flat=True))
            plan['dataset_ids'] = [i for i in plan['dataset_ids'] if i in valid]
            base = EvalRun.objects.filter(
                dataset_id=plan['dataset_ids'][0], organization=organization, is_baseline=True
            ).first()
            plan['baseline_run_id'] = base.id if base else None
        return plan
    except Exception:
        return _plan_eval_heuristic(req_text, organization)


def plan_eval(req_text, organization, mode='offline', llm_config=None, call_fn=None):
    """P3-14 入口：自然语言 → 结构化评测方案。

    - mode='offline'（默认）：确定性启发式，零外送。
    - mode='llm'：优先 LLM（租户模型），失败/解析失败自动降级启发式（数据不出域）。
    返回结构见 _plan_eval_heuristic。
    """
    if mode == 'llm' and (llm_config or call_fn):
        return _plan_eval_llm(req_text, organization, llm_config, call_fn)
    return _plan_eval_heuristic(req_text, organization)


# ---------------------------------------------------------------------------
# P3-13 知识中枢 RAG（离线词法检索，零外送、确定性）
#   知识库文本 → 重叠分块 → 词法 token 集合；检索时对 query 做同样 token 化，
#   按 Jaccard 重叠排序取 top_k。不依赖任何外部 embedding 服务。
# ---------------------------------------------------------------------------

# 中文需求/接口文档常见的「需求句」信号词（用于离线生成时从知识片段抽取用例源）
_REQ_SENT_HINTS = re.compile(r'应|需|必须|支持|返回|当|输入|输出|要求|提供|能够|可以|禁止|不允许')


def _tokenize_lex(text):
    """词法 token 集合：ASCII 词 + 中文连续字串的二元组（bigram）。

    二元组对中文短词匹配鲁棒，且纯本地计算（零外送）。
    """
    low = _normalize(text)
    tokens = set(re.findall(r'[a-z0-9_]+', low))
    # 中文（含日文平假名/片假名）连续段 → 二元组
    for seg in re.findall(r'[\u4e00-\u9fff\u3040-\u30ff]+', low):
        for i in range(len(seg) - 1):
            tokens.add(seg[i:i + 2])
        if len(seg) == 1:
            tokens.add(seg)
    return tokens


def _chunk_text(text, size=400, overlap=80):
    """段落感知分块：先按空行分段，贪心打包到 ~size；超长段落按窗口硬切（带 overlap）。"""
    text = (text or '').strip()
    if not text:
        return []
    paras = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    if not paras:
        paras = [text]
    chunks, cur = [], ''
    step = max(1, size - overlap)
    for p in paras:
        if len(cur) + len(p) + 1 <= size:
            cur = (cur + '\n' + p).strip() if cur else p
            continue
        if cur:
            chunks.append(cur)
        if len(p) > size:
            for i in range(0, len(p), step):
                chunks.append(p[i:i + size])
            cur = ''
        else:
            cur = p
    if cur:
        chunks.append(cur)
    return chunks


def build_chunks(content, size=400, overlap=80):
    """将知识文本分块并为每块预计算 token 集合（KnowledgeDoc.save 调用）。

    返回 [{idx, text, tokens}]；tokens 为排序后的词法 token 列表（检索时免重算）。
    """
    texts = _chunk_text(content, size=size, overlap=overlap)
    return [
        {'idx': i, 'text': t, 'tokens': sorted(_tokenize_lex(t))}
        for i, t in enumerate(texts)
    ]


def _extract_requirement_sentences(text):
    """从知识片段抽取候选「需求句」（离线生成用例的补充源）。

    句长 6~120 且含需求信号词；确定性、零外送。
    """
    sents = re.split(r'[。！？\n;；]', text or '')
    out = []
    for s in sents:
        s = s.strip()
        if 6 <= len(s) <= 120 and _REQ_SENT_HINTS.search(s):
            out.append(s)
    return out


def retrieve_knowledge(query, org, top_k=4, knowledge_ids=None):
    """P3-13 核心检索：在 org 的 READY 知识文档 chunks 上做词法重叠排序。

    返回 [{doc_id, doc_title, source_type, chunk_idx, text, score}]（score=Jaccard，降序）。
    确定性、零外送：仅本地 token 集合运算，无外部调用。
    """
    from .models import KnowledgeDoc
    qs = KnowledgeDoc.objects.filter(organization=org, status='READY')
    if knowledge_ids:
        qs = qs.filter(id__in=knowledge_ids)
    q_tokens = _tokenize_lex(query)
    scored = []
    if not q_tokens:
        return scored
    for doc in qs:
        for ch in (doc.chunks or []):
            c_tokens = set(ch.get('tokens') or _tokenize_lex(ch.get('text', '')))
            if not c_tokens:
                continue
            inter = len(q_tokens & c_tokens)
            if inter == 0:
                continue
            union = len(q_tokens | c_tokens)
            jac = inter / union if union else 0
            scored.append({
                'doc_id': doc.id,
                'doc_title': doc.title,
                'source_type': doc.source_type,
                'chunk_idx': ch.get('idx'),
                'text': ch.get('text', ''),
                'score': round(jac, 4),
            })
    scored.sort(key=lambda x: x['score'], reverse=True)
    return scored[:top_k]


def retrieve_for_generation(req_text, org, knowledge_ids=None, top_k=4):
    """检索并拼为可读上下文串（供 LLM 注入）；同时返回原始 hits 供前端展示。

    返回 (context_str, hits)。
    """
    hits = retrieve_knowledge(req_text, org, top_k=top_k, knowledge_ids=knowledge_ids)
    ctx = '\n---\n'.join(
        f'[来源:{h["doc_title"]}]({h["source_type"]}) {h["text"]}' for h in hits
    )
    return ctx, hits
