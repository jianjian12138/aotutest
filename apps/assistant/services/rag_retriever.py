"""共享的 RAG 检索：Text-to-SQL 表结构语义检索（一致性去重核心）。

复用 chroma_client 的共享单例与 table_schemas collection，行为对齐
apps/assistant/data_explorer_service 中已实现的真实向量检索（同款默认 embedding）。
任何失败均安全降级返回 None，由调用方回退到全量 schema，绝不抛错中断流程。
"""
import logging

from apps.assistant.services.chroma_client import get_schema_collection
from apps.data_factory.models import TableMetadata, DataFactoryProject

logger = logging.getLogger(__name__)


def _build_schema_index(project_id=None):
    """将 TableMetadata 嵌入 table_schemas，供语义检索相关表。"""
    try:
        tables = TableMetadata.objects.all()
        if project_id:
            try:
                proj = DataFactoryProject.objects.get(id=project_id)
                if proj.config:
                    tables = tables.filter(config=proj.config)
            except DataFactoryProject.DoesNotExist:
                pass
        if not tables.exists():
            return False
        docs, ids, metas = [], [], []
        for t in tables:
            cols = t.columns if isinstance(t.columns, list) else []
            col_defs = ", ".join(
                f"{c.get('name', '?')} ({c.get('type', 'varchar')})" for c in cols
            )
            docs.append(f"Table {t.table_name}: {col_defs}")
            ids.append(f"tbl_{t.id}")
            metas.append({"table_name": t.table_name})
        coll = get_schema_collection()
        try:
            coll.delete(ids=ids)
        except Exception:
            pass
        coll.upsert(documents=docs, ids=ids, metadatas=metas)
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("构建表结构向量索引失败（降级）：%s", e)
        return False


def retrieve_relevant_tables(project_id, nl, top_k=8):
    """真实 RAG：用语义向量检索出与需求最相关的表结构，拼接为文本返回。

    Args:
        project_id: 项目 ID；为 None 时索引全部表（与 data_explorer 行为一致）。
        nl: 自然语言问题 / 需求。
        top_k: 返回的相关表数量。

    Returns:
        拼接后的 schema 文本；任何失败返回 None（安全降级）。
    """
    try:
        if not _build_schema_index(project_id):
            return None
        coll = get_schema_collection()
        res = coll.query(query_texts=[nl], n_results=top_k)
        docs = (res.get("documents") or [[]])[0]
        if docs:
            return "\n".join(docs)
    except Exception as e:  # noqa: BLE001
        logger.warning("表结构 RAG 检索失败（降级）：%s", e)
    return None
