"""共享的 ChromaDB 单例客户端。

统一所有需要访问 Chroma 向量的模块（KG 知识库、Text-to-SQL schema 检索等），
避免每个模块各自创建 PersistentClient 实例，导致多 worker 并发时底层 SQLite
报 "database is locked"。路径与既有 data_explorer_service / services 中的
chroma_db 保持一致（settings.BASE_DIR/chroma_db）。
"""
import os
import threading

import chromadb
from django.conf import settings

# 单一锁：保证进程内只有一个 PersistentClient 实例。
_client_lock = threading.Lock()
_client = None


def get_chroma_client():
    """返回进程内唯一的 ChromaDB PersistentClient 单例。"""
    global _client
    if _client is not None:
        return _client
    with _client_lock:
        if _client is None:
            path = os.path.join(settings.BASE_DIR, "chroma_db")
            os.makedirs(path, exist_ok=True)
            _client = chromadb.PersistentClient(path=path)
    return _client


def get_schema_collection():
    """返回 table_schemas collection（不存在则创建），供 Text-to-SQL RAG 使用。"""
    return get_chroma_client().get_or_create_collection(name="table_schemas")
