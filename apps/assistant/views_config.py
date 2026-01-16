from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import DifyConfig, AIWorkflowConfig
from .serializers import DifyConfigSerializer, AIWorkflowConfigSerializer
import requests


class DifyConfigViewSet(viewsets.ModelViewSet):
    """Dify配置管理ViewSet"""
    queryset = DifyConfig.objects.all()
    serializer_class = DifyConfigSerializer
    permission_classes = [IsAuthenticated]
    
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
    
    def perform_create(self, serializer):
        # 如果设置为激活，先将同类型的其他配置设为不激活
        if serializer.validated_data.get('is_active', True):
            provider = serializer.validated_data.get('provider')
            if provider:
                AIWorkflowConfig.objects.filter(provider=provider).update(is_active=False)
        serializer.save()
    
    def perform_update(self, serializer):
        # 如果设置为激活，先将同类型的其他配置设为不激活
        if serializer.validated_data.get('is_active', False):
            instance = self.get_object()
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
        
        if not all([provider, api_url, api_key]):
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
            
            elif provider == 'coze':
                # Coze测试逻辑 (假设API)
                headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
                # Coze API可能有所不同，这里仅作示例
                response = requests.get(api_url, headers=headers, timeout=10)
                if response.status_code in [200, 401, 403]: # 只要能通，即使认证失败也算连接通了(401说明URL对)
                     return Response({'success': True, 'message': 'Coze连接测试完成'})
            
            # 其他提供商暂只做简单URL连通性测试
            try:
                requests.get(api_url, timeout=5)
                return Response({'success': True, 'message': f'{provider} 服务可访问'})
            except:
                return Response({'success': False, 'message': f'无法访问 {provider} 服务地址'})
                
        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
