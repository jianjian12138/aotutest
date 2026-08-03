"""
Phase 0 回归测试：租户功能开关的 fail-closed 语义。

验证：
1. 已开通租户的成员可通过对该功能的门禁；
2. 他租户（未开通）的成员被拒绝；
3. 无组织归属用户被拒绝（无法解析租户）；
4. 功能关闭后从"通过"变为"拒绝"。
"""
from django.test import TestCase

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from apps.core_platform.models import Organization, User

from .models import FeatureCode, TenantFeature
from .permissions import HasTenantFeature, tenant_has_feature


class _GatedView(APIView):
    permission_classes = [IsAuthenticated, HasTenantFeature]
    required_feature = FeatureCode.AGENT_EVAL

    def get(self, request):
        return Response({'ok': True})


class TenantFeatureGateTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org_a = Organization.objects.create(name='甲方A', code='org-a')
        cls.org_b = Organization.objects.create(name='甲方B', code='org-b')

        cls.user_a = User.objects.create_user('ua', password='x')
        cls.user_a.organization = cls.org_a
        cls.user_a.save()

        cls.user_b = User.objects.create_user('ub', password='x')
        cls.user_b.organization = cls.org_b
        cls.user_b.save()

        TenantFeature.objects.create(
            tenant=cls.org_a, feature_code=FeatureCode.AGENT_EVAL, enabled=True
        )

        cls.factory = APIRequestFactory()

    def _gate_allows(self, user):
        req = self.factory.get('/x/')
        req.user = user
        req.auth = None
        perm = HasTenantFeature()
        return perm.has_permission(req, _GatedView())

    def test_enabled_tenant_passes(self):
        self.assertTrue(tenant_has_feature(self.org_a, FeatureCode.AGENT_EVAL))
        self.assertTrue(self._gate_allows(self.user_a))

    def test_other_tenant_denied(self):
        self.assertFalse(tenant_has_feature(self.org_b, FeatureCode.AGENT_EVAL))
        self.assertFalse(self._gate_allows(self.user_b))

    def test_user_without_org_denied(self):
        user_none = User.objects.create_user('un', password='x')
        user_none.organization = None
        user_none.save()
        self.assertFalse(tenant_has_feature(None, FeatureCode.AGENT_EVAL))
        self.assertFalse(self._gate_allows(user_none))

    def test_disabled_then_enabled(self):
        tf = TenantFeature.objects.create(
            tenant=self.org_b, feature_code=FeatureCode.AGENT_EVAL, enabled=False
        )
        self.assertFalse(tenant_has_feature(self.org_b, FeatureCode.AGENT_EVAL))
        self.assertFalse(self._gate_allows(self.user_b))

        tf.enabled = True
        tf.save()
        self.assertTrue(tenant_has_feature(self.org_b, FeatureCode.AGENT_EVAL))
        self.assertTrue(self._gate_allows(self.user_b))
