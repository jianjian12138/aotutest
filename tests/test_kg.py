"""KnowledgeGraphService.extract_and_store_graph 测试（Django 依赖）。

需要 Django 运行期，例如：``python manage.py test tests.test_kg``。
若 Django 未配置（纯 pytest 环境），整模块优雅跳过。

验证目标：当存在激活的 AIModelConfig 但 LLM 调用抛错时，
extract_and_store_graph 不应创建（mock）图谱，且安全返回（不抛错、不污染知识库）。
"""
import unittest
from unittest import mock

try:
    import django
    if not django.conf.settings.configured:
        django.setup()
    from django.test import TestCase
    from apps.assistant.services import KnowledgeGraphService
    from apps.assistant.models import KnowledgeDocument, KnowledgeEntity
except Exception as exc:  # Django 不可用 / 未配置
    import unittest
    _DJANGO_SKIP_REASON = f"Django runtime unavailable: {exc}"

    class TestExtractGraphOnLlmError(unittest.TestCase):
        def test_skipped(self):
            self.skipTest(_DJANGO_SKIP_REASON)
else:
    class TestExtractGraphOnLlmError(TestCase):
        def test_no_mock_graph_when_llm_raises(self):
            doc = KnowledgeDocument.objects.create(
                title="测试文档", content="测试 AI 平台 自动化 知识图谱")
            chunks = ["段落一 关于测试", "段落二 关于AI", "段落三 关于自动化"]

            # 存在激活的 AI 配置（patch 出真值），但 LLM 调用抛错
            # KnowledgeGraphService 在 apps/assistant/services.py（legacy 模块）中定义，
            # 其全局名称 AIModelConfig / AIModelService 解析自 apps.assistant._legacy_services。
            fake_config = object()
            # 真实调用点位于 apps.assistant.services 命名空间
            # （AIModelConfig / AIModelService 由 services.py 从 apps.requirement_analysis.models 引入）。
            # 旧测试误 mock 已不存在的 _legacy_services 模块，导致 mock 失效、真实 LLM 被触发；
            # 以下改为 mock 真实调用点，使用例在离线/无网络环境下稳定可重跑。
            with mock.patch(
                "apps.assistant.services.AIModelConfig.objects.filter"
            ) as mock_filter:
                mock_filter.return_value.first.return_value = fake_config
                with mock.patch(
                    "apps.assistant.services.AIModelService.call_openai_compatible_api",
                    side_effect=RuntimeError("LLM boom"),
                ):
                    result = KnowledgeGraphService.extract_and_store_graph(doc, chunks)

            # 失败应安全返回 None，且绝不创建 mock 图谱（拒绝以假数据污染知识库）
            self.assertIsNone(result)
            self.assertEqual(KnowledgeEntity.objects.count(), 0)
