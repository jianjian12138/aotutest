from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from ..models import Organization
from ..permissions import IsAdminOrReadOnly, TenantAwareViewSetMixin
from ..serializers.organizations import OrganizationSerializer


class OrganizationViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    """【V3.5】租户/组织管理: Multi-Tenancy Core

    第四轮整改：
    - 组织即租户边界本体：非管理员仅可见自己所属组织；写操作仅平台管理员。
    - 移除模拟 SSO 端点（sso-login-simulate）：属演示遗留代码，存在伪造凭据风险，
      前端无引用（已 grep 确认），真实 SSO 应走标准 OAuth/OIDC 流程另行实现。

    # 第六轮批次2：接入统一租户隔离。Organization 自身即租户本体（无 organization 外键），
    # 显式声明 org_field='id'，mixin 产生 filter(id=user.organization_id)，
    # 与原手工 get_queryset 完全等价（未认证/无组织均 fail-closed 返回空集），故删除手工实现。
    """
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    org_field = 'id'

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        org = self.get_object()
        users = org.users.all()
        return Response({
            "status": "SUCCESS",
            "members": [u.username for u in users]
        })
