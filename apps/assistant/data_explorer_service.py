import json
import logging
import sqlite3

from apps.data_factory.models import TableMetadata, DataFactoryProject, DataSource
from apps.requirement_analysis.models import AIModelConfig, AIModelService
from apps.assistant.services.chroma_client import get_schema_collection
from backend.utils.sql_guard import (
    SQLGuardError, validate_statements, enforce_limit,
)
from django.db import connections, transaction
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

# ---- Text-to-SQL 真实 RAG：表结构向量检索底座 ----
# 将 TableMetadata 嵌入独立 collection，生成 SQL 时用语义向量检索
# 出与需求最相关的表结构，而非无差别地拼接全部 schema。
# 统一复用 apps/assistant/services/chroma_client 的 ChromaDB 单例，
# 避免各模块各自创建 PersistentClient 导致多 worker 并发时 SQLite 锁风险。


def _get_schema_collection():
    """复用统一的 ChromaDB 单例（避免多 worker SQLite 锁）。"""
    return get_schema_collection()


def _build_schema_index(project_id=None):
    """将 TableMetadata 嵌入向量库，供 Text-to-SQL 检索相关表。"""
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
        coll = _get_schema_collection()
        try:
            coll.delete(ids=ids)
        except Exception:
            pass
        coll.upsert(documents=docs, ids=ids, metadatas=metas)
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("构建表结构向量索引失败（降级为全量 schema）：%s", e)
        return False


def _retrieve_relevant_tables(nl, project_id=None, top_k=8):
    """真实 RAG：用语义向量检索出与需求最相关的表结构。"""
    try:
        if not _build_schema_index(project_id):
            return None
        coll = _get_schema_collection()
        res = coll.query(query_texts=[nl], n_results=top_k)
        docs = (res.get('documents') or [[]])[0]
        if docs:
            return "\n".join(docs)
    except Exception as e:  # noqa: BLE001
        logger.warning("表结构 RAG 检索失败（降级为全量 schema）：%s", e)
    return None

# 数据源类型 → 驱动模块映射（依赖已在 requirements 中声明）
_ENGINE_DRIVERS = {
    'mysql': 'pymysql',
    'postgresql': 'psycopg2',
    'sqlite3': 'sqlite3',
}

# 仅 SQL 类数据源支持 Text-to-SQL 直接执行
_SQL_TYPES = frozenset(_ENGINE_DRIVERS.keys())


def _connect_to_data_source(data_source):
    """
    为 DataSource 建立一条**独立只读**连接（不碰平台主库）。
    凭据由 EncryptedTextField 自动解密；本连接绝不执行写操作（写需调用方确认，
    且仍走 validate_statements 的 allow_insert 白名单）。
    """
    ds_type = (data_source.type or '').lower()
    if ds_type not in _SQL_TYPES:
        raise ValueError(
            f"数据源类型不支持 SQL 执行: {ds_type}（仅支持 MySQL / PostgreSQL / SQLite）"
        )
    _ENGINE_DRIVERS[ds_type]

    if ds_type == 'sqlite3':
        import os
        path = data_source.host or data_source.database or data_source.name
        if path and not os.path.isabs(path):
            path = os.path.join('.', path)
        conn = sqlite3.connect(path, timeout=10)
    elif ds_type == 'postgresql':
        import psycopg2
        conn = psycopg2.connect(
            host=data_source.host, port=int(data_source.port or 5432),
            dbname=data_source.database or data_source.name,
            user=data_source.username,
            password=data_source.password,  # EncryptedTextField 自动解密
            connect_timeout=15,
        )
    elif ds_type == 'mysql':
        import pymysql
        conn = pymysql.connect(
            host=data_source.host, port=int(data_source.port or 3306),
            database=data_source.database or data_source.name,
            user=data_source.username,
            password=data_source.password,
            connect_timeout=15,
        )
    else:  # pragma: no cover - 前置 type 校验已拦截
        raise ValueError(f"不支持的数据源类型: {ds_type}")

    return conn

