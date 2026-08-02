"""
创建平台超级管理员。

安全要求：
- 口令不允许硬编码；优先读取环境变量 ADMIN_PASSWORD；
- 未提供时自动生成随机强口令并在控制台一次性输出（请立即保存并尽快修改）。

用法：
    ADMIN_USERNAME=admin ADMIN_PASSWORD='StrongP@ss' python create_admin.py
或（自动生成随机口令）：
    python create_admin.py
"""
import os
import secrets
import string

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.core_platform.models import User  # noqa: E402


def generate_password(length=16):
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def main():
    username = os.environ.get('ADMIN_USERNAME', 'admin')
    email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
    password = os.environ.get('ADMIN_PASSWORD', '')

    if User.objects.filter(username=username).exists():
        print(f'Superuser "{username}" already exists! (未做任何修改)')
        return

    generated = False
    if not password:
        password = generate_password()
        generated = True

    if len(password) < 8:
        print('错误：ADMIN_PASSWORD 长度不得小于 8 位。')
        raise SystemExit(1)

    User.objects.create_superuser(username=username, email=email, password=password)
    print(f'Superuser "{username}" created successfully!')
    if generated:
        print('==============================================')
        print(f'  初始随机口令（仅显示一次，请立即保存）: {password}')
        print('  登录后请立即修改口令。')
        print('==============================================')


if __name__ == '__main__':
    main()
