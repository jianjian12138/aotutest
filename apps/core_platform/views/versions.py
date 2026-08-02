from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db import models
from ..models import Version
from ..permissions import TenantAwareViewSetMixin
from ..serializers.versions import VersionSerializer, VersionCreateSerializer
from apps.core_platform.models import Project

# 版本管理视图
class VersionListCreateView(TenantAwareViewSetMixin, generics.ListCreateAPIView):
    """版本列表和创建视图

    # 第六轮批次2：显式声明自管租户过滤，每个 return 分支收口 _apply_tenant_scope。
    """
    tenant_scope_self_managed = True
    tenant_scope_self_managed_reason = (
        'get_queryset 先算出当前用户可访问项目集合（Q(owner=user)|Q(members=user)），再以 projects__in 限定版本，'
        '不属于这些项目的版本一律不可见（fail-closed），即使 query_params 传入他人 projects 也只能在该集合内二次收窄；'
        'Version 只有 projects 这一 M2M 关联、无 organization/project 单外键，自动解析会退化为 created_by，'
        '把协作成员可见的共享版本收紧成"仅自己创建"，属功能倒退'
    )
    queryset = Version.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_baseline']  # 移除projects，手动处理
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return VersionCreateSerializer
        return VersionSerializer
    
    def get_queryset(self):
        # 只显示用户有权限访问的项目的版本
        user = self.request.user
        accessible_projects = Project.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        
        queryset = Version.objects.filter(projects__in=accessible_projects).distinct()
        
        # 手动处理项目筛选
        project_id = self.request.query_params.get('projects')
        if project_id and project_id.strip():  # 检查是否为空或空字符串
            try:
                project_id = int(project_id)
                queryset = queryset.filter(projects__id=project_id)
            except (ValueError, TypeError):
                # 如果无法转换为整数，忽略此筛选条件
                pass
        
        return self._apply_tenant_scope(queryset)
    
    def perform_create(self, serializer):
        user = self.request.user
        project_ids = serializer.validated_data.get('project_ids')
        
        # 检查项目权限
        accessible_projects = Project.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        
        # 验证用户对所有指定项目都有权限
        accessible_project_ids = set(accessible_projects.values_list('id', flat=True))
        requested_project_ids = set(project_ids)
        
        if not requested_project_ids.issubset(accessible_project_ids):
            from rest_framework.exceptions import ValidationError
            raise ValidationError("没有权限访问部分项目")
        
        serializer.save(created_by=user)

class VersionDetailView(TenantAwareViewSetMixin, generics.RetrieveUpdateDestroyAPIView):
    """版本详情视图

    # 第六轮批次2：显式声明自管租户过滤，return 分支收口 _apply_tenant_scope。
    """
    tenant_scope_self_managed = True
    tenant_scope_self_managed_reason = (
        '同 VersionListCreateView：仅返回归属于当前用户 owner|members 项目的版本，他人项目的版本不可达（fail-closed）；'
        'Version 无 organization/project 单外键，自动解析会退化为 created_by，把协作成员共享的版本收紧为仅自己创建，属功能倒退'
    )
    queryset = Version.objects.all()
    serializer_class = VersionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        accessible_projects = Project.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        qs = self.queryset.filter(projects__in=accessible_projects).distinct()
        return self._apply_tenant_scope(qs)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_project_versions(request, project_id):
    """获取指定项目的版本列表"""
    user = request.user
    
    # 检查项目权限
    accessible_projects = Project.objects.filter(
        models.Q(owner=user) | models.Q(members=user)
    ).distinct()
    
    if not accessible_projects.filter(id=project_id).exists():
        return Response({'error': '没有权限访问该项目'}, status=status.HTTP_403_FORBIDDEN)
    
    versions = Version.objects.filter(projects__id=project_id).order_by('-created_at')
    serializer = VersionSerializer(versions, many=True)
    return Response(serializer.data)
