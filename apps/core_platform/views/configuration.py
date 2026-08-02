from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
import json
from ..models import GlobalParameter, CommonMethod
from ..serializers.configuration import GlobalParameterSerializer, CommonMethodSerializer
from ..permissions import IsOwnerOrAdminOrReadOnly, IsAdminUserStrict, OwnedQuerySetMixin
from apps.api_testing.models import ApiRequest, ApiTestCaseStep
from backend.utils.sandbox import safe_exec

class GlobalParameterViewSet(OwnedQuerySetMixin, viewsets.ModelViewSet):
    queryset = GlobalParameter.objects.all()
    serializer_class = GlobalParameterSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdminOrReadOnly]
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

class CommonMethodViewSet(OwnedQuerySetMixin, viewsets.ModelViewSet):
    queryset = CommonMethod.objects.all()
    serializer_class = CommonMethodSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdminOrReadOnly]
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

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUserStrict])
    def debug(self, request, pk=None):
        """调试公共方法。

        安全说明：代码在受限沙箱（backend.utils.sandbox）中执行——
        无 os/sys/subprocess、白名单模块导入、超时控制；且仅平台管理员可调用。
        """
        instance = self.get_object()
        code = instance.code_snippet
        args = request.data.get('args', [])

        if not code:
            return Response({"error": "该方法没有代码片段"}, status=status.HTTP_400_BAD_REQUEST)

        target_name = instance.keyword.lstrip('$')
        exec_result = safe_exec(code, context={'args': args}, timeout=30)

        if not exec_result.get('success'):
            return Response({
                "error": exec_result.get('error', '执行失败'),
                "status": "error"
            }, status=status.HTTP_400_BAD_REQUEST)

        # 从沙箱局部作用域中寻找目标函数
        local_scope = exec_result.get('locals', {})
        func = local_scope.get(target_name)
        if func is None or not callable(func):
            func = next(
                (v for k, v in local_scope.items() if callable(v) and not k.startswith('__')),
                None
            )

        if not func:
            return Response({"error": "未找到函数定义"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if isinstance(args, list):
                result = func(*args)
            elif isinstance(args, dict):
                result = func(**args)
            else:
                result = func(args)

            return Response({
                "result": str(result),
                "output": exec_result.get('output', ''),
                "status": "success",
                "message": "执行成功"
            })
        except Exception as e:
            return Response({
                "error": str(e),
                "status": "error"
            }, status=status.HTTP_400_BAD_REQUEST)
