from django.apps import AppConfig


class TenantFeaturesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tenant_features'
    verbose_name = '租户功能开关'
    label = 'tenant_features'
