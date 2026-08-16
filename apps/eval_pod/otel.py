"""P3-8 OTel 回流：将 OpenTelemetry / JSON trace 转为平台内部的 EvalTrace。

背景
----
路线三把「Trace 观测」作为失败归因的核心（区分「规划弱」与「工具错」，见 M4 / P3-15）。
但真实 agent 框架（LangChain / LlamaIndex / AutoGen / 自建 harness）普遍用 OTel 导出
span，形态与平台 `EvalTraceStep.STEP_TYPES`（PLAN/TOOL/OBSERVE/OUTPUT/ERROR）并不一致。

本模块负责把外部 OTel 形态的 trace「回流」成平台内部模型，做到：
  ① 多形态兼容——标准 OTLP/JSON、简化包裹、裸 span 列表都能吃；
  ② 类型推导——把任意 span 名/属性/kind 映射回 5 类语义步骤；
  ③ 零外送——纯本地转换，不经过任何 LLM；
  ④ 租户安全——落库前由调用方（ViewSet.ingest）完成 run/case 的租户校验，
     本模块只做「写」，不负责鉴权。

与现有 `export` 动作互补：`export` 把内部 trace 导出成 Langfuse/OTel 风格 JSON；
`otel.ingest_otlp` 则是反向——把外部 OTel 导回内部，形成闭环（对标 One-Eval / Opik 的
trace 导入能力）。
"""

from datetime import datetime

from django.utils import timezone

from .models import EvalTrace, EvalTraceStep

__all__ = ['ingest_otlp', 'extract_spans']

# 语义关键词 → 步骤类型（按优先级从上到下命中）
_PLAN_KEYWORDS = ('plan', 'planning', 'reason', 'think', 'deliberat', 'reflect')
_TOOL_KEYWORDS = (
    'tool', 'function', 'action', 'execute', 'exec', 'call', 'invoke',
    'api', 'retriev', 'search', 'rag', 'db', 'query', 'sql', 'http', 'request',
)
_OUTPUT_KEYWORDS = (
    'output', 'final', 'answer', 'response', 'complete', 'result', 'summary',
    'generate', 'reply', 'render',
)
_OBSERVE_KEYWORDS = ('observe', 'observation', 'perceive', 'sense', 'read', 'fetch')


def _attrs_to_dict(attributes):
    """把 OTLP 属性数组 [{key, value:{typeValue}}] 拍平成普通 dict；兼容已是 dict 的情况。

    OTLP/JSON 的属性值是「any value」结构，形如 {"stringValue": "x"} / {"intValue": 3}。
    这里取第一个已知值类型；未知则原样保留。
    """
    if not attributes:
        return {}
    if isinstance(attributes, dict):
        return attributes
    out = {}
    for a in attributes:
        if not isinstance(a, dict):
            continue
        k = a.get('key')
        if k is None:
            continue
        v = a.get('value', {})
        if isinstance(v, dict):
            for vk in ('stringValue', 'intValue', 'doubleValue', 'boolValue', 'arrayValue', 'kvlistValue'):
                if vk in v:
                    out[k] = v[vk]
                    break
            else:
                out[k] = v
        else:
            out[k] = v
    return out


def extract_spans(payload):
    """从多种形态的 OTel/JSON payload 中提取 span 列表（统一原样返回）。

    支持三种形态：
      ① 标准 OTLP/JSON: {"resourceSpans":[{"scopeSpans":[{"spans":[...]}]}]}
      ② 简化包裹:        {"spans":[...]}
      ③ 裸列表:          [{"name":..., ...}, ...]
      ④ 单条 span dict:   {"name":..., "startTimeUnixNano":..., ...}
    """
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        raise ValueError('OTel payload 须为 dict 或 list')
    if 'resourceSpans' in payload:
        spans = []
        for rs in payload['resourceSpans']:
            for ss in (rs.get('scopeSpans') or []):
                spans.extend(ss.get('spans') or [])
        return spans
    if 'spans' in payload:
        return payload['spans']
    # 单条 span
    return [payload]


