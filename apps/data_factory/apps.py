from django.apps import AppConfig


class DataFactoryConfig(AppConfig):
    """数据工厂应用配置"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.data_factory'
    verbose_name = '数据工厂'
