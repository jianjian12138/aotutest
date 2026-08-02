"""阶段1 RBAC / 审计 视图。

- RoleViewSet：角色 CRUD（仅租户管理员/平台管理员）。
- PermissionViewSet：只读列出系统全部权限，供角色编辑器使用。
- UserRoleViewSet：查看/设置用户角色（仅管理员）。
- AuditLogViewSet：审计日志检索（只读，租户隔离）。
"""
from rest_framework import viewsets, permissions as drf_permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth.models import Permission
from django_filters.rest_framework import DjangoFilterBackend

from ..models import Role, AuditLog, User
from ..permissions import IsTenantAdminOrReadOnly, TenantAwareViewSetMixin, TenantScopedViewSetMixin, is_tenant_admin
from ..serializers.rbac import (
    RoleSerializer, PermissionSerializer, UserRoleSerializer, AuditLogSerializer,
)


class RoleViewSet(viewsets.ModelViewSet):
    # 第六轮批次2：平台级资源显式豁免。已核实 Role 模型（models.py:205）无 organization
    # 外键，code 全局 unique，属平台级角色字典表（如 tenant_admin），全租户共享；
    # 读对所有认证用户开放，写由 IsTenantAdminOrReadOnly 限制为租户/平台管理员。
    tenant_scope_exempt = True
    tenant_scope_exempt_reason = 'Role 为平台级角色字典表（无 organization 字段、code 全局唯一），全租户共享读取；写操作已由 IsTenantAdminOrReadOnly 限制为管理员'
    queryset = Role.objects.all().order_by('code')
    serializer_class = RoleSerializer
    permission_classes = [drf_permissions.IsAuthenticated, IsTenantAdminOrReadOnly]
    pagination_class = None


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """系统全部权限（用于角色编辑器勾选）。"""
    # 第六轮批次2：平台级资源显式豁免。Django 内置 auth.Permission 字典表，
    # 无任何租户字段，只读 ViewSet，供角色编辑器全量勾选，按租户过滤会直接破坏功能。
    tenant_scope_exempt = True
    tenant_scope_exempt_reason = 'Django 内置 auth.Permission 权限字典表，平台级公共只读数据，无租户字段；视图为 ReadOnlyModelViewSet 且需全量供角色编辑器勾选'
    queryset = Permission.objects.select_related('content_type').all().order_by('content_type__app_label', 'codename')
    serializer_class = PermissionSerializer
    permission_classes = [drf_permissions.IsAuthenticated, IsTenantAdminOrReadOnly]
    pagination_class = None
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['content_type__app_label']


class UserRoleViewSet(TenantAwareViewSetMixin, viewsets.GenericViewSet):
    """用户角色管理：列表查看 + 单用户设置角色。

    第四轮整改：修复跨租户提权——平台管理员可见全量；
    租户管理员仅可见本组织用户；普通用户仅可见自己。

    # 第六轮批次2：显式声明自管租户过滤，每个 return 分支收口 _apply_tenant_scope。
    """
    tenant_scope_self_managed = True
    tenant_scope_self_managed_reason = (
        '自定义 get_queryset 已按主体身份分级收敛用户可见范围：平台管理员全量、租户管理员限本组织（无组织时仅自己）、'
        '普通用户仅 id=自己，严于组织级隔离；若叠加自动解析（User 模型会被解析为 organization 过滤），'
        '普通用户将能看到同组织其他人的 PII，属可见性放宽，绝不可接受'
    )
    queryset = User.objects.all().order_by('id')
    serializer_class = UserRoleSerializer
    permission_classes = [drf_permissions.IsAuthenticated, IsTenantAdminOrReadOnly]

    def get_queryset(self):
        qs = self.queryset.all()
        user = self.request.user
        if not user.is_authenticated:
            return qs.none()
        if user.is_staff or user.is_superuser:
            return self._apply_tenant_scope(qs)
        if is_tenant_admin(user):
            org_id = getattr(user, 'organization_id', None)
            if org_id is None:
                return self._apply_tenant_scope(qs.filter(id=user.id))
            return self._apply_tenant_scope(qs.filter(organization_id=org_id))
        return self._apply_tenant_scope(qs.filter(id=user.id))

    def list(self, request):
        qs = self.get_queryset()
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(UserRoleSerializer(page, many=True).data)
        return Response(UserRoleSerializer(qs, many=True).data)

    def retrieve(self, request, pk=None):
        user = self.get_object()
        return Response(UserRoleSerializer(user).data)

    @action(detail=True, methods=['put', 'post'])
    def set_roles(self, request, pk=None):
        user = self.get_object()
        serializer = UserRoleSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserRoleSerializer(user).data)


class AuditLogViewSet(TenantScopedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related('user', 'organization').all()
    serializer_class = AuditLogSerializer
    permission_classes = [drf_permissions.IsAuthenticated, IsTenantAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['action', 'user', 'organization', 'resource_type', 'method']
    search_fields = ['path', 'ip_address', 'trace_id', 'body_snippet']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