class DataExplorerService:
    
    @staticmethod
    def generate_sql(project_id, natural_language):
        """将测试人员的自然语言需求转换为高度可执行的 MOCK SQL 语句或查询条件"""
        try:
            # 真实 RAG：先用语义向量检索出与需求最相关的表结构，
            # 检索失败或库为空时降级为全量 schema（保持可用）。
            rag_schema = _retrieve_relevant_tables(natural_language, project_id)
            if rag_schema:
                schema_context = rag_schema
                schema_note = "（已通过向量检索，仅展示与需求语义最相关的表结构）"
            else:
                tables = TableMetadata.objects.all()
                if project_id:
                    try:
                        project = DataFactoryProject.objects.get(id=project_id)
                        if project.config:
                            tables = TableMetadata.objects.filter(config=project.config)
                    except DataFactoryProject.DoesNotExist:
                        pass

                if not tables.exists():
                    return {"status": "FAILED", "error": "当前环境尚未扫描到任何表结构，请先进行元数据同步。"}

                schema_lines = []
                for t in tables:
                    col_defs = []
                    if isinstance(t.columns, list):
                        for c in t.columns:
                            col_defs.append(f"{c.get('name', 'unknown')} ({c.get('type', 'varchar')})")

                    schema_lines.append(f"Table Name: {t.table_name} | Columns Format: {', '.join(col_defs)}")

                schema_context = "\n".join(schema_lines)
                schema_note = ""

            prompt = f"""
你是一个极其出色的测试数据工厂高级抽象架构师。
你的职责是：根据下方我提供给你的物理数据库映射拓扑结构 (Table Schemas)，完美且优雅地翻译测试工程师给出的口语化“造数据”需求。

【底层真实数据库的 Schema 结构全映射】
{schema_context}
{schema_note}

【测试工程师正在尝试用自然语言发出的指令】
"{natural_language}"

任务：
1. 如果该任务是需要新生成（伪造/Mock）用户的假数据，请生成严格符合以上物理列属性的多条 INSERT 语句，并自动发散生成合理的随机测试数据（例如伪造邮箱、随机手机号、随机生成外键等组合）。
2. 如果任务指令是让你查询某些环境是否存在，请返回 SELECT 语句。
3. 如果测试工程师要求多条记录（例如：给我造10个用户），你必须返回对应的批量 INSERT VALUES 行记录。

关键限制：
请严格且【仅仅】返回纯粹的 SQL 可执行字符串，**不要**包含 Markdown 代码块包裹符（如 ```sql ）！并且**绝对禁止**任何前言后语及人类口语化的解释！
你的输出即将被后端 `cursor.execute()` 直接裸执行，任何人类对话残余都会导致语法跑偏崩溃。
多条语句请利用分号 ';' 分割。
"""
            model_config = AIModelConfig.objects.filter(is_active=True).first()
            if not model_config:
                return {"status": "FAILED", "error": "系统未配置活跃的 AI (Deepseek/OpenAI等) 引擎。请先前往全局配置模块激活大模型底座！"}
                
            messages = [{"role": "user", "content": prompt}]
            response_data = async_to_sync(AIModelService.call_openai_compatible_api)(model_config, messages)
            answer = response_data['choices'][0]['message']['content'].strip()
            
            # 清理 Markdown 代码块可能导致的残余包装器
            if answer.startswith("```sql"):
                answer = answer[6:]
            if answer.startswith("```"):
                answer = answer[3:]
            if answer.endswith("```"):
                answer = answer[:-3]
                
            return {"status": "SUCCESS", "sql": answer.strip()}
            
        except Exception as e:
            return {"status": "FAILED", "error": f"Data Explorer 大语言引擎推理异常链拆解失败: {str(e)}"}

    @staticmethod
    def execute_generated_sql(sql_script, confirm_write=False, data_source_id=None, user=None):
        """
        执行 AI 生成的 SQL（经安全防护层校验）。

        安全策略（backend.utils.sql_guard）：
        - 默认仅允许只读语句（SELECT/WITH/SHOW/DESCRIBE/EXPLAIN）；
        - INSERT 造数语句必须由前端用户显式确认（confirm_write=True）；
        - UPDATE/DELETE/DDL 一律拒绝；
        - SELECT 自动追加 LIMIT，结果集截断，防止数据爆炸。

        库路由（租户隔离）：
        - 必须指定 data_source_id，连到**目标 DataSource**（独立的业务库 / 只读从库），
          绝不触碰平台主库；且对 DataSource 做租户/归属校验，越权访问直接拒绝；
        - 未指定数据源：一律拒绝（不回退平台主库，避免泄露内部表）。
        """
        try:
            statements = validate_statements(sql_script, allow_insert=confirm_write)
        except SQLGuardError as e:
            return {"status": "REJECTED", "error": f"SQL 安全校验未通过: {e}"}

        try:
            # 决定执行连接：必须指定合法的目标数据源，禁止回退平台主库
            if not data_source_id:
                return {"status": "REJECTED",
                        "error": "请先选择目标数据源（DataSource）后再执行；出于安全考虑，"
                                "未指定数据源时不允许查询平台主库。"}
            try:
                data_source = DataSource.objects.get(id=data_source_id)
            except DataSource.DoesNotExist:
                return {"status": "FAILED", "error": f"指定的数据源不存在: {data_source_id}"}
            # 租户/创建者隔离：默认拒绝，仅以下情况放行
            user_org_id = getattr(getattr(user, 'organization', None), 'id', None) if user else None
            user_id = getattr(user, 'id', None) if user else None
            is_owner = bool(data_source.created_by_id and data_source.created_by_id == user_id)
            is_same_org = bool(data_source.organization_id and data_source.organization_id == user_org_id)
            is_super = bool(getattr(user, 'is_superuser', False))
            if not (is_super or is_owner or is_same_org):
                return {"status": "REJECTED", "error": "无权访问该数据源（租户隔离校验未通过）"}
            conn = _connect_to_data_source(data_source)
            owns_connection = True

            overall_results = []
            try:
                cursor = conn.cursor()
                for stmt in statements:
                    sql = enforce_limit(stmt)
                    cursor.execute(sql)
                    # 只有 SELECT/SHOW 这种产生返回值的游标才有 description 元数据
                    if cursor.description:
                        columns = [col[0] for col in cursor.description]
                        rows = cursor.fetchall()
                        # 防止数据爆炸截断至前 50 条即可
                        data_rows = [dict(zip(columns, row)) for row in rows][:50]
                        overall_results.append({"type": "SELECTION", "data": data_rows})
                    else:
                        overall_results.append({
                            "type": "MUTATION",
                            "status": "Executed OK",
                            "affected_rows": cursor.rowcount
                        })
                if owns_connection:
                    conn.commit()
            finally:
                if owns_connection and conn is not None:
                    try:
                        conn.close()
                    except Exception:
                        pass

            return {"status": "SUCCESS", "results": overall_results}
        except Exception:
            logger.exception("Data Explorer SQL 执行失败")
            return {"status": "FAILED", "error": "SQL 执行失败，详情已记录日志。"}
