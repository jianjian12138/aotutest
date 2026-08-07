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


def _offline_generate(req_text):
    """离线启发式生成（零外送、确定性）。"""
    cases = []
    for item in _split_items(req_text):
        input_text, expected = _parse_item(item)
        code = 'req-' + hashlib.md5(item.encode('utf-8')).hexdigest()[:8]
        cases.append({
            'code': code,
            'input_text': input_text,
            'expected': expected,
            'is_edge': _is_edge(item),
            'meta': {'source': 'offline', 'raw': item[:200]},
        })
    return cases


def _llm_generate(req_text, llm_config, call_fn):
    """可选 LLM 升级：调用租户模型生成更丰富用例，解析为稳定中间格式。

    调用失败或解析失败由调用方负责降级回离线（保证确定性、零外送）。
    """
    messages = [
        {
            'role': 'system',
            'content': (
                '你是评测用例生成专家。根据需求生成结构化评测用例，'
                '仅返回 JSON 数组，每项含 input_text(输入/提示)、expected(期望输出)、'
                'is_edge(是否边缘/对抗用例)。不要输出解释。'
            ),
        },
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
            'meta': {'source': 'llm'},
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


def generate_cases(req_text, mode='offline', llm_config=None, call_fn=None):
    """B1 用例生成 Agent：需求 → 稳定中间格式 EvalCase 列表。

    离线（默认，零外送）或 LLM 升级；LLM 失败确定性降级离线。
    """
    if mode == 'llm' and (llm_config or call_fn):
        try:
            return _llm_generate(req_text, llm_config, call_fn)
        except Exception:
            return _offline_generate(req_text)
    return _offline_generate(req_text)


_JUDGE_HINTS = {
    'RULE': '规则用例存在结构性失败，检查 expected 与 rubric 是否匹配',
    'LLM_JUDGE': 'LLM 裁判类结果存在系统性偏差，建议复核评分提示',
    'HEURISTIC': '离线启发式结果需经 HITL 人工复核确认',
}


def analyze_run(run):
    """B3 分析 Agent：跨用例模式识别（系统性失败定位），复用已有评分结果。"""
    results = list(run.results.all())
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
    return {'total': len(results), 'patterns': patterns}


def compare_to_baseline(run, baseline_run, regress_delta=0.05):
    """B4 确定性基线对比：当前 run vs baseline（同 dataset）。定位劣化指标。"""
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


def eval_gate(run, thresholds, baseline_run=None, regress_delta=0.05):
    """C1 质量门禁：阈值 + 回归拦截，指出掉哪个指标。"""
    failed = []
    for metric, thr in (thresholds or {}).items():
        val = getattr(run, metric)
        if val is None:
            continue
        if val < thr:
            failed.append({'metric': metric, 'value': val, 'threshold': thr})
    regressed_metrics = []
    if baseline_run:
        cmp = compare_to_baseline(run, baseline_run, regress_delta)
        for m, d in cmp['diffs'].items():
            if d['delta'] < -regress_delta:
                regressed_metrics.append({'metric': m, 'delta': d['delta']})
    return {
        'passed': not (failed or regressed_metrics),
        'failed_thresholds': failed,
        'regressed_metrics': regressed_metrics,
    }
