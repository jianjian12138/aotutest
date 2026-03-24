from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import DifyConfig, AIWorkflowConfig
from .serializers import DifyConfigSerializer, AIWorkflowConfigSerializer
from .mcp_service import MCPService
from .skills_service import SkillsService
import requests
import json


class DifyConfigViewSet(viewsets.ModelViewSet):
    """Dify配置管理ViewSet"""
    queryset = DifyConfig.objects.all()
    serializer_class = DifyConfigSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    
    def list(self, request):
        """获取激活的配置"""
        active_config = DifyConfig.get_active_config()
        if active_config:
            serializer = self.get_serializer(active_config)
            # 返回时隐藏完整的API key，只显示部分
            data = serializer.data
            if 'api_key' in data and data['api_key']:
                data['api_key_masked'] = data['api_key'][:8] + '****'
                del data['api_key']
            return Response(data)
        return Response({'message': '未找到激活的配置'}, status=status.HTTP_404_NOT_FOUND)
    
    def create(self, request):
        """创建新配置"""
        # 如果设置为激活，先将其他配置设为不激活
        if request.data.get('is_active', True):
            DifyConfig.objects.update(is_active=False)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, pk=None, partial=False):
        """更新配置"""
        instance = self.get_object()
        
        # 如果设置为激活，先将其他配置设为不激活
        if request.data.get('is_active', False):
            DifyConfig.objects.exclude(pk=pk).update(is_active=False)
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    def partial_update(self, request, pk=None):
        """部分更新配置"""
        return self.update(request, pk=pk, partial=True)
    
    @action(detail=False, methods=['get'])
    def all_configs(self, request):
        """获取所有的配置项无视激活状态 (给管理界面下拉表使用)"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def test_connection(self, request):
        """测试Dify API连接"""
        api_url = request.data.get('api_url')
        api_key = request.data.get('api_key')
        
        if not api_url or not api_key:
            return Response(
                {'error': 'API URL和API Key都是必填项'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 发送测试请求到Dify API
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # 使用一个简单的测试消息
            test_data = {
                'inputs': {},
                'query': 'test',
                'user': 'test_user'
            }
            
            # 去除URL末尾的斜杠
            api_url = api_url.rstrip('/')
            
            response = requests.post(
                f'{api_url}/chat-messages',
                headers=headers,
                json=test_data,
                timeout=30
            )
            
            if response.status_code == 200:
                return Response({'message': '连接成功！', 'success': True})
            else:
                return Response({
                    'error': f'连接失败: {response.status_code}',
                    'detail': response.text,
                    'success': False
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except requests.exceptions.Timeout:
            return Response({
                'error': '连接超时，请检查API URL是否正确',
                'success': False
            }, status=status.HTTP_408_REQUEST_TIMEOUT)
        except requests.exceptions.RequestException as e:
            return Response({
                'error': f'连接错误: {str(e)}',
                'success': False
            }, status=status.HTTP_400_BAD_REQUEST)


class AIWorkflowConfigViewSet(viewsets.ModelViewSet):
    """AI工作流配置管理"""
    queryset = AIWorkflowConfig.objects.all()
    serializer_class = AIWorkflowConfigSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    
    def perform_create(self, serializer):
        # 如果设置为激活，先将同类型的其他配置设为不激活 (MCP除外，支持多个同时激活)
        is_active = serializer.validated_data.get('is_active', True)
        provider = serializer.validated_data.get('provider')
        if is_active and provider and provider != 'mcp':
            AIWorkflowConfig.objects.filter(provider=provider).update(is_active=False)
        serializer.save()
    
    def perform_update(self, serializer):
        # 如果设置为激活，先将同类型的其他配置设为不激活 (MCP除外)
        is_active = serializer.validated_data.get('is_active', False)
        if is_active:
            instance = self.get_object()
            if instance.provider != 'mcp':
                AIWorkflowConfig.objects.filter(provider=instance.provider).exclude(pk=instance.pk).update(is_active=False)
        serializer.save()
        
    @action(detail=False, methods=['get'])
    def active_configs(self, request):
        """获取所有激活的配置"""
        configs = AIWorkflowConfig.objects.filter(is_active=True)
        serializer = self.get_serializer(configs, many=True)
        return Response(serializer.data)
        
    @action(detail=False, methods=['post'])
    def test_connection(self, request):
        """测试连接"""
        provider = request.data.get('provider')
        api_url = request.data.get('api_url')
        api_key = request.data.get('api_key')
        
        if not all([provider, api_url]):
            return Response({'error': '缺少必要参数'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # 根据不同提供商进行简单的连接测试
            if provider == 'dify':
                # 复用Dify测试逻辑
                headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
                test_data = {'inputs': {}, 'query': 'ping', 'user': 'test'}
                response = requests.post(f'{api_url.rstrip("/")}/chat-messages', headers=headers, json=test_data, timeout=10)
                if response.status_code == 200:
                    return Response({'success': True, 'message': 'Dify连接成功'})
                else:
                    return Response({'success': False, 'message': f'Dify连接失败: {response.status_code}'})
            
            elif provider == 'mcp':
                # MCP测试
                mcp_type = request.data.get('mcp_type', 'remote')
                result = MCPService.get_tools(api_url, api_key, mcp_type)
                if isinstance(result, list) or (isinstance(result, dict) and "error" not in result):
                    # 如果测试成功，且提供了ID，更新数据库中的工具数量
                    config_id = request.data.get('id')
                    tools_count = len(result) if isinstance(result, list) else 0
                    if config_id:
                        AIWorkflowConfig.objects.filter(pk=config_id).update(tools_count=tools_count)
                    return Response({'success': True, 'message': 'MCP连接成功', 'tools': result, 'tools_count': tools_count})
                else:
                    error_msg = result.get('error') if isinstance(result, dict) else 'Unknown error'
                    return Response({'success': False, 'message': f"MCP连接失败: {error_msg}"})

            elif provider == 'skills':
                # Skills测试 (简单执行一段代码)
                test_code = "print('Skill execution test success'); result = 'OK'"
                result = SkillsService.execute_skill(test_code)
                if result['success']:
                    return Response({'success': True, 'message': 'Skills执行引擎正常'})
                else:
                    return Response({'success': False, 'message': f"Skills引擎异常: {result['error']}"})

            elif provider == 'coze':
                # Coze测试逻辑 (假设API)
                headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
                response = requests.get(api_url, headers=headers, timeout=10)
                if response.status_code in [200, 401, 403]:
                     return Response({'success': True, 'message': 'Coze连接测试完成'})
            
            # 其他提供商暂只做简单URL连通性测试
            try:
                requests.get(api_url, timeout=5)
                return Response({'success': True, 'message': f'{provider} 服务可访问'})
            except:
                return Response({'success': False, 'message': f'无法访问 {provider} 服务地址'})
                
        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def mcp_tools(self, request, pk=None):
        """获取MCP服务器的工具列表"""
        config = self.get_object()
        if config.provider != 'mcp':
            return Response({'error': '只有MCP类型的配置才支持获取工具'}, status=status.HTTP_400_BAD_REQUEST)
        
        result = MCPService.get_tools(config.api_url, config.api_key, config.mcp_type)
        return Response(result)

    @action(detail=True, methods=['post'])
    def call_mcp_tool(self, request, pk=None):
        """调用MCP工具"""
        config = self.get_object()
        if config.provider != 'mcp':
            return Response({'error': '只有MCP类型的配置才支持调用工具'}, status=status.HTTP_400_BAD_REQUEST)
            
        tool_name = request.data.get('tool_name')
        arguments = request.data.get('arguments', {})
        
        if not tool_name:
            return Response({'error': 'tool_name是必填项'}, status=status.HTTP_400_BAD_REQUEST)
            
        result = MCPService.call_tool(config.api_url, tool_name, arguments, config.api_key, config.mcp_type)
        return Response(result)

    @action(detail=True, methods=['post'])
    def run_skill(self, request, pk=None):
        """执行Skill脚本"""
        config = self.get_object()
        if config.provider != 'skills':
            return Response({'error': '只有Skills类型的配置才支持执行脚本'}, status=status.HTTP_400_BAD_REQUEST)
            
        code = request.data.get('code') or config.additional_config.get('code')
        context = request.data.get('context', {})
        
        if not code:
            return Response({'error': '代码不能为空'}, status=status.HTTP_400_BAD_REQUEST)
            
        result = SkillsService.execute_skill(code, context)
        return Response(result)
