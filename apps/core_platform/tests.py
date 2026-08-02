"""core_platform 单元测试（Django TestCase，运行：python manage.py test apps.core_platform）。

覆盖阶段 0/1 二次评审修复点：
- crypto：明文/None 透传（无需密钥）、加密前缀
- is_tenant_admin：超级管理员 True、普通用户 False（不依赖未播种权限）
"""
from django.test import TestCase
from django.contrib.auth import get_user_model

from backend.utils.crypto import decrypt_value, encrypt_value
from apps.core_platform.permissions import is_tenant_admin

User = get_user_model()


class CryptoPassthroughTest(TestCase):
    def test_plaintext_passthrough(self):
        # 历史明文数据原样返回（无需密钥）
        self.assertEqual(decrypt_value("hello"), "hello")

    def test_none_passthrough(self):
        self.assertIsNone(decrypt_value(None))

    def test_encrypt_prefix(self):
        enc = encrypt_value("secret")
        self.assertTrue(enc.startswith("enc:v1:"))


class TenantAdminTest(TestCase):
    def test_superuser_is_admin(self):
        u = User.objects.create(username="su", is_staff=True, is_superuser=True)
        self.assertTrue(is_tenant_admin(u))

    def test_regular_not_admin(self):
        u = User.objects.create(username="u")
        self.assertFalse(is_tenant_admin(u))
