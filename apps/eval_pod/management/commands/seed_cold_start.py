"""
P3-5 冷启动：为开通 AGENT_EVAL 的租户幂等种子默认评分器模板。

用法：
  python manage.py seed_cold_start                 # 全部开通 agent 测评的租户
  python manage.py seed_cold_start --org-code org-xxx   # 仅指定租户
  python manage.py seed_cold_start --dry-run        # 只列出将种子的租户，不写入

幂等：按 (organization, name) 唯一，已存在的同名评分器模板自动跳过。
"""
from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.core_platform.models import Organization
from apps.tenant_features.models import FeatureCode, TenantFeature
from apps.eval_pod.cold_start import apply_cold_start


class Command(BaseCommand):
    help = 'P3-5 冷启动：为开通 AGENT_EVAL 的租户种子默认评分器模板（幂等）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--org-code', dest='org_code', default=None,
            help='仅对指定租户 code 种子；缺省为全部开通 agent 测评的租户',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='只打印将种子的租户，不写入数据库',
        )

    def handle(self, *args, **options):
        org_code = options.get('org_code')
        dry = options.get('dry_run')

        orgs = Organization.objects.all()
        if org_code:
            orgs = orgs.filter(code=org_code)
        else:
            enabled = TenantFeature.objects.filter(
                Q(feature_code=FeatureCode.AGENT_EVAL) & Q(enabled=True)
            ).values_list('tenant_id', flat=True)
            orgs = orgs.filter(id__in=enabled)

        total_created = 0
        count = 0
        for org in orgs:
            count += 1
            if dry:
                self.stdout.write(f'[dry-run] {org.code} ({org.name})')
                continue
            res = apply_cold_start(org)
            total_created += len(res['created'])
            skip = len(res['skipped'])
            self.stdout.write(
                f'{org.code}: created={len(res["created"])} skipped={skip}'
            )
        if dry:
            self.stdout.write(self.style.WARNING(f'[dry-run] 共 {count} 个租户（未写入）'))
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Done. 处理 {count} 个租户，总新建 {total_created} 个评分器模板')
            )
