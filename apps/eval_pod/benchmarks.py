"""
E7 标准 Benchmark 模板目录（文章二 Benchmark 选型）。

平台级目录由 `ensure_benchmark_catalog()` 幂等播种（在 apps.ready 中调用）。
租户可通过 datasets/from_template/ 基于 catalog 生成 EvalDataset + 用例骨架。

选型要点（对标文章二）：
- τ-bench 专测 Pass^k（可靠性下限）→ measures_pass_k=True，引导门禁用 pass_k_rate。
- SWE-bench / GAIA / WebArena / AgentBench / OSWorld 覆盖代码/通用/网页/多任务/桌面场景。
"""
from django.db.models import Q

from .models import BenchmarkTemplate

# 平台级目录定义（organization=None）
CATALOG = [
    {
        'key': 'swe-bench', 'name': 'SWE-bench（代码修复）', 'source': 'SWE-BENCH',
        'description': '真实 GitHub Issue + PR 修复，衡量 agent 端到端写代码能力。',
        'dimensions': ['完成率', '补丁正确性', '测试通过率'],
        'measures_pass_k': False,
        'case_skeleton': [
            {'input_text': '修复仓库中的 issue：{issue_title}', 'expected': '通过全部单元测试的 PR',
             'is_edge': False, 'meta': {'task_type': 'code_fix'}},
        ],
    },
    {
        'key': 'gaia', 'name': 'GAIA（通用 AI 助手）', 'source': 'GAIA',
        'description': '需多步推理+工具使用的真实问题，覆盖网页/文件/表格等。',
        'dimensions': ['完成率', '工具准确率', '推理正确性'],
        'measures_pass_k': False,
        'case_skeleton': [
            {'input_text': '请回答并给出依据：{question}', 'expected': '{answer}',
             'is_edge': False, 'meta': {'task_type': 'qa'}},
        ],
    },
    {
        'key': 'webarena', 'name': 'WebArena（网页智能体）', 'source': 'WEBARENA',
        'description': '在真实网站环境中完成多步操作任务。',
        'dimensions': ['完成率', '操作正确性', '状态一致性'],
        'measures_pass_k': False,
        'case_skeleton': [
            {'input_text': '在站点上完成：{task}', 'expected': '任务状态变为已完成',
             'is_edge': False, 'meta': {'task_type': 'web_task'}},
        ],
    },
    {
        'key': 'tau-bench', 'name': 'τ-bench（可靠性/用户-工具交互）', 'source': 'TAU-BENCH',
        'description': '用户-工具多轮交互，专测 Pass^k：同一任务重复多次须全部成功（可靠性下限）。',
        'dimensions': ['Pass^k 可靠性', '工具准确率', '策略遵循'],
        'measures_pass_k': True,
        'case_skeleton': [
            {'input_text': '与系统交互完成用户请求：{request}', 'expected': '请求被正确处理且幂等',
             'is_edge': True, 'meta': {'task_type': 'user_tool', 'reliability_critical': True}},
        ],
    },
    {
        'key': 'agentbench', 'name': 'AgentBench（多环境智能体）', 'source': 'AGENTBENCH',
        'description': '跨 OS/数据库/知识图谱等多环境的综合评测。',
        'dimensions': ['完成率', '环境适配', '规划质量'],
        'measures_pass_k': False,
        'case_skeleton': [
            {'input_text': '在 {env} 环境中完成：{task}', 'expected': '{expected}',
             'is_edge': False, 'meta': {'task_type': 'env_task'}},
        ],
    },
    {
        'key': 'osworld', 'name': 'OSWorld（桌面 GUI 智能体）', 'source': 'OSWORLD',
        'description': '真实桌面 OS 图形界面多步任务。',
        'dimensions': ['完成率', 'GUI 操作正确性', '长程规划'],
        'measures_pass_k': False,
        'case_skeleton': [
            {'input_text': '在桌面完成：{task}', 'expected': '{expected}',
             'is_edge': True, 'meta': {'task_type': 'gui_task'}},
        ],
    },
]


def ensure_benchmark_catalog():
    """幂等播种平台级（organization=None）Benchmark 目录。"""
    for spec in CATALOG:
        BenchmarkTemplate.objects.update_or_create(
            organization=None, key=spec['key'],
            defaults={
                'name': spec['name'], 'source': spec['source'],
                'description': spec['description'],
                'dimensions': spec['dimensions'],
                'measures_pass_k': spec['measures_pass_k'],
                'case_skeleton': spec['case_skeleton'],
            },
        )


def list_templates_for(org):
    """返回某租户可见的模板（平台级 + 本租户私有）。"""
    if org is None:
        q = Q(organization__isnull=True)
    else:
        q = Q(organization__isnull=True) | Q(organization=org)
    return list(BenchmarkTemplate.objects.filter(q))
