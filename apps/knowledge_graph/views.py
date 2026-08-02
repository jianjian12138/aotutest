from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.conf import settings
import os
import uuid
import logging
from .models import KnowledgeDocument, KnowledgeEntity, KnowledgeRelation

logger = logging.getLogger(__name__)
from .serializers import (
    KnowledgeDocumentSerializer, 
    KnowledgeEntitySerializer, 
    KnowledgeRelationSerializer,
    DocumentChunkSerializer
)
from .services import KnowledgeGraphService
from apps.core_platform.permissions import TenantAwareViewSetMixin

class KnowledgeDocumentViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    queryset = KnowledgeDocument.objects.all()
    serializer_class = KnowledgeDocumentSerializer
    permission_classes = [IsAuthenticated]  # 安全整改：知识文档上传必须登录
    # 第六轮批次2：接入统一租户隔离——知识文档为组织级共享资源（原逻辑全员可见属跨租户泄露）。
    # 模型无 created_by/organization 字段，仅有可空 project 外键，
    # 显式走 KnowledgeDocument.project → Project.organization（路径逐段核对存在），同组织可见。
    # 注意：project 为空的历史文档对非管理员不可见（模型缺属主字段，无更细锚点，已在报告登记）。
    org_field = 'project__organization'
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['updated_at', 'created_at']
    ordering = ['-updated_at']

    def perform_create(self, serializer):
        source_type = self.request.data.get('source_type', 'file')
        external_url = self.request.data.get('external_url', '')
        project_id = self.request.data.get('project') or self.request.data.get('project_id')
        
        save_kwargs = {'project_id': project_id} if project_id else {}

        if source_type == 'file':
            file_obj = self.request.FILES.get('file')
            if file_obj:
                # 安全整改：扩展名白名单 + 大小上限 + 文件名消毒（防路径穿越）
                from backend.utils.uploads import (
                    UploadValidationError, validate_upload, safe_upload_path,
                )
                from rest_framework.exceptions import ValidationError
                try:
                    safe_name, ext = validate_upload(file_obj)
                except UploadValidationError as e:
                    raise ValidationError({'file': str(e)})

                upload_dir = os.path.join(settings.MEDIA_ROOT, 'knowledge_docs')
                os.makedirs(upload_dir, exist_ok=True)
                file_path = safe_upload_path(upload_dir, safe_name)
                
                with open(file_path, 'wb+') as destination:
                    for chunk in file_obj.chunks():
                        destination.write(chunk)
                
                serializer.save(
                    name=safe_name,
                    file_path=file_path,
                    file_type=ext,
                    size=file_obj.size,
                    source_type='file',
                    **save_kwargs
                )
            else:
                serializer.save(source_type='file', **save_kwargs)
        else:
            # External source (Aliyun, Youdao)
            name = self.request.data.get('name', 'External Document')
            serializer.save(
                name=name,
                source_type=source_type,
                external_url=external_url,
                file_type='url',
                status='pending',
                **save_kwargs
            )
            # Automatically trigger fetch and process
            try:
                KnowledgeGraphService.process_document(serializer.instance.id)
            except Exception as e:
                logger.error(f"Failed to auto-process external document: {e}")

    @action(detail=False, methods=['post'])
    def sync_requirement(self, request):
        """Sync a requirement (or document) to KG."""
        requirement_id = request.data.get('requirement_id')
        document_id = request.data.get('document_id')
        
        if not requirement_id and not document_id:
            return Response({'error': 'requirement_id or document_id required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            if document_id:
                doc = KnowledgeGraphService.sync_from_document(document_id)
            else:
                doc = KnowledgeGraphService.sync_from_requirement(requirement_id)
                
            if not doc:
                 return Response({'error': 'Sync failed'}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'status': 'synced', 'document_id': doc.id})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search KG with project context."""
        query = request.query_params.get('query')
        project_id = request.query_params.get('project_id') or request.query_params.get('project')
        
        if not query:
            return Response({'error': 'query required'}, status=status.HTTP_400_BAD_REQUEST)
            
        result = KnowledgeGraphService.search(query, project_id)
        return Response(result)

    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Trigger document processing (extraction)."""
        document = self.get_object()
        
        # Async processing recommended, but synchronous for now for simplicity/demonstration
        try:
            KnowledgeGraphService.process_document(document.id)
            return Response({'status': 'processing_started', 'message': 'Document processing started.'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def content(self, request, pk=None):
        """Get document content."""
        document = self.get_object()
        
        # If document is from requirement sync, construct content from chunks
        if document.source_type == 'requirement':
            chunks = document.chunks.order_by('chunk_index')
            if chunks.exists():
                content = "\n\n".join([chunk.content for chunk in chunks])
                return Response({'content': content})
            return Response({'content': 'No content available for this requirement.'})

        if not document.file_path or not os.path.exists(document.file_path):
            return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            with open(document.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return Response({'content': content})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def chunks(self, request, pk=None):
        """Get chunks for this document."""
        document = self.get_object()
        chunks = document.chunks.all()
        serializer = DocumentChunkSerializer(chunks, many=True)
        return Response(serializer.data)

class KnowledgeGraphVizViewSet(viewsets.ViewSet):
    """ViewSet for querying the Knowledge Graph Visualization."""
    permission_classes = [IsAuthenticated]  # 安全整改：图谱数据需登录访问
    
    @action(detail=False, methods=['get'])
    def entities(self, request):
        entities = KnowledgeEntity.objects.all()
        serializer = KnowledgeEntitySerializer(entities, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def relations(self, request):
        relations = KnowledgeRelation.objects.all()
        serializer = KnowledgeRelationSerializer(relations, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def visualization_data(self, request):
        """Get data formatted for graph visualization (e.g., ECharts, D3)."""
        try:
            entities = KnowledgeEntity.objects.all()
            relations = KnowledgeRelation.objects.all()
            
            nodes = [{"id": str(e.id), "name": e.name, "category": 0} for e in entities]
            # Use source_id and target_id directly to avoid N+1 database queries when accessing foreign keys
            links = [{"source": str(r.source_id), "target": str(r.target_id), "name": r.relation_type} for r in relations]
            
            return Response({
                "nodes": nodes,
                "links": links,
                "categories": [{"name": "Entity"}]
            })
        except Exception as e:
            import traceback
            logger.error(f"Error in visualization_data: {e}\n{traceback.format_exc()}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
