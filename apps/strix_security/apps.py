from django.apps import AppConfig


class StrixSecurityConfig(AppConfig):
    """Strix安全测试应用配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.strix_security'
    verbose_name = 'Strix安全测试'
