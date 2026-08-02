"""双租户隔离实测（甲方验收硬证据）。

模拟两个组织 OrgA / OrgB 与各自成员 user_a / user_b，外加管理员 admin，
验证：
  1. 各自创建的资源（核心 Project / API 测试 Project / UI 设备）仅创建者可见；
  2. 另一租户成员通过列表与按 ID 直取均不可见（404/403，列表无交集）；
  3. 严格 fail-closed：即便是管理员（is_staff，非 owner/成员）亦不可越权读取他租户数据，
     平台不存在"超级读者"，隔离对所有非授权主体一致生效；
  4. #157 修复后的 UiDevice 按 organization 隔离生效。

走真实 HTTP 链路（DRF APIClient + force_authenticate），覆盖视图集 get_queryset /
权限 / 序列化全链路，是比单测更贴近生产的端到端证据。

运行：DEBUG=true python manage.py test tests.test_tenant_isolation -v 2
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.core_platform.models import Organization, Project
from apps.api_testing.models import ApiProject
from apps.ui_automation.models.device import UiDevice


def _unwrap(resp):
    """统一响应防腐中间件把负载包在 {"code","message","data",...} 中。"""
    body = resp.json()
    return body.get('data', body), body.get('code', resp.status_code)


def _ids(resp):
    """兼容分页/非分页两种列表响应，提取 id 列表。"""
    data, _ = _unwrap(resp)
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        for key in ('results', 'items', 'list'):
            if key in data and isinstance(data[key], list):
                items = data[key]
                break
        else:
            items = []
    else:
        items = []
    return [i.get('id') for i in items]


class DualTenantIsolationTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.org_a = Organization.objects.create(name='验收测试-OrgA', code='ORGA')
        cls.org_b = Organization.objects.create(name='验收测试-OrgB', code='ORGB')
        cls.user_a = User.objects.create_user('tenant_a_user', password='Test@12345')
        cls.user_a.organization = cls.org_a
        cls.user_a.save()
        cls.user_b = User.objects.create_user('tenant_b_user', password='Test@12345')
        cls.user_b.organization = cls.org_b
        cls.user_b.save()
        # 平台级管理员（无组织归属），用于验证"平台不存在超级读者"：
        # 即便 is_staff/is_superuser 也不可越权读取他租户数据。
        cls.admin = User.objects.create_user('tenant_admin_user', password='Test@12345',
                                             is_staff=True, is_superuser=True)

    def _client(self, user):
        c = APIClient()
        c.force_authenticate(user)
        return c

    @staticmethod
    def _assert_created(r, label):
        data, code = _unwrap(r)
        assert code in (200, 201), f'{label} 创建失败 {code}: {data}'

    def test_core_project_isolation(self):
        ua, ub = self.user_a, self.user_b
        ca = self._client(ua)
        r = ca.post('/api/projects/', {'name': 'A项目', 'project_type': 'API',
                                       'status': 'active'}, format='json')
        self._assert_created(r, '核心项目')
        pa_id = Project.objects.get(name='A项目', owner=ua).id

        rb = self._client(ub)
        self.assertNotIn(pa_id, _ids(rb.get('/api/projects/')),
                         'user_b 竟能看见 user_a 的核心项目')
        self.assertIn(rb.get(f'/api/projects/{pa_id}/').status_code, (403, 404),
                      'user_b 直取他租户项目应被拒')

    def test_api_testing_project_isolation(self):
        ua, ub = self.user_a, self.user_b
        ca = self._client(ua)
        r = ca.post('/api/api-testing/projects/',
                    {'name': 'API项目A', 'base_url': 'http://example.com/a',
                     'project_type': 'HTTP', 'status': 'NOT_STARTED',
                     'description': '隔离测试'}, format='json')
        self._assert_created(r, 'API测试项目')
        api_id = ApiProject.objects.get(name='API项目A').id

        rb = self._client(ub)
        self.assertNotIn(api_id, _ids(rb.get('/api/api-testing/projects/')),
                         'user_b 竟能看见 user_a 的 API 测试项目')
        self.assertIn(rb.get(f'/api/api-testing/projects/{api_id}/').status_code, (403, 404))

    def test_uidevice_organization_isolation(self):
        """#157 修复验证：UiDevice 按 organization 隔离。"""
        ua, ub = self.user_a, self.user_b
        ca = self._client(ua)
        r = ca.post('/api/ui-automation/devices/',
                    {'name': '设备A', 'device_id': 'dev-a-0001', 'platform': 'android',
                     'type': 'real', 'status': 'online', 'version': '1.0'}, format='json')
        self._assert_created(r, 'UI设备')
        dev = UiDevice.objects.get(device_id='dev-a-0001')
        dev_id = dev.id
        self.assertEqual(dev.organization_id, self.org_a.id, '设备未归属创建者组织')

        rb = self._client(ub)
        self.assertNotIn(dev_id, _ids(rb.get('/api/ui-automation/devices/')),
                         'user_b 竟能看见 user_a 组织的设备')
        self.assertIn(rb.get(f'/api/ui-automation/devices/{dev_id}/').status_code, (403, 404))

    def test_admin_no_super_reader_uidevice(self):
        """RBAC 一致性回归：admin 亦非"超级读者"，不可越权读取他租户 UiDevice。

        收尾批次将 UiDeviceViewSet.staff_has_full_access 由 True 改为 False，
        使 UiDevice 与 Project/ApiProject 保持一致——admin 同样按 organization 严格
        fail-closed，无组织归属的 admin 看不到任何他租户设备。
        """
        ua = self.user_a
        ca = self._client(ua)
        r = ca.post('/api/ui-automation/devices/',
                    {'name': '设备A2', 'device_id': 'dev-a-0002', 'platform': 'android',
                     'type': 'real', 'status': 'online', 'version': '1.0'}, format='json')
        self._assert_created(r, 'UI设备')
        dev_id = UiDevice.objects.get(device_id='dev-a-0002').id

        cadmin = self._client(self.admin)
        self.assertNotIn(dev_id, _ids(cadmin.get('/api/ui-automation/devices/')),
                         'admin 竟能越权看见他租户设备（应为严格 fail-closed）')
        self.assertIn(cadmin.get(f'/api/ui-automation/devices/{dev_id}/').status_code, (403, 404),
                      'admin 直取他租户设备应被拒')
