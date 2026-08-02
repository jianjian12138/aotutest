from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import render
from django.db.models import Q
import requests
import json
import logging
logger = logging.getLogger(__name__)
from .models import AssistantSession, AssistantMessage, ChatMessage, DifyConfig, AIWorkflowConfig, KnowledgeDocument, KnowledgeEntity, KnowledgeRelationship
from apps.requirement_analysis.models import AIModelConfig, AIModelService
from apps.core_platform.permissions import TenantAwareViewSetMixin
from asgiref.sync import async_to_sync
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
from .intelligent_executor import IntelligentExecutor
from .crawler_service import AutonomousCrawler
from .impact_analysis import GitImpactAnalyzer
from .visual_service import VisualAIAnalyzer


class AssistantSessionViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    """智能助手会话视图集"""
    permission_classes = [permissions.IsAuthenticated]
    # 第六轮批次2：接入统一租户隔离——AssistantSession 租户锚点为 user 字段
    org_field = 'user'
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AssistantSessionCreateSerializer
        return AssistantSessionSerializer
    
    def get_queryset(self):
        # 第六轮批次2：接入统一租户隔离——保留原有更严格的"仅本人会话"过滤
        # （不放宽为组织可见，管理员分支拿到的也是已按本人过滤的集合），再统一收口。
        qs = AssistantSession.objects.filter(user=self.request.user)
        return self._apply_tenant_scope(qs)
    
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


