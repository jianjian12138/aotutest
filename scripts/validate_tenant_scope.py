"""第四轮整改验证：校验所有接入 TenantAwareViewSetMixin 的 ViewSet 租户过滤路径可被 ORM 编译。

用法：DEBUG=true .venv311/Scripts/python.exe scripts/validate_tenant_scope.py
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

import importlib
import inspect

from apps.core_platform.permissions import TenantAwareViewSetMixin

VIEW_MODULES = [
    'apps.cicd.views',
    'apps.requirement_analysis.views',
    'apps.data_factory.views',
    'apps.executions.views',
    'apps.reviews.views',
    'apps.strix_security.views',
]

ok, bad, skipped = [], [], []

for mod_name in VIEW_MODULES:
    mod = importlib.import_module(mod_name)
    for name, cls in inspect.getmembers(mod, inspect.isclass):
        if cls.__module__ != mod_name:
            continue
        if not issubclass(cls, TenantAwareViewSetMixin):
            continue
        qs = getattr(cls, 'queryset', None)
        if qs is None:
            skipped.append(f'{mod_name}.{name} (无 queryset)')
            continue
        model = qs.model
        org_field = getattr(cls, 'org_field', None)
        # 复刻 mixin 的解析逻辑
        if org_field:
            filt = org_field
        else:
            fields = model._meta.get_fields()
            field_names = [f.name for f in fields]
            if 'organization' in field_names:
                filt = 'organization'
            elif any(f.name == 'project' and getattr(f, 'is_relation', False) for f in fields):
                filt = 'project__organization'
            elif 'created_by' in field_names:
                filt = 'created_by'
            elif 'creator' in field_names:
                filt = 'creator'
            else:
                skipped.append(f'{mod_name}.{name} (fail-closed，无租户字段)')
                continue
        try:
            str(model.objects.filter(**{filt: 1}).query)  # 强制编译，验证路径
            ok.append(f'{mod_name}.{name} -> {filt}')
        except Exception as e:
            bad.append(f'{mod_name}.{name} -> {filt} : {type(e).__name__}: {e}')

print(f'== 通过 ({len(ok)}) ==')
for line in ok:
    print('  OK ', line)
print(f'== fail-closed/跳过 ({len(skipped)}) ==')
for line in skipped:
    print('  -- ', line)
print(f'== 失败 ({len(bad)}) ==')
for line in bad:
    print('  !! ', line)

sys.exit(1 if bad else 0)
