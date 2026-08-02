import logging
import os
import json
from typing import List, Dict, Any
from django.conf import settings
from django.db.models import Q
from .models import KnowledgeDocument, DocumentChunk, KnowledgeEntity, KnowledgeRelation, AliyunInterfaceLog
from .connectors.wechat import WechatConnector
from apps.requirement_analysis.models import AIModelConfig, BusinessRequirement
from apps.core_platform.models import Project

logger = logging.getLogger(__name__)

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import JsonOutputParser
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logger.warning("LangChain libraries not found. Knowledge Graph AI features will be limited.")

class KnowledgeGraphService:
    """Knowledge Graph Service for processing documents and extracting entities/relations."""

    @staticmethod
    def _get_llm_client():
        """Get LLM client based on active configuration."""
        if not LANGCHAIN_AVAILABLE:
            return None
            
        # Try to find an active model config for 'knowledge_graph' or general 'writer'
        config = AIModelConfig.objects.filter(role='knowledge_graph', is_active=True).first()
        if not config:
            config = AIModelConfig.objects.filter(role='writer', is_active=True).first()
            
        if not config:
            # Fallback to any active config
            config = AIModelConfig.objects.filter(is_active=True).first()
            
        if not config:
            logger.warning("No active AI Model Config found.")
            return None
            
        api_key = config.api_key
        model = config.model_name
        base_url = None
        
        if config.model_type == 'deepseek':
            base_url = 'https://api.deepseek.com'
        elif config.model_type == 'other' and config.base_url:
            base_url = config.base_url
            
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=0
        )

    @classmethod
    def process_document(cls, document_id: str):
        """Process a document: extract text, chunk, and extract knowledge."""
        try:
            document = KnowledgeDocument.objects.get(id=document_id)
            document.status = 'processing'
            document.save()
            
            # 1. Extract text
            text_content = ""
            
            # Handle external sources first
            if document.source_type == 'wechat' and document.external_url:
                article_data = WechatConnector.fetch_article(document.external_url)
                if article_data:
                    html_content = article_data['content']
                    text_content = article_data['text_content']
                    # Update document name and save to a local file for persistence
                    document.name = article_data['title']
                    
                    upload_dir = os.path.join(settings.MEDIA_ROOT, 'knowledge_docs')
                    os.makedirs(upload_dir, exist_ok=True)
                    import uuid
                    file_path = os.path.join(upload_dir, f"{uuid.uuid4()}_wechat.html")
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(html_content)
                    
                    document.file_path = file_path
                    document.file_type = 'html'
                    document.size = len(html_content.encode('utf-8'))
                    document.save()
                else:
                    raise Exception("Failed to fetch WeChat article content")
            
            # Add other external sources here (aliyun, youdao) if needed
            
            # Now extract from file (either uploaded or just fetched)
            try:
                if document.file_path and os.path.exists(document.file_path):
                    with open(document.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        text_content = f.read()
                elif not text_content:
                    raise FileNotFoundError(f"File not found: {document.file_path}")
            except Exception as e:
                logger.error(f"Failed to read file: {e}")
                document.status = 'failed'
                document.save()
                return
            
            # 2. Chunking
            if LANGCHAIN_AVAILABLE:
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=200,
                    length_function=len,
                )
                chunks = text_splitter.split_text(text_content)
            else:
                # Simple fallback splitting
                chunks = [text_content[i:i+1000] for i in range(0, len(text_content), 1000)]
            
            # Save chunks
            db_chunks = []
            for i, chunk_text in enumerate(chunks):
                db_chunk = DocumentChunk.objects.create(
                    document=document,
                    content=chunk_text,
                    chunk_index=i
                )
                db_chunks.append(db_chunk)
            
            # 3. Knowledge Extraction (Entity & Relation)
            cls.extract_knowledge_from_chunks(db_chunks)
            
            document.status = 'indexed'
            document.save()
            
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {e}")
            document.status = 'failed'
            document.save()

    @classmethod
    def build_interface_kg(cls):
        """Build API knowledge graph from logs."""
        logs = AliyunInterfaceLog.objects.all().order_by('created_at')
        
        # 1. Identify APIs as Entities
        api_entities = {} # URL -> Entity
        for log in logs:
            name = f"{log.method} {log.url}"
            entity, created = KnowledgeEntity.objects.get_or_create(
                name=name,
                defaults={"entity_type": "API", "description": f"Auto-discovered API from logs"}
            )
            api_entities[name] = entity
            
        # 2. Identify Sequential & Data Dependencies
        # Simple heuristic: If log B follows log A within 5 seconds and shares a value
        for i in range(len(logs) - 1):
            log_a = logs[i]
            log_b = logs[i+1]
            
            entity_a = api_entities[f"{log_a.method} {log_a.url}"]
            entity_b = api_entities[f"{log_b.method} {log_b.url}"]
            
            # Sequence relation
            KnowledgeRelation.objects.get_or_create(
                source=entity_a,
                target=entity_b,
                relation_type="calls",
                defaults={"description": "Sequential call observed in logs"}
            )
            
            # Data dependency (Simple check for common values)
            # e.g., if a value in log_a response exists in log_b request
            resp_values = set(str(v) for v in log_a.response_body.values() if v)
            req_values = set(str(v) for v in log_b.request_body.values() if v)
            
            common = resp_values.intersection(req_values)
            if common:
                KnowledgeRelation.objects.get_or_create(
                    source=entity_a,
                    target=entity_b,
                    relation_type="dependency",
                    defaults={"description": f"Shared values: {list(common)}", "metadata": {"shared_values": list(common)}}
                )

    @classmethod
    def search(cls, query: str, project_id: str = None) -> Dict[str, Any]:
        """Search knowledge graph and return context."""
        entities = KnowledgeEntity.objects.filter(Q(name__icontains=query) | Q(description__icontains=query))
        
        if project_id:
            entities = entities.filter(source_chunks__document__project_id=project_id).distinct()
        
        context_parts = []
        for ent in entities:
            context_parts.append(f"Entity: {ent.name} ({ent.entity_type})\nDescription: {ent.description}")
            
            # Get relations
            relations = KnowledgeRelation.objects.filter(Q(source=ent) | Q(target=ent))
            for rel in relations:
                context_parts.append(f"Relation: {rel.source.name} --[{rel.relation_type}]--> {rel.target.name}")
                
        return {
            "context_text": "\n\n".join(context_parts),
            "entities_count": entities.count()
        }

    @classmethod
    def extract_knowledge_from_chunks(cls, chunks: List[DocumentChunk]):
        """Extract entities and relations from chunks using LLM."""
        llm = cls._get_llm_client()
        if not llm:
            logger.warning("No LLM available for knowledge extraction.")
            return

        try:
            from langchain_core.messages import HumanMessage
        except ImportError:
            return

        for chunk in chunks:
            try:
                prompt = f"""
                Extract key entities (Person, Organization, Concept, API, BusinessRule) and relationships from the text.
                Return JSON: {{ "entities": [{{"name": "X", "type": "T", "description": "D"}}], "relations": [{{"source": "X", "target": "Y", "type": "R", "description": "D"}}] }}
                Text: {chunk.content[:3000]}
                """
                response = llm.invoke([HumanMessage(content=prompt)])
                content = response.content.strip()
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                
                data = json.loads(content)
                
                entity_map = {}
                for ent_data in data.get("entities", []):
                    entity, _ = KnowledgeEntity.objects.get_or_create(
                        name=ent_data['name'],
                        defaults={'entity_type': ent_data.get('type', 'Concept'), 'description': ent_data.get('description', '')}
                    )
                    entity.source_chunks.add(chunk)
                    entity_map[entity.name] = entity
                
                for rel_data in data.get("relations", []):
                    src = entity_map.get(rel_data['source'])
                    tgt = entity_map.get(rel_data['target'])
                    if src and tgt:
                        KnowledgeRelation.objects.get_or_create(
                            source=src, target=tgt, relation_type=rel_data.get('type', 'related_to'),
                            defaults={'description': rel_data.get('description', '')}
                        )
            except Exception as e:
                logger.error(f"Error extracting from chunk {chunk.id}: {e}")

    @classmethod
    def sync_from_requirement(cls, requirement_id: int):
        """Sync a BusinessRequirement to Knowledge Graph."""
        try:
            req = BusinessRequirement.objects.get(id=requirement_id)
            project = None
            if req.analysis and req.analysis.document and req.analysis.document.project:
                project = req.analysis.document.project
            
            # Even if no project, we can still sync (maybe as global knowledge or uncategorized)
            
            doc_name = f"Req: {req.requirement_name}"
            doc, created = KnowledgeDocument.objects.get_or_create(
                name=doc_name,
                source_type='requirement',
                project=project,
                defaults={'status': 'processing'}
            )
            
            content = f"Requirement: {req.requirement_name}\nType: {req.get_requirement_type_display()}\n"
            content += f"Description: {req.description}\nAcceptance Criteria: {req.acceptance_criteria}"
            
            if not created:
                doc.chunks.all().delete()
            
            chunk = DocumentChunk.objects.create(document=doc, content=content, chunk_index=0)
            
            cls.extract_knowledge_from_chunks([chunk])
            
            doc.status = 'indexed'
            doc.save()
            return doc
        except Exception as e:
            logger.error(f"Failed to sync requirement {requirement_id}: {e}")
            raise

    @classmethod
    def sync_from_document(cls, document_id: int):
        """Sync a RequirementDocument to Knowledge Graph."""
        try:
            from apps.requirement_analysis.models import RequirementDocument
            req_doc = RequirementDocument.objects.get(id=document_id)
            
            doc_name = f"Doc: {req_doc.title}"
            doc, created = KnowledgeDocument.objects.get_or_create(
                name=doc_name,
                source_type='requirement',
                project=req_doc.project,
                defaults={'status': 'processing'}
            )
            
            # Combine document content and analyzed requirements if available
            content = f"Document Title: {req_doc.title}\n\n"
            if req_doc.extracted_text:
                content += f"Content:\n{req_doc.extracted_text}\n\n"
                
            if hasattr(req_doc, 'analysis'):
                content += "Analyzed Requirements:\n"
                for req in req_doc.analysis.requirements.all():
                    content += f"- {req.requirement_name}: {req.description}\n"
            
            if not created:
                doc.chunks.all().delete()
            
            # Split content if too large
            if len(content) > 1000:
                 chunks = [content[i:i+1000] for i in range(0, len(content), 1000)]
                 db_chunks = []
                 for i, chunk_text in enumerate(chunks):
                     db_chunk = DocumentChunk.objects.create(
                         document=doc,
                         content=chunk_text,
                         chunk_index=i
                     )
                     db_chunks.append(db_chunk)
                 cls.extract_knowledge_from_chunks(db_chunks)
            else:
                chunk = DocumentChunk.objects.create(document=doc, content=content, chunk_index=0)
                cls.extract_knowledge_from_chunks([chunk])
            
            doc.status = 'indexed'
            doc.save()
            return doc
        except Exception as e:
            logger.error(f"Failed to sync requirement document {document_id}: {e}")
            raise
