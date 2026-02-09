import os
from celery import Celery

# 设置默认 Django 设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

app = Celery('backend')

# 使用 Django 的 settings 文件配置 Celery
# 所有 Celery 配置项都必须以 CELERY_ 开头
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现各个 App 下的 tasks.py
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
