from django.apps import AppConfig


class PerformanceTestConfig(AppConfig):
    """性能测试应用配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.performance_test'
    verbose_name = '性能测试'
