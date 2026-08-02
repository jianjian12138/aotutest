"""
受限 Python 代码执行沙箱。

用于替代平台内所有裸 exec() 调用（技能执行、公共方法调试、前后置脚本等）。
安全策略：
1. 白名单 builtins —— 移除 eval/exec/compile/open/__import__ 等危险内建；
2. 白名单模块导入 —— 仅允许 json/re/time/datetime/math/random/uuid/hashlib/base64 等纯计算模块；
3. 禁止 os/sys/subprocess/socket/importlib/ctypes 等系统级模块；
4. 执行超时控制（通过子线程 + join 超时实现，超时后标记失败）；
5. stdout 捕获且限制输出体积。

6. AST 静态校验 —— 拒绝任何下划线开头的属性访问（拦截
   `().__class__.__bases__[0].__subclasses__()` 一类的沙箱逃逸链）；
7. 移除 getattr/setattr/delattr —— 防止用字符串拼接绕过 AST 属性检查。

注意：这不是操作系统级隔离，纵深防御仍需配合：
- 仅管理员可配置可执行代码（见 views 层权限）；
- 生产环境建议将执行迁移至独立容器/进程池。
"""
import ast
import io
import sys
import logging
import threading
import traceback
import builtins as _builtins

logger = logging.getLogger(__name__)

# 允许导入的模块白名单（纯计算/数据处理类）
ALLOWED_MODULES = frozenset({
    'json', 're', 'time', 'datetime', 'math', 'random', 'uuid',
    'hashlib', 'base64', 'string', 'decimal', 'fractions',
    'itertools', 'functools', 'collections', 'copy', 'statistics',
    'urllib.parse', 'html', 'textwrap', 'unicodedata',
    # 测试常用第三方（只读、安全）
    'faker', 'jsonpath_ng',
})

# 危险内建函数黑名单（从 builtins 白名单中剔除）
_BLOCKED_BUILTINS = frozenset({
    'eval', 'exec', 'compile', 'open', 'input', 'breakpoint',
    'exit', 'quit', 'help', 'memoryview', 'globals', 'locals', 'vars',
    '__import__',
    # 反射/元类逃逸面：
    # - getattr/setattr/delattr 可用字符串拼接绕过 AST 下划线属性检查
    # - type 可构造元类、访问 __subclasses__
    # - super/object 可作为攀爬 MRO 的起点
    'getattr', 'setattr', 'delattr', 'type', 'super', 'object',
    'classmethod', 'staticmethod', 'property',
    # 运行时字符串属性解析逃逸面：
    # str.format / str.format_map 会在运行时解析 "{x.__class__}" 形式的字段，
    # 完全绕过源码级 AST 下划线属性检查，是经典沙箱逃逸通道。
    # 封禁后用户改用 f-string（仍受 AST 检查）或显式拼接。
    'format', 'format_map',
})

# 运行时字符串属性解析的“方法名”黑名单（配合 AST 拦截）
# 形如 `"{x.__class__}".format(x)` 的调用在源码里只是一次普通方法调用，
# AST 静态校验只能看到 Attribute 节点（format），看不到字符串内部的 __class__ 访问，
# 故需在 AST 阶段直接拒绝对 .format / .format_map 的调用。
_BLOCKED_STR_METHODS = frozenset({'format', 'format_map'})

# 允许的少数 dunder 属性（常规业务代码可能用到）
_ALLOWED_DUNDER_ATTRS = frozenset({'__init__', '__str__', '__repr__', '__len__', '__name__', '__doc__'})


class SandboxSecurityError(Exception):
    """代码未通过沙箱静态安全校验。"""


