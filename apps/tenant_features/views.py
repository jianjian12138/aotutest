"""
租户功能开关 API（路线三 · Phase 0）。

- 普通租户成员：GET 仅可见本租户功能开通状态（供前端按能力动态渲染入口，实现"用不到就不可见"）。
- 租户管理员（tenant_admin）/ 平台管理员：可开通或关闭本租户功能（写受 IsTenantAdminOrReadOnly 保护）。
"""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.core_platform.permissions import IsTenantAdminOrReadOnly

from .models import TenantFeature
from .serializers import TenantFeatureSerializer


class TenantFeatureViewSet(viewsets.ModelViewSet):
    serializer_class = TenantFeatureSerializer
    permission_classes = [IsAuthenticated, IsTenantAdminOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return TenantFeature.objects.all()
        org = getattr(user, 'organization', None)
        if org is None:
            return TenantFeature.objects.none()
        return TenantFeature.objects.filter(tenant=org)
