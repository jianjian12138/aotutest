"""
租户功能开关权限（路线三 · Phase 0）。

用法：
    from apps.tenant_features.permissions import HasTenantFeature
    from apps.tenant_features.models import FeatureCode

    class AgentEvalView(APIView):
        permission_classes = [IsAuthenticated, HasTenantFeature]
        required_feature = FeatureCode.AGENT_EVAL

严格 fail-closed 语义：
- 未认证                         → 拒绝；
- 未声明 required_feature        → 放行（向后兼容，不强制所有视图都接入）；
- 用户无组织归属                 → 拒绝（无法解析租户）；
- 租户未开通 / 已过期            → 拒绝。

注意：平台管理员（is_staff / is_superuser）同样受控。功能开关代表的是
"该租户是否购买/开通此能力"，不应因操作人员是平台管理员而越权使用他租户
未开通的能力。租户级管理（开通/关闭）走单独的 TenantFeatureViewSet，由
IsTenantAdminOrReadOnly 保护。
"""
from rest_framework import permissions

from .models import TenantFeature


def tenant_has_feature(org, code):
    """判定某租户是否拥有并开通指定功能（含过期检查）。org 为 None 时返回 False。"""
    if org is None:
        return False
    tf = TenantFeature.objects.filter(tenant=org, feature_code=code).first()
    if tf is None:
        return False
    return tf.is_active


class HasTenantFeature(permissions.BasePermission):
    message = '当前租户未开通该功能，或功能已过期。'
    required_feature = None

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        # 允许在视图或权限类上声明 required_feature
        feature = getattr(view, 'required_feature', None) or self.required_feature
        if not feature:
            return True
        org = getattr(user, 'organization', None)
        return tenant_has_feature(org, feature)
