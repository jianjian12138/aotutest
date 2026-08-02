import logging

from backend.utils.sandbox import safe_exec

logger = logging.getLogger(__name__)


class SkillsService:
    """
    Skills Service for executing dynamic Python code snippets.

    安全说明：技能代码一律通过 backend.utils.sandbox.safe_exec 受限执行——
    白名单 builtins/模块、禁止 os/sys/subprocess、stdout 截断、超时控制。
    技能代码本身仅允许管理员配置（见 agent 配置视图的权限控制）。
    """

    @staticmethod
    def execute_skill(code, context=None, timeout=30):
        """
        Execute a Python skill with a given context inside the sandbox.
        """
        result = safe_exec(code, context=context, timeout=timeout)
        if result.get('success'):
            return {
                'success': True,
                'output': result.get('output', ''),
                'result': result.get('result'),
            }
        return {
            'success': False,
            'error': result.get('error', 'unknown error'),
            'traceback': result.get('traceback', ''),
        }
