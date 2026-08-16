"""
P3-11 评判模型强度（Judge Strength Self-Calibration）。

问题背景（对标文章二 / Giskard / DeepEval 的「裁判可信度」）：
LLM-as-Judge 是评测结论的核心来源，但其本身可能「弱」——对明显正确/错误的输出
给出错误裁决。若不量化裁判强度，评测结论的可信度无法保证（「用不可信的裁判打分」）。

设计：
- GOLDEN_CALIBRATION：内置「金标准校准集」——一组人工确认、结论无歧义的样本
  （input/expected/output + 人工标注的 golden_passed）。
- assess_judge_strength(llm_config, call_fn)：让被评估的评判模型对校准集中每个样本
  独立裁决（复用 graders.llm_judge_grade 的 LLM 路径），与 golden_passed 比对，
  计算 strength_score（一致性 0-1）/ agreement / sample_size。
- 全程零外送（call_fn 可注入做离线测试；生产走本租户 AIModelConfig，数据不出域）。
- 未配置评判模型（llm_config=None 且无 call_fn）→ 无法校准，返回 None，由调用方 400。
"""

# 金标准校准集：结论无歧义的人工标注样本（input / expected / output / 人工裁决）。
# 由 4 个「应通过」+ 4 个「应失败」组成，便于直观检验裁判是否「放水」或「过苛」。
GOLDEN_CALIBRATION = [
    {
        'id': 'GC01', 'input_text': '查询北京今天的天气', 'expected': '北京今天晴',
        'output': '北京今天晴，气温 25 度，适合出行', 'golden_passed': True,
        'note': '输出包含预期关键信息，应判通过',
    },
    {
        'id': 'GC02', 'input_text': '把 hello 翻译成中文', 'expected': '你好',
        'output': '你好', 'golden_passed': True,
        'note': '翻译正确，应判通过',
    },
    {
        'id': 'GC03', 'input_text': '计算 2 + 3 的结果', 'expected': '5',
        'output': '结果是 5', 'golden_passed': True,
        'note': '计算正确，应判通过',
    },
    {
        'id': 'GC04', 'input_text': '判断 7 是否为质数', 'expected': '是质数',
        'output': '7 只能被 1 和自身整除，是质数', 'golden_passed': True,
        'note': '结论正确，应判通过',
    },
    {
        'id': 'GC05', 'input_text': '把 hello 翻译成中文', 'expected': '你好',
        'output': 'bonjour（法语）', 'golden_passed': False,
        'note': '翻译错误，应判失败',
    },
    {
        'id': 'GC06', 'input_text': '计算 2 + 3 的结果', 'expected': '5',
        'output': '结果是 6', 'golden_passed': False,
        'note': '计算错误，应判失败',
    },
    {
        'id': 'GC07', 'input_text': '提取用户姓名', 'expected': '张三',
        'output': '该用户名为李四', 'golden_passed': False,
        'note': '提取结果与预期不符，应判失败',
    },
    {
        'id': 'GC08', 'input_text': '总结下面这段话的要点', 'expected': '要点一：A；要点二：B',
        'output': '这段内容与主题无关，无法总结', 'golden_passed': False,
        'note': '未达成预期总结，应判失败',
    },
]


class _GoldenCase:
    """最小用例对象，仅提供 graders.llm_judge_grade 所需的 input_text / expected。"""

    def __init__(self, input_text, expected):
        self.input_text = input_text
        self.expected = expected
        self.is_edge = False


def assess_judge_strength(llm_config=None, call_fn=None, golden=None):
    """评估评判模型与金标准的一致性。

    参数：
    - llm_config：AIModelConfig（生产走本租户 for_tenant）；与 call_fn 至少其一非空。
    - call_fn：可注入的 LLM 调用（测试用，确定性产出）。
    - golden：覆盖默认 GOLDEN_CALIBRATION（测试用）。

    返回 {'strength_score': 0-1, 'agreement': int, 'sample_size': int}；
    若无任何可调用的评判来源（llm_config 与 call_fn 均为空）→ 返回 None（无法校准）。

    对校准集中每个样本独立调用 graders.llm_judge_grade（仅取 passed 与 golden_passed 比对），
    统计一致比例作为 strength_score。零外送、不落库（落库由 ViewSet 负责）。
    """
    from . import graders

    if llm_config is None and call_fn is None:
        return None

    items = golden if golden is not None else GOLDEN_CALIBRATION
    if not items:
        return {'strength_score': 0.0, 'agreement': 0, 'sample_size': 0}

    agreement = 0
    for item in items:
        case = _GoldenCase(item['input_text'], item['expected'])
        # 仅取裁决的 passed（LLM 路径；call_fn 注入时走 LLM_JUDGE）
        verdict = graders.llm_judge_grade(
            case, item['output'], rubric=None, config=llm_config, call_fn=call_fn
        )
        passed = verdict[1]
        if passed == bool(item['golden_passed']):
            agreement += 1

    total = len(items)
    strength_score = round(agreement / total, 3) if total else 0.0
    return {
        'strength_score': strength_score,
        'agreement': agreement,
        'sample_size': total,
    }
