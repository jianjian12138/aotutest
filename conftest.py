"""Pytest 全局配置 — 让 tests/ 下的 Django 依赖测试在 pytest 中真正执行。

背景：tests/test_orchestrator_critic.py、tests/test_kg.py、tests/test_rag_retriever.py
在模块顶部 try: django.setup()，若 DJANGO_SETTINGS_MODULE 未设置则整模块跳过。
本 conftest.py 在 pytest 收集前设置环境变量并初始化 Django，使这些测试不再被跳过。
"""
import os
import sys

# 项目根目录加入 sys.path（确保 `import apps` / `import backend` 可用）
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# 设置 Django settings 模块（与 manage.py 一致）
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

try:
    import django
    django.setup()
except Exception:
    # Django 依赖未安装时静默跳过 — 纯 Python 测试仍可运行
    pass
