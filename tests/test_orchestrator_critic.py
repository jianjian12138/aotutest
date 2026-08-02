"""Orchestrator._critic_review 结构校验器测试（Django 依赖）。

需要 Django 运行期，例如：``python manage.py test tests.test_orchestrator_critic``。
若 Django 未配置（如纯 pytest 环境 ``cd tests && python -m pytest -q``），
整模块优雅跳过，保证 tests/ 下纯测试仍绿。

校验目标：_critic_review 拒绝 空名 / 重名 / 非法 HTTP method / 空 url，
并接受一个合法用例。
"""
import unittest

try:
    import django
    if not django.conf.settings.configured:
        django.setup()  # 无 DJANGO_SETTINGS_MODULE 时抛 ImproperlyConfigured -> 走 except
    from django.test import SimpleTestCase
    from apps.assistant.orchestrator import MultiAgentOrchestrator
except Exception as exc:  # Django 不可用 / 未配置
    import unittest
    _DJANGO_SKIP_REASON = f"Django runtime unavailable: {exc}"

    class TestOrchestratorCritic(unittest.TestCase):
        def test_skipped(self):
            self.skipTest(_DJANGO_SKIP_REASON)
else:
    class TestOrchestratorCritic(SimpleTestCase):
        """校验结构校验器对非法用例的拦截与对合法用例的放行。"""

        @staticmethod
        def _case(name, method="GET", url="/api/x", steps=None):
            return {"name": name, "steps": steps or [{"method": method, "url": url}]}

        def test_rejects_empty_name(self):
            valid, rejected, _ = MultiAgentOrchestrator._critic_review(
                [self._case("", url="/x")])
            self.assertEqual(valid, [])
            self.assertEqual(len(rejected), 1)
            self.assertIn("name", rejected[0]["reason"])

        def test_rejects_duplicate_name(self):
            valid, rejected, _ = MultiAgentOrchestrator._critic_review(
                [self._case("dup"), self._case("dup")])
            self.assertEqual(len(valid), 1)
            self.assertEqual(len(rejected), 1)
            self.assertIn("重名", rejected[0]["reason"])

        def test_rejects_illegal_http_method(self):
            valid, rejected, _ = MultiAgentOrchestrator._critic_review(
                [self._case("m", method="FOO", url="/x")])
            self.assertEqual(valid, [])
            self.assertEqual(len(rejected), 1)

        def test_rejects_empty_url(self):
            valid, rejected, _ = MultiAgentOrchestrator._critic_review(
                [self._case("u", method="GET", url="")])
            self.assertEqual(valid, [])
            self.assertEqual(len(rejected), 1)

        def test_accepts_valid_case(self):
            valid, rejected, _ = MultiAgentOrchestrator._critic_review(
                [self._case("valid", method="POST", url="/api/login")])
            self.assertEqual(len(valid), 1)
            self.assertEqual(rejected, [])
            self.assertEqual(valid[0]["name"], "valid")
