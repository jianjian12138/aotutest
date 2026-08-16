"""
E8 Harness 抽象层（文章一 3 轴 LLM×Harness×Environment）。

把「只评 LLM」升级为「评 Agent」：评测对象不再是单次 prompt→completion，
而是「环境 env → 被测 agent（经 harness 驱动）→ 轨迹 trace → 评分器 grade」的闭环。

协议（借鉴 Inspect AI 的 Solver/Scorer + Env 概念）：
    harness.reset(env)            -> state      # 初始化/重置被测环境
    harness.run(state, agent, case) -> (output, trace_steps)  # 驱动 agent 跑一个用例
    harness.grade(state, output, case, grader) -> verdict     # 评分（复用 graders 引擎）

本模块只提供契约与最小实现（NoOpHarness），真正接入被测 agent 由各团队实现子类。
评测舱现有 run action 仍以「调用方提供 outputs」为主；引入 harness 后可让 agent 在
闭环环境里自驱产生 outputs 与 trace（M4 归因数据），无需改现有评分链路。

P3-6 新增两类可直接落地的 harness：
- MockHarness：三种确定性模式（expected/echo/fail），零外送，用于 CI 冒烟与回归基线。
- RealHarness：真实驱动被测 agent（agent_fn 注入优先，否则 AIModelConfig 同步调用）。
两者都产出步骤级 trace（PLAN→TOOL→OBSERVE→OUTPUT），供 M4 回放与 E5 崩溃归因。
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple


class HarnessAdapter(ABC):
    """被测 agent 适配器基类。子类实现 reset/run/grade 三件套。"""

    @abstractmethod
    def reset(self, env: Dict[str, Any]) -> Dict[str, Any]:
        """初始化/重置被测环境，返回可变 state。"""
        raise NotImplementedError

    @abstractmethod
    def run(self, state: Dict[str, Any], agent: Any, case: Any) -> Tuple[str, List[Dict[str, Any]]]:
        """驱动被测 agent 跑一个用例，返回 (最终输出, 步骤级 trace_steps)。

        trace_steps 形态对齐 EvalTraceStep：[{step_index, step_type, name,
        input_data, output_data, latency_ms, error}]，供 M4 回放与 E5 崩溃归因。
        """
        raise NotImplementedError

    def grade(self, state: Dict[str, Any], output: str, case: Any, grader_config: Any,
              llm_config=None, call_fn=None) -> Dict[str, Any]:
        """评分：默认复用平台 graders 引擎（保持 reason 强制非空、离线降级）。"""
        from . import graders
        score, passed, reason, judge = graders.grade_case(
            case, output, grader_config, llm_config=llm_config, call_fn=call_fn
        )
        return {'score': score, 'passed': passed, 'reason': reason, 'judge': judge}


class NoOpHarness(HarnessAdapter):
    """最小可用实现：将 case.input_text 直接作为 output，产生单步 OBSERVE trace。

    用于离线演示与单测，证明 harness 协议可串起来而不依赖真实 agent/环境。
    """

    def reset(self, env: Dict[str, Any]) -> Dict[str, Any]:
        return dict(env or {})

    def run(self, state: Dict[str, Any], agent: Any, case: Any) -> Tuple[str, List[Dict[str, Any]]]:
        output = getattr(case, 'input_text', str(case))
        steps = [{
            'step_index': 0,
            'step_type': 'OBSERVE',
            'name': 'noop-echo',
            'input_data': {'case': getattr(case, 'id', None)},
            'output_data': {'output': output},
            'latency_ms': 0,
            'error': '',
        }]
        return output, steps


def _trace_steps(case, output, tool_name, latency_tool_ms=2, error=''):
    """构造 4 步确定性 trace（PLAN→TOOL→OBSERVE→OUTPUT），供 M4 回放 / E5 归因。

    统一形态对齐 EvalTraceStep 字段；error 非空时 TOOL 步骤标记错误（不影响步骤数）。
    """
    return [
        {
            'step_index': 0,
            'step_type': 'PLAN',
            'name': 'plan',
            'input_data': {'case_id': getattr(case, 'id', None)},
            'output_data': {'plan': f'produce output via {tool_name}'},
            'latency_ms': 1,
            'error': '',
        },
        {
            'step_index': 1,
            'step_type': 'ERROR' if error else 'TOOL',
            'name': tool_name,
            'input_data': {'input_text': getattr(case, 'input_text', '')},
            'output_data': {'output': output},
            'latency_ms': latency_tool_ms,
            'error': error or '',
        },
        {
            'step_index': 2,
            'step_type': 'OBSERVE',
            'name': 'observe',
            'input_data': {},
            'output_data': {'produced': bool(output)},
            'latency_ms': 0,
            'error': '',
        },
        {
            'step_index': 3,
            'step_type': 'OUTPUT',
            'name': 'output',
            'input_data': {},
            'output_data': {'output': output},
            'latency_ms': 1,
            'error': '',
        },
    ]


class MockHarness(HarnessAdapter):
    """P3-6 E2E Mock harness：三种确定性模式产出 output，零外送。

    - expected：output = case.expected → RULE(contains) 全通过（适合建立确定性基线）。
    - echo：output = case.input_text（回显，验证链路但不保证通过）。
    - fail：output = '' → RULE 全失败（验证门禁能"说不"）。
    每个用例产生 PLAN→TOOL→OBSERVE→OUTPUT 步骤级 trace（M4 归因），TOOL=合成 agent。
    """

    MODES = ('expected', 'echo', 'fail')

    def __init__(self, mock_mode: str = 'expected'):
        if mock_mode not in self.MODES:
            mock_mode = 'expected'
        self.mock_mode = mock_mode

    def reset(self, env: Dict[str, Any]) -> Dict[str, Any]:
        return dict(env or {})

    def run(self, state: Dict[str, Any], agent: Any, case: Any) -> Tuple[str, List[Dict[str, Any]]]:
        if self.mock_mode == 'expected':
            output = getattr(case, 'expected', '') or ''
            tool_name = 'mock-expected'
        elif self.mock_mode == 'echo':
            output = getattr(case, 'input_text', str(case)) or ''
            tool_name = 'mock-echo'
        else:  # fail
            output = ''
            tool_name = 'mock-fail'
        steps = _trace_steps(case, output, tool_name)
        return output, steps


class RealHarness(HarnessAdapter):
    """P3-6 E2E Real harness：真实驱动被测 agent，产生真实 output + trace。

    优先级：① agent_fn 注入（测试/生产真实 agent 封装，callable 接收 input_text 返回 output）
    ② AIModelConfig（经 runners.call_model_sync 同步调用 OpenAI 兼容端点）
    均无 → 返回空串 + ERROR 步骤（编排层在调用前校验，这里兜底防静默成功）。
    步骤级 trace 真实反映 agent 调用（PLAN→TOOL(真实调用)→OBSERVE→OUTPUT）。
    """

    def __init__(self, config: Any = None, agent_fn: Any = None):
        self.config = config
        self.agent_fn = agent_fn

    def reset(self, env: Dict[str, Any]) -> Dict[str, Any]:
        return dict(env or {})

    def run(self, state: Dict[str, Any], agent: Any, case: Any) -> Tuple[str, List[Dict[str, Any]]]:
        from . import runners

        input_text = getattr(case, 'input_text', str(case)) or ''
        tool_name = 'real-agent-call'

        if self.agent_fn is not None:
            try:
                output = self.agent_fn(input_text)
            except Exception as exc:  # noqa: BLE001
                steps = _trace_steps(case, '', tool_name, error=f'agent_fn error: {exc}')
                return '', steps
        elif self.config is not None:
            output = runners.call_model_sync(self.config, input_text)
        else:
            steps = _trace_steps(case, '', tool_name, error='no agent configured (agent_fn/config)')
            return '', steps

        if output is None:
            output = ''
        steps = _trace_steps(case, output, tool_name, latency_tool_ms=50)
        return output, steps
