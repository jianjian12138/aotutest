# `apps.assistant.services` 作为包存在，以容纳共享的 chroma_client / rag_retriever 子模块。
# 由于同名目录会遮蔽同名的 `apps/assistant/services.py`（知识库 KG 服务）模块，这里显式
# 桥接原模块的公开 API，保证既有 `from apps.assistant.services import KnowledgeGraphService`
# 等导入继续可用，避免破坏 assistant / knowledge_graph 的 views。
import importlib.util
import os
import sys

_legacy_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "services.py")
_spec = importlib.util.spec_from_file_location("apps.assistant._legacy_services", _legacy_path)
_legacy = importlib.util.module_from_spec(_spec)
_legacy.__package__ = "apps.assistant"
# 注册到 sys.modules，使 mock.patch("apps.assistant._legacy_services.XXX") 可用
sys.modules["apps.assistant._legacy_services"] = _legacy
_spec.loader.exec_module(_legacy)

# 重新导出原 services.py 的公开 API
KnowledgeGraphService = _legacy.KnowledgeGraphService
get_chroma_collection = _legacy.get_chroma_collection
# 同时导出 AIModelConfig / AIModelService，使 mock.patch("apps.assistant.services.XXX") 也可用
AIModelConfig = _legacy.AIModelConfig
AIModelService = _legacy.AIModelService

__all__ = ["KnowledgeGraphService", "get_chroma_collection", "AIModelConfig", "AIModelService"]