class ChatViewSet(TenantAwareViewSetMixin, viewsets.ViewSet):
    """聊天功能ViewSet（引入 mixin 以在 action 内使用 scoped_get 零件）"""
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def send_message(self, request):
        """发送消息到AI API (支持Dify, Coze等)"""
        session_id = request.data.get('session_id')
        message = request.data.get('message')
        # 兼容多种 ID 传参方式
        workflow_config_id = request.data.get('workflow_config_id') or \
                            request.data.get('model_config_id') or \
                            request.data.get('model_id')
        use_knowledge_graph = request.data.get('use_knowledge_graph', False)
        
        if not session_id or not message:
            return Response(
                {'error': 'session_id和message都是必填项'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 获取会话
        try:
            # AssistantSession 以 user 为租户字段；保留 user=request.user 原有限定
            session = self.scoped_get(
                AssistantSession,
                org_field='user',
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
        model_config = None
        dify_config = None
        
        if workflow_config_id:
            # 1. 尝试从 AIWorkflowConfig 获取
            # AIWorkflowConfig 无任何租户字段，scoped_get 对非管理员 fail-closed，
            # 查不到时按原逻辑回退到激活配置
            try:
                workflow_config = self.scoped_get(AIWorkflowConfig, id=workflow_config_id)
            except (AIWorkflowConfig.DoesNotExist, ValueError):
                # 2. 尝试从 AIModelConfig 获取（按 created_by 自动做租户过滤）
                try:
                    model_config = self.scoped_get(AIModelConfig, id=workflow_config_id)
                except (AIModelConfig.DoesNotExist, ValueError):
                    pass
        
        # 如果没有指定ID或找不到，尝试获取激活的配置
        if not workflow_config and not model_config:
            workflow_config = AIWorkflowConfig.objects.filter(is_active=True).first()
            if not workflow_config:
                model_config = AIModelConfig.objects.filter(is_active=True).first()
            
        # 如果没有配置，尝试获取旧版Dify配置
        if not workflow_config and not model_config:
            dify_config = DifyConfig.get_active_config()
            
        if not workflow_config and not model_config and not dify_config:
             return Response(
                {'error': '未配置AI模型或工作流引擎，请先在配置中心或AI助手设置中配置'},
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
        
        # 保存用户消息（通过已过租户校验的 session 关系创建，杜绝挂载到他租户）
        user_message = session.chat_messages.create(
            role='user',
            content=message,
            conversation_id=session.conversation_id
        )
        
        # 尝试使用智能执行器 (MCP, Skills, Workflow)
        try:
            executor_context = {
                "session_id": session_id,
                "test_mode": request.data.get('test_mode', 'api'),
                "project_id": request.data.get('project_id'),
                "device_id": request.data.get('device_id')
            }
            intelligent_result = IntelligentExecutor.execute(message, request.user, executor_context)
        except Exception as e:
            logger.error(f"IntelligentExecutor execution failed: {e}")
            intelligent_result = {"error": str(e)}
        
        # 处理指令型技能 (不中断流程，而是合并指令)
        skill_instructions = ""
        if intelligent_result.get('type') == 'instructional':
            skill_name = intelligent_result.get('skill_name')
            skill_instructions = intelligent_result.get('instructions')
            logger.info(f"Using instructional skill: {skill_name}")
            # 我们将指令合并到 context 中
            context = f"{context}\n\n【技能指令 - {skill_name}】:\n{skill_instructions}"
            # 清除 intelligent_result 以便继续后续 AI 调用
            intelligent_result = {"error": "continue_to_ai"}

        if "error" not in intelligent_result:
            # 如果成功通过技能或MCP处理，直接返回结果
            answer = f"【智能执行结果】:\n{json.dumps(intelligent_result, ensure_ascii=False, indent=2)}"
            # 通过已过租户校验的 session 关系创建
            assistant_message = session.chat_messages.create(
                role='assistant',
                content=answer,
                conversation_id=session.conversation_id
            )
            return Response({
                'user_message': ChatMessageSerializer(user_message).data,
                'assistant_message': ChatMessageSerializer(assistant_message).data,
                'intelligent': True
            })

        try:
            # 根据配置类型调用不同的处理逻辑
            if workflow_config:
                return self._handle_workflow_request(request, session, workflow_config, final_message, user_message)
            elif model_config:
                return self._handle_model_config_request(request, session, model_config, final_message, user_message)
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

    @action(detail=False, methods=['post'], url_path='data-explorer-chat')
    def data_explorer_chat(self, request):
        """【V2.3】数据探索助手: Text-to-SQL Flow"""
        project_id = request.data.get('project_id')
        message = request.data.get('message')
        auto_execute = request.data.get('auto_execute', False)
        # 写操作（INSERT 造数）必须由用户在前端显式确认
        confirm_write = bool(request.data.get('confirm_write', False))
        # 指定目标数据源（独立业务库/只读从库）；不传则仅允许只读主库查询
        data_source_id = request.data.get('data_source_id')

        if not message:
             return Response({'error': '自然语言请求消息 message 不能为空'}, status=status.HTTP_400_BAD_REQUEST)
             
        from .data_explorer_service import DataExplorerService
        
        # 1. Pipeline: 尝试流转给大模型理解意图并生成 SQL
        llm_response = DataExplorerService.generate_sql(project_id, message)
        
        if llm_response.get('status') != 'SUCCESS':
            return Response(llm_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        sql_script = llm_response.get('sql')
        
        # 2. Pipeline: 若开启动态落库沙盒验证，则即时执行（经 sql_guard 校验）
        execution_results = []
        if auto_execute:
            exec_resp = DataExplorerService.execute_generated_sql(
                sql_script, confirm_write=confirm_write,
                data_source_id=data_source_id, user=request.user)
            if exec_resp.get('status') == 'SUCCESS':
                execution_results = exec_resp.get('results', [])
            else:
                # SQL 语法错误或执行异常依然返回 200 交由前端容错展示
                return Response({
                    'sql': sql_script,
                    'error': exec_resp.get('error'),
                    'warning': 'SQL 生成成功但沙盒执行崩溃！'
                }, status=status.HTTP_200_OK)

        return Response({
            'status': 'SUCCESS',
            'sql': sql_script,
            'results': execution_results
        }, status=status.HTTP_200_OK)

    def _handle_model_config_request(self, request, session, config, message, user_message):
        """处理直接调用 AI 模型配置 (OpenAI 兼容)"""
        messages = [
            {"role": "user", "content": message}
        ]
        
        try:
            # 使用 async_to_sync 调用异步的 AIModelService
            response_data = async_to_sync(AIModelService.call_openai_compatible_api)(config, messages)
            
            answer = response_data['choices'][0]['message']['content']
            
            # 保存助手回复
            assistant_message = ChatMessage.objects.create(
                session=session,
                role='assistant',
                content=answer,
                conversation_id=session.conversation_id
            )
            
            return Response({
                'user_message': ChatMessageSerializer(user_message).data,
                'assistant_message': ChatMessageSerializer(assistant_message).data,
                'conversation_id': session.conversation_id
            })
            
        except Exception as e:
            return Response({
                'error': f'AI模型调用失败: {str(e)}'
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
        
        # 如果 provider 是 skills，说明这只是一个指令增强，不应该直接调用 api_url
        if provider == 'skills':
            # 查找一个真正可用的 AI 模型来执行
            fallback_model = AIModelConfig.objects.filter(is_active=True).first()
            if fallback_model:
                # 使用技能指令增强消息
                instructions = config.additional_config.get('instructions', '')
                enhanced_message = f"【系统指令】: {instructions}\n\n【用户需求】: {message}"
                return self._handle_model_config_request(request, session, fallback_model, enhanced_message, user_message)
            else:
                return Response({'error': '技能模式需要配置至少一个活跃的 AI 模型作为执行引擎'}, status=status.HTTP_400_BAD_REQUEST)

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


class KnowledgeGraphViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = KnowledgeDocument.objects.all()
    serializer_class = KnowledgeDocumentSerializer
    # 第六轮批次2：接入统一租户隔离——知识库文档为组织级共享资源。
    # 模型无 organization/project 字段，仅有 created_by，若走自动解析会收成
    # "仅创建者可见"，破坏组织内共享协作（功能倒退）；故显式声明多跳路径
    # created_by__organization（User.organization 外键真实存在），同组织可见。
    org_field = 'created_by__organization'

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
        demo_count = 0
        for n in nodes:
            # 第六轮批次2：演示数据（无 AI 配置时的关键词规则降级产物）必须可辨识
            is_demo = (n.entity_type or '').startswith('demo_')
            if is_demo:
                demo_count += 1
            node_data.append({
                "id": str(n.id),
                "name": n.name,
                "category": 1 if n.entity_type == 'concept' else 0,
                "is_demo": is_demo
            })

        edge_data = []
        for e in edges:
            edge_data.append({
                "source": str(e.source.id),
                "target": str(e.target.id),
                "name": e.relation_type,
                "is_demo": (e.description or '').startswith('[演示数据')
            })

        payload = {
            "nodes": node_data,
            "edges": edge_data,
            "demo_node_count": demo_count,
        }
        if demo_count:
            payload["demo_data_warning"] = (
                f"当前图谱包含 {demo_count} 个演示节点（未配置可用 AI 模型时由关键词规则生成，"
                f"非真实语义抽取）。请在系统设置中配置 AI 模型后重新处理文档以获得真实图谱。"
            )
        return Response(payload)

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

class CrawlerViewSet(viewsets.ViewSet):
    """【V3.1】自主探索智能体: Scriptless Exploration"""
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='run-exploration')
    def run_exploration(self, request):
        start_url = request.data.get('start_url', 'http://localhost:5656')
        max_steps = request.data.get('max_steps', 10)
        
        crawler = AutonomousCrawler(start_url=start_url, max_steps=max_steps)
        
        # 为了演示，我们使用同步方式运行（实际生产应使用 Celery 或 Background Tasks）
        # 这里建议使用 loop.run_in_executor 或者直接 run
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(crawler.run_exploration())
        finally:
            loop.close()
            
        return Response({
            "status": "SUCCESS",
            "message": f"Completed {len(results)} exploration steps.",
            "history": results
        })

class PredictiveQAViewSet(viewsets.ViewSet):
    """【V3.2】精准测试与风险预测: Impact Analysis"""
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='analyze-impact')
    def analyze_impact(self, request):
        commit_id = request.query_params.get('commit', 'HEAD')
        request.query_params.get('base', 'main')
        
        analyzer = GitImpactAnalyzer()
        # For simplicity, we just analyze the latest commit vs current state
        impact_data = analyzer.analyze_impact(target_commit=commit_id)
        
        return Response({
            "status": "SUCCESS",
            **impact_data
        })

class VisualRegressionViewSet(viewsets.ViewSet):
    """【V3.3】多模态视觉回归: Semantic UI Comparison"""
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='compare')
    def compare_screenshots(self, request):
        base_image_path = request.data.get('base_image_path')
        current_image_base64 = request.data.get('current_image_base64')
        
        # In a real scenario, we would look up the baseline from a database
        # For V3.3 demo, we assume the user provides the path or we use a default
        analyzer = VisualAIAnalyzer()
        
        # Use a dummy baseline if not provided for demo
        if not base_image_path:
             return Response({"status": "ERROR", "message": "Missing baseline image path"}, status=400)

        # Run async comparison
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(analyzer.compare_screenshots(base_image_path, current_image_base64))
        
        return Response({
            "status": "SUCCESS",
            "data": result
        })

    @action(detail=False, methods=['get'], url_path='baselines')
    def list_baselines(self, request):
        """Standardized baseline list for V3.3 UI"""
        return Response({
            "status": "SUCCESS",
            "items": [
                {"id": 1, "name": "Homepage Header", "path": "/media/visual_regression/baseline_home.png"},
                {"id": 2, "name": "Login Form", "path": "/media/visual_regression/baseline_login.png"},
            ]
        })
