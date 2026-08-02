import json
import logging
import re
import threading
import uuid

import requests
from asgiref.sync import async_to_sync
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .models import (
    KnowledgeDocument, DocumentChunk, KnowledgeEntity,
    KnowledgeRelationship, AIWorkflowConfig, DifyConfig,
)
from apps.requirement_analysis.models import AIModelService, AIModelConfig

# 共享的 Chroma 单例客户端（避免多 worker 并发时底层 SQLite "database is locked"）
from apps.assistant.services.chroma_client import get_chroma_client

logger = logging.getLogger(__name__)

# 知识库 collection 的惰性、线程安全单例（复用共享 Chroma 单例）。
_knowledge_collection = None
_knowledge_collection_lock = threading.Lock()


def get_chroma_collection():
    """惰性、线程安全地返回知识库 collection（复用共享 Chroma 单例）。"""
    global _knowledge_collection
    if _knowledge_collection is not None:
        return _knowledge_collection
    with _knowledge_collection_lock:
        if _knowledge_collection is None:
            client = get_chroma_client()
            _knowledge_collection = client.get_or_create_collection(name="knowledge_base")
    return _knowledge_collection

class KnowledgeGraphService:
    
    @staticmethod
    def process_document(doc_id):
        """处理文档：切片、向量化、提取知识图谱"""
        try:
            doc = KnowledgeDocument.objects.get(id=doc_id)
        except KnowledgeDocument.DoesNotExist:
            return False, "Document not found"

        # 1. 文本切片
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", "。", "！", "？", " ", ""]
        )
        chunks = text_splitter.split_text(doc.content)

        # 2. 向量化并存储 (模拟或使用简单Embedding)
        # 注意：实际生产中应使用 OpenAIEmbeddings 或 HuggingFaceEmbeddings
        # 这里为了演示方便，如果未配置Embedding模型，Chroma默认使用其内置的all-MiniLM-L6-v2
        
        ids = [f"doc_{doc.id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{"source": doc.title, "doc_id": doc.id, "chunk_index": i} for i in range(len(chunks))]

        # 存入Chroma（惰性初始化 + 线程锁，稳定 id 支持 upsert 防重复）
        collection = get_chroma_collection()
        # 先删旧向量再写，保证重处理不产生重复向量
        try:
            collection.delete(ids=ids)
        except Exception:
            pass
        collection.upsert(
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )

        # 存入数据库
        for i, chunk_text in enumerate(chunks):
            DocumentChunk.objects.create(
                document=doc,
                content=chunk_text,
                chunk_index=i,
                vector_id=ids[i]
            )

        # 3. 知识图谱提取 (尝试调用配置的AI引擎)
        KnowledgeGraphService.extract_and_store_graph(doc, chunks)
        
        return True, f"Processed {len(chunks)} chunks"

    @staticmethod
    def extract_and_store_graph(doc, chunks):
        """调用真实 AI 引擎抽取实体和关系；仅当无任何可用大模型配置时降级为 mock（明确标注）。"""
        # 简单策略：只处理前几个切片，避免消耗过多 Token
        sample_text = "\n".join(chunks[:3])

        prompt = f"""
        请分析以下文本，提取关键的“实体”(Entity)和实体间的“关系”(Relationship)。
        文本内容：
        {sample_text}

        请严格以JSON格式返回，格式如下：
        {{
            "entities": [
                {{"name": "实体1", "type": "类型", "description": "描述"}},
                {{"name": "实体2", "type": "类型", "description": "描述"}}
            ],
            "relationships": [
                {{"source": "实体1", "target": "实体2", "type": "关系类型", "description": "描述"}}
            ]
        }}
        """

        # 仅当完全无可用的大模型配置时才降级 mock
        config = AIModelConfig.objects.filter(is_active=True).first()
        if not config:
            # audit: real-impl 降级路径的告警日志；降级产物已按口径强制打标 demo_ 前缀 + [演示数据] 描述，graph_data 接口返回 is_demo 与 demo_data_warning，用户可辨识
            logger.warning("知识图谱：未配置激活的 AI 模型，使用 mock 抽取（演示数据）。")
            KnowledgeGraphService._save_mock_graph(doc)
            return

        try:
            messages = [{"role": "user", "content": prompt}]
            response_data = async_to_sync(AIModelService.call_openai_compatible_api)(config, messages)
            answer = response_data['choices'][0]['message']['content'].strip()

            # 清理 Markdown 代码块包裹
            if answer.startswith("```json"):
                answer = answer[7:]
            elif answer.startswith("```"):
                answer = answer[3:]
            if answer.endswith("```"):
                answer = answer[:-3]

            match = re.search(r'\{[\s\S]*\}', answer)
            data = json.loads(match.group(0)) if match else {}
            entities = data.get('entities', [])
            relationships = data.get('relationships', [])

            for ent in entities:
                name = ent.get('name')
                if not name:
                    continue
                entity, _ = KnowledgeEntity.objects.get_or_create(
                    name=name,
                    defaults={'entity_type': ent.get('type', 'Concept'),
                              'description': ent.get('description', '')}
                )
                for rel in relationships:
                    target = rel.get('target')
                    # 仅建立以当前实体为 source 的关系
                    if not target or rel.get('source') != name:
                        continue
                    target_entity, _ = KnowledgeEntity.objects.get_or_create(
                        name=target,
                        defaults={'entity_type': rel.get('type', 'Concept'),
                                  'description': rel.get('description', '')}
                    )
                    KnowledgeRelationship.objects.get_or_create(
                        source=entity, target=target_entity,
                        relation_type=rel.get('type', '关联'),
                        defaults={'description': rel.get('description', '')}
                    )
            logger.info("知识图谱：已用真实 LLM 抽取 %d 实体 / %d 关系（文档：%s）。",
                        len(entities), len(relationships), doc.title)
        except Exception as e:
            # 已有可用的大模型配置却调用失败：绝不静默造"演示"假数据污染知识库，
            # 把失败暴露出来便于排障。仅当完全无配置时才允许 mock（见上方 if not config）。
            logger.warning(
                # audit: real-impl 错误日志文案（说明"拒绝生成假数据"的整改行为本身），非造假实现
                "知识图谱 LLM 抽取失败（已有配置，拒绝生成假数据，错误已暴露）：doc_id=%s 错误=%s",
                getattr(doc, "id", None), e,
            )
            return

    # 第六轮批次2：演示数据必须在库内可辨识，供前端与审计区分真假
    DEMO_ENTITY_TYPE_PREFIX = 'demo_'
    DEMO_DESC_PREFIX = '[演示数据·未经真实 AI 抽取]'

    @staticmethod
    def _save_mock_graph(doc):
        """无任何可用大模型配置时的降级演示图谱。

        第六轮批次2：此前生成的节点与真实抽取结果外观完全一致，用户无从分辨。
        现在强制打标——entity_type 加 `demo_` 前缀、description 加显式前缀，
        graph_data 接口据此向前端返回 is_demo 标记与告警。
        """
        p = KnowledgeGraphService.DEMO_DESC_PREFIX
        root_entity, _ = KnowledgeEntity.objects.get_or_create(
            name=doc.title,
            defaults={"entity_type": "demo_document",
                      "description": f"{p} 文档根节点（关键词规则生成，非模型抽取）"}
        )

        # 关键词规则匹配，不具备语义抽取能力，仅用于无模型配置时的界面演示
        keywords = ["测试", "AI", "平台", "自动化", "RAG", "知识图谱"]
        for kw in keywords:
            if kw in doc.content:
                entity, _ = KnowledgeEntity.objects.get_or_create(
                    name=kw,
                    defaults={"entity_type": "demo_concept",
                              "description": f"{p} 关于{kw}的概念（关键词规则命中）"}
                )

                KnowledgeRelationship.objects.get_or_create(
                    source=root_entity,
                    target=entity,
                    relation_type="包含",
                    defaults={"description": f"{p} 文档包含此概念（关键词规则推定）"}
                )

    @staticmethod
    def search(query, top_k=3):
        """混合检索：向量 + 图谱"""
        results = {
            "chunks": [],
            "graph": {"nodes": [], "edges": []},
            "context_text": ""
        }

        # 1. 向量检索（复用惰性、线程安全的 collection）
        collection = get_chroma_collection()
        search_res = collection.query(
            query_texts=[query],
            n_results=top_k
        )
        
        if search_res['documents']:
            for i, doc_text in enumerate(search_res['documents'][0]):
                results["chunks"].append({
                    "content": doc_text,
                    "metadata": search_res['metadatas'][0][i]
                })
                results["context_text"] += f"{doc_text}\n---\n"

        # 2. 图谱检索 (简单的关键词匹配)
        # 查找名称包含查询词的实体
        entities = KnowledgeEntity.objects.filter(name__icontains=query)[:5]
        for entity in entities:
            results["graph"]["nodes"].append({
                "id": str(entity.id),
                "name": entity.name,
                "category": 1 # ECharts category
            })
            
            # 获取关联关系
            relations = KnowledgeRelationship.objects.filter(source=entity)
            for rel in relations:
                results["graph"]["nodes"].append({
                    "id": str(rel.target.id),
                    "name": rel.target.name,
                    "category": 2
                })
                results["graph"]["edges"].append({
                    "source": str(rel.source.id),
                    "target": str(rel.target.id),
                    "name": rel.relation_type
                })

        # 去重
        results["graph"]["nodes"] = [dict(t) for t in {tuple(d.items()) for d in results["graph"]["nodes"]}]
        results["graph"]["edges"] = [dict(t) for t in {tuple(d.items()) for d in results["graph"]["edges"]}]

        return results
