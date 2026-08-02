"""retrieve_relevant_tables 测试（Django 依赖）。

需要 Django 运行期，例如：``python manage.py test tests.test_rag_retriever``。
若 Django 未配置（纯 pytest 环境），整模块优雅跳过。

验证目标：
- 已建索引（chroma 可用）时返回拼接后的 schema 字符串；
- 完全失败（chroma 抛错）时安全降级返回 None，绝不向上抛错。
"""
import unittest
from unittest import mock

try:
    import django
    if not django.conf.settings.configured:
        django.setup()
    from django.test import TestCase
    from apps.assistant.services.rag_retriever import retrieve_relevant_tables
except Exception as exc:  # Django 不可用 / 未配置
    import unittest
    _DJANGO_SKIP_REASON = f"Django runtime unavailable: {exc}"

    class TestRagRetriever(unittest.TestCase):
        def test_skipped(self):
            self.skipTest(_DJANGO_SKIP_REASON)
else:
    class TestRagRetriever(TestCase):
        def test_returns_string_when_indexed(self):
            fake_coll = mock.MagicMock()
            fake_coll.query.return_value = {
                "documents": [["Table users: id (int), name (varchar)"]],
                "metadatas": [[{"table_name": "users"}]],
            }
            with mock.patch(
                "apps.assistant.services.rag_retriever.get_schema_collection",
                return_value=fake_coll,
            ):
                with mock.patch(
                    "apps.assistant.services.rag_retriever._build_schema_index",
                    return_value=True,
                ):
                    result = retrieve_relevant_tables(None, "用户表")
            self.assertIsInstance(result, str)
            self.assertIn("users", result)

        def test_returns_none_when_chroma_raises(self):
            with mock.patch(
                "apps.assistant.services.rag_retriever.get_schema_collection",
                side_effect=RuntimeError("chroma down"),
            ):
                result = retrieve_relevant_tables(None, "任意问题")
            self.assertIsNone(result)
