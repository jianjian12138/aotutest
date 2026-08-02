"""沙箱安全回归测试（纯 Python，无需 Django，可在 CI 直接运行）。

覆盖阶段 0/1 二次评审发现的 RCE 绕过通道：
- 下划线属性访问逃逸链（__class__/__bases__/getattr）
- str.format / str.format_map 运行期解析下划线属性
- "%s" % x 字符串格式化运行期解析
"""
import pytest

from backend.utils.sandbox import safe_exec


def test_safe_code_runs():
    r = safe_exec("result = 1 + 2")
    assert r["success"] is True
    assert r["result"] == 3


def test_blocks_dunder_attr():
    r = safe_exec("x = ().__class__.__bases__")
    assert r["success"] is False


def test_blocks_getattr():
    r = safe_exec("x = getattr(int, '__subclasses__')()")
    assert r["success"] is False


def test_blocks_str_format_rce():
    # "{x.__class__}".format(x=1) 在运行期解析下划线属性，绕过 AST 静态检查
    r = safe_exec('x = "{x.__class__}".format(x=1)')
    assert r["success"] is False


def test_blocks_str_format_map_rce():
    r = safe_exec('x = "{x.__class__}".format_map({"x": 1})')
    assert r["success"] is False


def test_blocks_percent_format_rce():
    r = safe_exec('x = "%s" % (1).__class__')
    assert r["success"] is False


def test_allows_fstring():
    r = safe_exec('result = f"{1 + 2}"')
    assert r["success"] is True
    assert r["result"] == "3"


def test_blocks_eval_builtin():
    r = safe_exec("x = eval('1 + 1')")
    assert r["success"] is False
