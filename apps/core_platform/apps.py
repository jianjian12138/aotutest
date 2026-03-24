from django.apps import AppConfig

class CorePlatformConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core_platform'
    verbose_name = 'Core Platform'
    label = 'core_platform'

    def ready(self):
        import apps.core_platform.signals

