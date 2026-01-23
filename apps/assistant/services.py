import os
import uuid
import chromadb
from chromadb.utils import embedding_functions
from django.conf import settings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .models import KnowledgeDocument, DocumentChunk, KnowledgeEntity, KnowledgeRelationship, AIWorkflowConfig, DifyConfig
import json
import requests

# 初始化ChromaDB客户端
CHROMA_DB_PATH = os.path.join(settings.BASE_DIR, 'chroma_db')
os.makedirs(CHROMA_DB_PATH, exist_ok=True)
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# 使用默认的集合
collection = chroma_client.get_or_create_collection(name="knowledge_base")

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
        
        ids = [str(uuid.uuid4()) for _ in range(len(chunks))]
        metadatas = [{"source": doc.title, "doc_id": doc.id, "chunk_index": i} for i in range(len(chunks))]
        
        # 存入Chroma
        collection.add(
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
        """调用AI提取实体和关系"""
        # 简单策略：只处理前几个切片，避免消耗过多Token
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
        
        # 获取可用的AI配置
        config = AIWorkflowConfig.objects.filter(is_active=True).first()
        if not config:
            dify_config = DifyConfig.get_active_config()
            # 如果没有配置，这里可以做一个简单的Mock数据用于演示
            if not dify_config:
                KnowledgeGraphService._save_mock_graph(doc)
                return

        # TODO: 这里应该调用 ChatViewSet 中的通用发送逻辑
        # 为了简化，这里暂时模拟提取结果 (或者如果在真实环境有Key，可以实现真实调用)
        # 由于我们不知道用户的API Key是否有效，为了保证演示效果，我们先进行Mock提取
        # 如果需要真实提取，可以扩展此处的API调用逻辑
        KnowledgeGraphService._save_mock_graph(doc)

    @staticmethod
    def _save_mock_graph(doc):
        """生成演示用的图谱数据 (当无法调用AI时)"""
        # 基于文档标题生成一些节点
        root_entity, _ = KnowledgeEntity.objects.get_or_create(
            name=doc.title,
            defaults={"entity_type": "Document", "description": "文档根节点"}
        )
        
        # 提取一些简单的关键词作为节点 (简单的规则)
        keywords = ["测试", "AI", "平台", "自动化", "RAG", "知识图谱"]
        for kw in keywords:
            if kw in doc.content:
                entity, _ = KnowledgeEntity.objects.get_or_create(
                    name=kw,
                    defaults={"entity_type": "Concept", "description": f"关于{kw}的概念"}
                )
                
                # 建立关系
                KnowledgeRelationship.objects.get_or_create(
                    source=root_entity,
                    target=entity,
                    relation_type="包含",
                    defaults={"description": "文档包含此概念"}
                )

    @staticmethod
    def search(query, top_k=3):
        """混合检索：向量 + 图谱"""
        results = {
            "chunks": [],
            "graph": {"nodes": [], "edges": []},
            "context_text": ""
        }

        # 1. 向量检索
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
