# -*- coding: utf-8 -*-
"""第六轮批次1：插入演示数据供测试验收使用（幂等，可重复执行）。

设计目标：
  1. 构造【双租户】数据（演示租户A / 演示租户B），可直接用于验收租户隔离：
     用 demo_user_a 登录应只能看到 A 的数据，demo_user_b 只能看到 B 的数据。
  2. 所有演示数据名称带「演示-」前缀，描述中显式标注"演示数据"，与真实数据可区分。
  3. 演示账号（密码均为 Demo@12345）：
     - demo_admin   平台管理员（is_staff，全量可见）
     - demo_user_a  租户A普通用户
     - demo_user_b  租户B普通用户

用法：
  DEBUG=true python scripts/seed_demo_data.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

import django  # noqa: E402

django.setup()

from apps.core_platform.models import Organization, Project  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402

User = get_user_model()

DEMO_PASSWORD = 'Demo@12345'
created, skipped = [], []


def log(flag, what):
    (created if flag else skipped).append(what)


def main():
    # 1. 双租户
    org_a, f = Organization.objects.get_or_create(
        code='DEMO-ORG-A',
        defaults={'name': '演示-租户A', 'description': '演示数据：租户A（供验收租户隔离）'})
    log(f, 'Organization 演示-租户A')
    org_b, f = Organization.objects.get_or_create(
        code='DEMO-ORG-B',
        defaults={'name': '演示-租户B', 'description': '演示数据：租户B（供验收租户隔离）'})
    log(f, 'Organization 演示-租户B')

    # 2. 演示账号
    def ensure_user(username, org, is_staff=False):
        user, f = User.objects.get_or_create(username=username, defaults={
            'email': f'{username}@demo.local',
            'organization': org,
            'is_staff': is_staff,
        })
        if f:
            user.set_password(DEMO_PASSWORD)
            user.save()
        log(f, f'User {username}')
        return user

    ensure_user('demo_admin', org_a, is_staff=True)
    user_a = ensure_user('demo_user_a', org_a)
    user_b = ensure_user('demo_user_b', org_b)

    # 3. 每个租户一个演示项目
    proj_a, f = Project.objects.get_or_create(
        name='演示-租户A项目', defaults={
            'description': '演示数据：租户A的项目，仅 demo_user_a / demo_admin 可见',
            'organization': org_a, 'owner': user_a})
    log(f, 'Project 演示-租户A项目')
    if f:
        proj_a.members.add(user_a)
    proj_b, f = Project.objects.get_or_create(
        name='演示-租户B项目', defaults={
            'description': '演示数据：租户B的项目，仅 demo_user_b / demo_admin 可见',
            'organization': org_b, 'owner': user_b})
    log(f, 'Project 演示-租户B项目')
    if f:
        proj_b.members.add(user_b)

    # 4. 通知配置（每租户一条，webhook_url 为无害占位，验证掩码输出）
    try:
        from apps.notifications.models import NotificationConfig
        for owner, tag in ((user_a, 'A'), (user_b, 'B')):
            _, f = NotificationConfig.objects.get_or_create(
                name=f'演示-通知配置{tag}', created_by=owner, defaults={
                    'config_type': 'webhook_feishu',
                    'webhook_bots': {'feishu': {
                        'name': f'演示机器人{tag}（演示数据，非真实）',
                        'webhook_url': 'https://open.feishu.cn/open-apis/bot/v2/hook/DEMO-PLACEHOLDER',
                        'enabled': False}},
                    'is_active': False})
            log(f, f'NotificationConfig 演示-通知配置{tag}')
    except Exception as e:  # noqa: BLE001
        skipped.append(f'NotificationConfig 失败: {e}')

    # 5. 测试用例（若模型字段兼容，各租户两条）
    try:
        from apps.testcases.models import TestCase
        field_names = {fld.name for fld in TestCase._meta.get_fields()}
        for proj, owner, tag in ((proj_a, user_a, 'A'), (proj_b, user_b, 'B')):
            for i in (1, 2):
                defaults = {'description': f'演示数据：租户{tag}测试用例{i}，供验收使用'}
                if 'project' in field_names:
                    kw = {'title' if 'title' in field_names else 'name': f'演示-用例{tag}{i}',
                          'project': proj}
                    for owner_field in ('created_by', 'creator', 'author'):
                        if owner_field in field_names:
                            defaults[owner_field] = owner
                    obj, f = TestCase.objects.get_or_create(**kw, defaults=defaults)
                    log(f, f'TestCase 演示-用例{tag}{i}')
    except Exception as e:  # noqa: BLE001
        skipped.append(f'TestCase 跳过: {e}')

    print('=' * 60)
    print('演示数据插入完成（幂等，可重复执行）')
    print(f'新建 {len(created)} 项：')
    for c in created:
        print('  +', c)
    print(f'已存在/跳过 {len(skipped)} 项：')
    for s in skipped:
        print('  =', s)
    print('-' * 60)
    print('验收方法：')
    print('  1. demo_user_a / Demo@12345 登录 → 仅见 演示-租户A项目 及 A 侧数据')
    print('  2. demo_user_b / Demo@12345 登录 → 仅见 演示-租户B项目 及 B 侧数据')
    print('  3. demo_admin  / Demo@12345 登录 → 全量可见（is_staff）')
    print('  4. 通知配置读接口应只返回 webhook_bots_masked（掩码），不含明文 URL/secret')


if __name__ == '__main__':
    main()
