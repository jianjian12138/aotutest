from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import render
from django.db.models import Q
import requests
from .models import AssistantSession, AssistantMessage, ChatMessage, DifyConfig, AIWorkflowConfig, KnowledgeDocument, KnowledgeEntity, KnowledgeRelationship
from .serializers import (
    AssistantSessionSerializer, 
    AssistantSessionCreateSerializer,
    AssistantMessageSerializer,
    ChatMessageSerializer,
    KnowledgeDocumentSerializer,
    KnowledgeEntitySerializer,
    KnowledgeRelationshipSerializer
)
from .services import KnowledgeGraphService


class AssistantSessionViewSet(viewsets.ModelViewSet):
    """智能助手会话视图集"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AssistantSessionCreateSerializer
        return AssistantSessionSerializer
    
    def get_queryset(self):
        return AssistantSession.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_message(self, request, pk=None):
        """添加消息到会话"""
        session = self.get_object()
        serializer = AssistantMessageSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(session=session)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """获取会话的聊天消息"""
        session = self.get_object()
        messages = session.chat_messages.all()
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)


class ChatViewSet(viewsets.ViewSet):
    """聊天功能ViewSet"""
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def send_message(self, request):
        """发送消息到AI API (支持Dify, Coze等)"""
        session_id = request.data.get('session_id')
        message = request.data.get('message')
        workflow_config_id = request.data.get('workflow_config_id')
        use_knowledge_graph = request.data.get('use_knowledge_graph', False)
        
        if not session_id or not message:
            return Response(
                {'error': 'session_id和message都是必填项'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 获取会话
        try:
            session = AssistantSession.objects.get(
                session_id=session_id,
                user=request.user
            )
        except AssistantSession.DoesNotExist:
            return Response(
                {'error': '会话不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 确定使用的配置
        workflow_config = None
        dify_config = None
        
        if workflow_config_id:
            try:
                workflow_config = AIWorkflowConfig.objects.get(id=workflow_config_id)
            except AIWorkflowConfig.DoesNotExist:
                pass
        
        # 如果没有指定ID或找不到，尝试获取激活的Workflow配置
        if not workflow_config:
            workflow_config = AIWorkflowConfig.objects.filter(is_active=True).first()
            
        # 如果没有Workflow配置，尝试获取旧版Dify配置
        if not workflow_config:
            dify_config = DifyConfig.get_active_config()
            
        if not workflow_config and not dify_config:
             return Response(
                {'error': '未配置AI工作流引擎，请先在知识图谱-AI评测师中配置'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 知识库检索逻辑
        context = ""
        if use_knowledge_graph:
            # 使用新版RAG检索
            rag_results = KnowledgeGraphService.search(message)
            if rag_results['context_text']:
                context = f"\n\n【知识库参考上下文】:\n{rag_results['context_text']}"
            else:
                context = "\n\n【知识库搜索结果】: 未找到相关文档，请进行深度搜索或基于通用知识回答。"
        
        # 构建最终发送给AI的消息
        final_message = message
        if context:
            final_message = f"{message}\n{context}"
        
        # 保存用户消息 (保存原始消息，不含context)
        user_message = ChatMessage.objects.create(
            session=session,
            role='user',
            content=message,
            conversation_id=session.conversation_id
        )
        
        try:
            # 根据配置类型调用不同的处理逻辑
            if workflow_config:
                return self._handle_workflow_request(request, session, workflow_config, final_message, user_message)
            else:
                return self._handle_dify_request(request, session, dify_config, final_message, user_message)
                
        except requests.exceptions.Timeout:
            return Response({
                'error': 'API请求超时'
            }, status=status.HTTP_408_REQUEST_TIMEOUT)
        except requests.exceptions.RequestException as e:
            return Response({
                'error': f'API请求失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _handle_dify_request(self, request, session, config, message, user_message):
        """处理旧版Dify请求"""
        headers = {
            'Authorization': f'Bearer {config.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'inputs': {},
            'query': message,
            'user': str(request.user.id),
            'response_mode': 'blocking'
        }
        
        if session.conversation_id:
            payload['conversation_id'] = session.conversation_id
        
        api_url = config.api_url.rstrip('/')
        
        response = requests.post(
            f'{api_url}/chat-messages',
            headers=headers,
            json=payload,
            timeout=60
        )
        
        return self._process_response(response, session, user_message, provider='dify')

    def _handle_workflow_request(self, request, session, config, message, user_message):
        """处理新版Workflow请求"""
        provider = config.provider
        api_url = config.api_url.rstrip('/')
        
        if provider == 'dify':
            # Dify Workflow/Chat 逻辑
            headers = {
                'Authorization': f'Bearer {config.api_key}',
                'Content-Type': 'application/json'
            }
            payload = {
                'inputs': {}, # 如果是Workflow，这里可能需要更多参数
                'query': message,
                'user': str(request.user.id),
                'response_mode': 'blocking'
            }
            if session.conversation_id:
                payload['conversation_id'] = session.conversation_id
                
            response = requests.post(f'{api_url}/chat-messages', headers=headers, json=payload, timeout=60)
            return self._process_response(response, session, user_message, provider='dify')
            
        elif provider == 'coze':
            # Coze API Logic (Example)
            headers = {
                'Authorization': f'Bearer {config.api_key}',
                'Content-Type': 'application/json'
            }
            payload = {
                'query': message,
                'user': str(request.user.id),
                'conversation_id': session.conversation_id,
                'bot_id': config.workflow_id
            }
            # Coze API endpoint structure varies
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            # Need to adapt response processing for Coze
            return self._process_response(response, session, user_message, provider='coze')
            
        elif provider in ['n8n', 'skills', 'mcp']:
             # Generic Webhook/API call
            headers = {'Content-Type': 'application/json'}
            if config.api_key:
                headers['Authorization'] = f'Bearer {config.api_key}'
            
            payload = {
                'message': message,
                'user_id': request.user.id,
                'session_id': session.session_id
            }
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            return self._process_response(response, session, user_message, provider='generic')

        return Response({'error': f'不支持的提供商: {provider}'}, status=status.HTTP_400_BAD_REQUEST)

    def _process_response(self, response, session, user_message, provider='dify'):
        """统一处理响应"""
        if response.status_code == 200:
            data = response.json()
            
            answer = ''
            conversation_id = None
            message_id = None
            
            if provider == 'dify':
                answer = data.get('answer', '')
                conversation_id = data.get('conversation_id')
                message_id = data.get('message_id')
            elif provider == 'coze':
                # Adapt based on Coze response format
                if 'messages' in data:
                    for msg in reversed(data['messages']):
                        if msg.get('type') == 'answer':
                            answer = msg.get('content')
                            break
                    if not answer:
                         answer = data.get('messages', [{}])[-1].get('content', '')
                else:
                    answer = str(data)
                conversation_id = data.get('conversation_id')
            else:
                # Generic
                answer = data.get('output', {}).get('text', '') or data.get('answer', '') or str(data)
            
            # 更新会话
            if conversation_id and not session.conversation_id:
                session.conversation_id = conversation_id
                session.save()
            
            # 保存助手回复
            assistant_message = ChatMessage.objects.create(
                session=session,
                role='assistant',
                content=answer,
                conversation_id=conversation_id,
                message_id=message_id
            )
            
            return Response({
                'user_message': ChatMessageSerializer(user_message).data,
                'assistant_message': ChatMessageSerializer(assistant_message).data,
                'conversation_id': conversation_id
            })
        else:
            return Response({
                'error': f'API错误: {response.status_code}',
                'detail': response.text
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def assistant_view(request):
    """智能助手页面视图 - 用于iframe内嵌"""
    return render(request, 'assistant/assistant.html')


class KnowledgeGraphViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = KnowledgeDocument.objects.all()
    serializer_class = KnowledgeDocumentSerializer

    def perform_create(self, serializer):
        doc = serializer.save(created_by=self.request.user)
        if doc.file:
            try:
                # 确保读取文件内容并保存到 content 字段
                doc.file.seek(0)
                file_content = doc.file.read().decode('utf-8', errors='ignore')
                doc.content = file_content
                doc.save(update_fields=['content'])
            except Exception as e:
                print(f"Failed to read file content: {e}")
                pass
        
        # 触发知识图谱处理
        try:
            KnowledgeGraphService.process_document(doc.id)
        except Exception as e:
            print(f"Failed to process document in KG: {e}")

    @action(detail=False, methods=['get'])
    def graph_data(self, request):
        """获取图谱数据"""
        nodes = KnowledgeEntity.objects.all()
        edges = KnowledgeRelationship.objects.all()
        
        node_data = []
        for n in nodes:
            node_data.append({
                "id": str(n.id),
                "name": n.name,
                "category": 1 if n.entity_type == 'concept' else 0
            })
            
        edge_data = []
        for e in edges:
            edge_data.append({
                "source": str(e.source.id),
                "target": str(e.target.id),
                "name": e.relation_type
            })
            
        return Response({
            "nodes": node_data,
            "edges": edge_data
        })

    @action(detail=False, methods=['get'])
    def search(self, request):
        """RAG搜索"""
        query = request.query_params.get('q', '')
        if not query:
            return Response({"error": "Query parameter 'q' is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        results = KnowledgeGraphService.search(query)
        return Response(results)
        
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """获取统计信息"""
        return Response({
            "document_count": KnowledgeDocument.objects.count(),
            "knowledge_nodes": KnowledgeEntity.objects.count(),
            "relation_count": KnowledgeRelationship.objects.count(),
            "last_update": KnowledgeDocument.objects.last().created_at if KnowledgeDocument.objects.exists() else None
        })
