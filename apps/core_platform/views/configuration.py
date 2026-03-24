from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
import json
import traceback
from ..models import GlobalParameter, CommonMethod
from ..serializers.configuration import GlobalParameterSerializer, CommonMethodSerializer
from apps.api_testing.models import ApiRequest, ApiTestCaseStep

class GlobalParameterViewSet(viewsets.ModelViewSet):
    queryset = GlobalParameter.objects.all()
    serializer_class = GlobalParameterSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['key', 'description']
    ordering_fields = ['key', 'created_at']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        key_pattern = f"{{{{{instance.key}}}}}"
        
        # 检查接口管理中的引用
        # 由于是JSONField，我们将其转换为字符串进行模糊查询
        # 注意：这里的查询逻辑可能需要根据实际使用的数据库进行优化
        request_refs = ApiRequest.objects.filter(
            Q(url__icontains=key_pattern) |
            Q(headers__icontains=key_pattern) |
            Q(params__icontains=key_pattern) |
            Q(body__icontains=key_pattern) |
            Q(assertions__icontains=key_pattern) |
            Q(extract_rules__icontains=key_pattern)
        ).exists()
        
        if request_refs:
            return Response(
                {"error": f"参数 '{instance.key}' 正在被接口管理中的接口引用，禁止删除"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 检查用例管理中的引用
        step_refs = ApiTestCaseStep.objects.filter(
            Q(url__icontains=key_pattern) |
            Q(headers__icontains=key_pattern) |
            Q(params__icontains=key_pattern) |
            Q(body__icontains=key_pattern) |
            Q(assertions__icontains=key_pattern) |
            Q(extract_rules__icontains=key_pattern)
        ).exists()
        
        if step_refs:
            return Response(
                {"error": f"参数 '{instance.key}' 正在被用例管理中的步骤引用，禁止删除"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        return super().destroy(request, *args, **kwargs)

class CommonMethodViewSet(viewsets.ModelViewSet):
    queryset = CommonMethod.objects.all()
    serializer_class = CommonMethodSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'keyword', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        keyword = instance.keyword
        
        # 检查接口管理中的引用 (主要在脚本中)
        request_refs = ApiRequest.objects.filter(
            Q(pre_request_script__icontains=keyword) |
            Q(post_request_script__icontains=keyword)
        ).exists()
        
        if request_refs:
            return Response(
                {"error": f"公共方法 '{instance.name}' ({keyword}) 正在被接口管理中的脚本引用，禁止删除"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # 检查用例管理中的引用
        step_refs = ApiTestCaseStep.objects.filter(
            Q(pre_request_script__icontains=keyword) |
            Q(post_request_script__icontains=keyword)
        ).exists()
        
        if step_refs:
            return Response(
                {"error": f"公共方法 '{instance.name}' ({keyword}) 正在被用例管理中的步骤脚本引用，禁止删除"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def debug(self, request, pk=None):
        """调试公共方法"""
        instance = self.get_object()
        code = instance.code_snippet
        args = request.data.get('args', [])
        
        if not code:
            return Response({"error": "该方法没有代码片段"}, status=status.HTTP_400_BAD_REQUEST)
            
        # 准备执行上下文
        local_scope = {}
        global_scope = {
            '__builtins__': __builtins__,
            'json': __import__('json'),
            're': __import__('re'),
            'os': __import__('os'),
            'sys': __import__('sys'),
            'time': __import__('time'),
            'logging': __import__('logging'),
            'datetime': __import__('datetime'),
            'ApiRequest': ApiRequest,
            'ApiTestCaseStep': ApiTestCaseStep,
        }
        
        # 尝试导入常用模块
        try:
            from libs.config_center import LOG, ENV
            global_scope['LOG'] = LOG
            global_scope['ENV'] = ENV
        except ImportError:
            pass
            
        try:
            from keywords.playwright_keywords import get_playwright_driver
            global_scope['get_playwright_driver'] = get_playwright_driver
        except ImportError:
            pass
            
        try:
            # 执行代码定义函数
            exec(code, global_scope, local_scope)
            
            # 找到定义的函数
            func_name = None
            func = None
            
            # 优先匹配方法名（去除$）
            target_name = instance.keyword.lstrip('$')
            if target_name in local_scope:
                func_name = target_name
                func = local_scope[target_name]
            else:
                # 否则找第一个可调用对象
                for key, value in local_scope.items():
                    if callable(value) and not key.startswith('__'):
                        func_name = key
                        func = value
                        break
            
            if not func:
                return Response({"error": "未找到函数定义"}, status=status.HTTP_400_BAD_REQUEST)
            
            # 调用函数
            # 注意：如果 args 是列表，则解包；如果是字典，则 kwargs
            result = None
            if isinstance(args, list):
                result = func(*args)
            elif isinstance(args, dict):
                result = func(**args)
            else:
                result = func(args)
                
            return Response({
                "result": str(result),
                "status": "success",
                "message": "执行成功"
            })
            
        except Exception as e:
            return Response({
                "error": str(e),
                "traceback": traceback.format_exc(),
                "status": "error"
            }, status=status.HTTP_400_BAD_REQUEST)