def _validate_ast(code):
    """
    AST 静态校验：拒绝以下模式，拦截主流沙箱逃逸链——
    - 访问任何以下划线开头的属性（如 __class__/__bases__/__subclasses__/__globals__/
      __mro__/__dict__/func.__code__ 等），少量常规 dunder 除外；
    - import 语句中的非白名单模块（运行期 _safe_import 双保险）。
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise SandboxSecurityError(f'代码语法错误: {e}') from e

    for node in ast.walk(tree):
        # 属性访问检查：obj._x / obj.__x__ 一律拒绝（白名单 dunder 除外）
        if isinstance(node, ast.Attribute):
            attr = node.attr
            if attr.startswith('_') and attr not in _ALLOWED_DUNDER_ATTRS:
                raise SandboxSecurityError(
                    f"禁止访问下划线开头的属性 '{attr}'（沙箱逃逸防护）"
                )
        # import 静态检查
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split('.')[0]
                if alias.name not in ALLOWED_MODULES and root not in ALLOWED_MODULES:
                    raise SandboxSecurityError(f"模块 '{alias.name}' 不在沙箱白名单中")
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ''
            root = mod.split('.')[0]
            if mod not in ALLOWED_MODULES and root not in ALLOWED_MODULES:
                raise SandboxSecurityError(f"模块 '{mod}' 不在沙箱白名单中")
        # 运行时字符串属性解析拦截：
        # "...".format(x) / "...".format_map(x) 会在运行期解析字符串内的
        # "{x.__class__}" 字段，从而绕过上面的下划线属性静态检查，是沙箱逃逸通道。
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in _BLOCKED_STR_METHODS:
                raise SandboxSecurityError(
                    f"禁止使用 '{node.func.attr}()' 进行字符串格式化"
                    f"（可经 '{node.func.attr}()' 在运行期解析下划线属性，绕过沙箱检查）"
                )
        # "..." % (...) 形式同理：% 运算在运行期解析 %(name)s 字段，
        # 也会触发字符串内的属性访问，绕过静态检查。
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
            left = node.left
            if isinstance(left, ast.Constant) and isinstance(left.value, str):
                raise SandboxSecurityError(
                    "禁止使用 % 格式化字符串（可经运行期解析下划线属性，绕过沙箱检查）"
                )
    return True

MAX_OUTPUT_BYTES = 64 * 1024  # stdout 捕获上限 64KB
DEFAULT_TIMEOUT = 30          # 默认执行超时（秒）


def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    """仅允许白名单模块导入。"""
    root = name.split('.')[0]
    if name in ALLOWED_MODULES or root in ALLOWED_MODULES:
        return _builtins.__import__(name, globals, locals, fromlist, level)
    raise ImportError(
        f"模块 '{name}' 不在沙箱白名单中。允许的模块: {', '.join(sorted(ALLOWED_MODULES))}"
    )


def _build_safe_builtins():
    safe = {}
    for name in dir(_builtins):
        if name.startswith('_') and name != '__build_class__':
            continue
        if name in _BLOCKED_BUILTINS:
            continue
        safe[name] = getattr(_builtins, name)
    # __build_class__ 是 class 定义所必需
    safe['__build_class__'] = _builtins.__build_class__
    safe['__import__'] = _safe_import
    safe['__name__'] = 'sandbox'
    return safe


class _CaptureStdout:
    """线程内 stdout 捕获（写入 StringIO，超限截断）。"""

    def __init__(self):
        self.buffer = io.StringIO()
        self._truncated = False

    def write(self, s):
        if self.buffer.tell() < MAX_OUTPUT_BYTES:
            self.buffer.write(s)
        else:
            self._truncated = True

    def flush(self):
        pass

    def getvalue(self):
        val = self.buffer.getvalue()
        if self._truncated:
            val += '\n...[输出超过 64KB 已截断]'
        return val


def safe_exec(code, context=None, timeout=DEFAULT_TIMEOUT, extra_globals=None):
    """
    在受限环境中执行一段 Python 代码。

    :param code: 待执行代码字符串
    :param context: 注入执行环境的 context 字典（以变量 `context` 暴露）
    :param timeout: 执行超时秒数
    :param extra_globals: 额外注入的全局对象（调用方自行保证安全）
    :return: dict(success, output, result/error, traceback?)
    """
    context = context or {}
    capture = _CaptureStdout()

    # 先做 AST 静态安全校验，未通过直接拒绝执行
    try:
        _validate_ast(code)
    except SandboxSecurityError as e:
        logger.warning("Sandbox AST validation rejected code: %s", e)
        return {
            'success': False,
            'error': f'安全校验未通过: {e}',
            'output': '',
        }

    globals_dict = {
        '__builtins__': _build_safe_builtins(),
        'context': context,
        'print': lambda *a, **kw: capture.write(
            (kw.get('sep', ' ')).join(str(x) for x in a) + kw.get('end', '\n')
        ),
    }
    if extra_globals:
        globals_dict.update(extra_globals)

    local_scope = {}
    outcome = {}

    def _runner():
        try:
            exec(code, globals_dict, local_scope)  # noqa: S102 -- 受限沙箱内执行
            outcome['success'] = True
        except Exception as e:  # noqa: BLE001 -- 沙箱边界必须兜住一切用户代码异常
            outcome['success'] = False
            outcome['error'] = str(e)
            outcome['traceback'] = traceback.format_exc()

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join(timeout)

    if thread.is_alive():
        logger.warning("Sandbox execution timed out after %ss", timeout)
        return {
            'success': False,
            'error': f'代码执行超时（>{timeout}s），已终止等待。',
            'output': capture.getvalue(),
        }

    if not outcome.get('success'):
        logger.error("Sandbox execution failed: %s", outcome.get('error'))
        return {
            'success': False,
            'error': outcome.get('error', 'unknown error'),
            'traceback': outcome.get('traceback', ''),
            'output': capture.getvalue(),
        }

    return {
        'success': True,
        'output': capture.getvalue(),
        'result': globals_dict.get('result', local_scope.get('result')),
        'locals': local_scope,
    }