def _to_ms(value):
    """把一个时间值转成毫秒（int）。

    处理：OTLP 纳秒字符串/整数、epoch 秒、epoch 毫秒、ISO 字符串。
    无法解析时返回 None（不影响其余字段）。
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if value > 1e15:           # 纳秒 → ms
            return round(value / 1e6)
        if value > 1e9:            # 秒级 epoch（10 位）→ ms；毫秒 epoch(~1.7e12) 走下支
            return round(value * 1000)
        return round(value)        # 毫秒（或更小量纲）
    if isinstance(value, str):
        s = value.strip()
        if s.isdigit():
            return _to_ms(int(s))
        try:
            dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
            return int(dt.timestamp() * 1000)
        except Exception:
            return None
    return None


def _span_duration_ms(span):
    """解析单个 span 的耗时（ms）。优先 OTLP 纳秒字符串，其次通用名称/字段。"""
    # ① OTLP/JSON 纳秒字符串（最可能路径）
    start = span.get('startTimeUnixNano') or span.get('start_time_unix_nano')
    end = span.get('endTimeUnixNano') or span.get('end_time_unix_nano')
    if start is not None and end is not None:
        try:
            return max(0, round((int(end) - int(start)) / 1e6))
        except (ValueError, TypeError):
            pass
    # ② 通用字段：epoch ms / s / ISO
    start_ms = _to_ms(span.get('start_time') or span.get('startTime') or span.get('start'))
    end_ms = _to_ms(span.get('end_time') or span.get('endTime') or span.get('end'))
    if start_ms is not None and end_ms is not None:
        return max(0, end_ms - start_ms)
    # ③ 直接给了 duration
    dur = span.get('duration_ms') or span.get('duration')
    if dur is not None:
        dm = _to_ms(dur)
        if dm is not None:
            return max(0, dm)
    return None


def _span_error(span):
    """提取 span 的错误信息（status=ERROR 或 exception 事件）。无则返回空串。"""
    status = span.get('status')
    if isinstance(status, dict):
        code = (status.get('code') or '').upper()
        msg = status.get('message') or ''
        if code in ('STATUS_CODE_ERROR', 'ERROR'):
            return msg or 'span status=ERROR'
    elif isinstance(status, str) and status.upper() in ('STATUS_CODE_ERROR', 'ERROR'):
        return 'span status=ERROR'
    # exception / error 事件
    for ev in (span.get('events') or []):
        name = (ev.get('name') or '').lower()
        if 'exception' in name or 'error' in name:
            attrs = _attrs_to_dict(ev.get('attributes'))
            exc = (
                attrs.get('exception.message')
                or attrs.get('exception.type')
                or ev.get('name')
            )
            return str(exc)
    return ''


def _span_type(span):
    """把任意 span 推导回 5 类语义步骤（PLAN/TOOL/OBSERVE/OUTPUT/ERROR）。

    优先级：span 名关键词 → gen_ai.operation.name → span kind。
    默认 OBSERVE（最中性，避免误判成错误）。
    """
    name = (span.get('name') or '').lower()
    kind = (span.get('kind') or '').upper()
    attrs = _attrs_to_dict(span.get('attributes'))

    if any(k in name for k in _PLAN_KEYWORDS):
        return 'PLAN'
    if any(k in name for k in _TOOL_KEYWORDS):
        return 'TOOL'
    if any(k in name for k in _OUTPUT_KEYWORDS):
        return 'OUTPUT'
    if any(k in name for k in _OBSERVE_KEYWORDS):
        return 'OBSERVE'

    op = attrs.get('gen_ai.operation.name')
    if op in ('execute_tool', 'call_tool', 'function_call'):
        return 'TOOL'
    if op in ('generate_content', 'chat', 'completion'):
        return 'OUTPUT'
    if op in ('retrieve', 'vector_search'):
        return 'TOOL'

    # 客户端/生产者/消费者 span 通常代表一次 outbound 调用 → 工具
    if kind in ('SPAN_KIND_CLIENT', 'SPAN_KIND_PRODUCER', 'SPAN_KIND_CONSUMER'):
        return 'TOOL'
    return 'OBSERVE'


def _as_json(value):
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        return {'text': value}
    return {'value': value}


def _span_input(span):
    """尽量抽取 span 的输入（prompt / input / 属性摘要）。"""
    if 'input' in span and isinstance(span['input'], (dict, list, str)):
        return _as_json(span['input'])
    attrs = _attrs_to_dict(span.get('attributes'))
    if 'gen_ai.prompt' in attrs:
        return {'prompt': attrs['gen_ai.prompt']}
    if attrs:
        # 仅保留轻量、可序列化的属性，避免把超大资源属性灌进 input_data
        slim = {k: v for k, v in attrs.items() if not isinstance(v, (dict, list))}
        return slim
    return {}


def _span_output(span):
    """尽量抽取 span 的输出（completion / output / status.message）。"""
    if 'output' in span and isinstance(span['output'], (dict, list, str)):
        return _as_json(span['output'])
    attrs = _attrs_to_dict(span.get('attributes'))
    if 'gen_ai.completion' in attrs:
        return {'completion': attrs['gen_ai.completion']}
    status = span.get('status')
    if isinstance(status, dict) and status.get('message'):
        return {'status_message': status['message']}
    return {}


def ingest_otlp(run, case, payload):
    """将 OTel/JSON trace 回流为 EvalTrace + EvalTraceStep。

    参数
    ----
    run  : EvalRun 实例（调用方须保证其属于当前租户）
    case : EvalCase 实例（调用方须保证 case.dataset_id == run.dataset_id）
    payload: OTLP/JSON dict、{"spans":[...]}、或裸 span 列表

    返回
    ----
    新建的 EvalTrace 实例。

    聚合规则
    --------
    - total_latency_ms = max(span 结束) - min(span 起始)（绝对时间差，跨 span 串联）
    - status = ERROR 当且仅当任一 span 含错误（status=ERROR 或 exception 事件）
    - 步骤按输入顺序（span 列表顺序）落库 step_index=0,1,2...（回放按此序）
    """
    spans = extract_spans(payload)
    if not spans:
        raise ValueError('OTel payload 未包含任何 span，无法回流')

    steps = []
    min_start = None
    max_end = None
    trace_error = ''

    for idx, span in enumerate(spans):
        dur = _span_duration_ms(span)
        err = _span_error(span)
        stype = _span_type(span)
        # 类型兜底：无明确语义且本身出错 → 标为 ERROR（失败点高亮依赖 error 字段，
        # 即便保留原语义类型也会被 _trace_replay 判为失败；这里只在不冲突时改标 ERROR）
        if err and stype == 'OBSERVE':
            stype = 'ERROR'
        if err and not trace_error:
            trace_error = err

        s_ms = _to_ms(
            span.get('startTimeUnixNano') or span.get('start_time')
            or span.get('startTime') or span.get('start')
        )
        e_ms = _to_ms(
            span.get('endTimeUnixNano') or span.get('end_time')
            or span.get('endTime') or span.get('end')
        )
        if s_ms is not None:
            min_start = s_ms if min_start is None else min(min_start, s_ms)
        if e_ms is not None:
            max_end = e_ms if max_end is None else max(max_end, e_ms)

        name = (span.get('name') or f'step-{idx}')[:200]
        steps.append({
            'step_index': idx,
            'step_type': stype,
            'name': name,
            'input_data': _span_input(span),
            'output_data': _span_output(span),
            'latency_ms': dur,
            'error': err,
        })

    total = (max_end - min_start) if (min_start is not None and max_end is not None) else None

    trace = EvalTrace.objects.create(
        run=run,
        case=case,
        status='ERROR' if trace_error else 'OK',
        total_latency_ms=total,
        finished_at=timezone.now(),
    )
    for s in steps:
        EvalTraceStep.objects.create(trace=trace, **s)
    return trace
