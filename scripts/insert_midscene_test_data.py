import os
import sys
import django

# 设置 Django 环境
sys.path.append('d:\\TEST')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.midscene.models import MidsceneConfig, MidsceneTask

def run():
    User = get_user_model()
    # 尝试获取管理员用户，如果没有则获取第一个用户
    user = User.objects.filter(is_superuser=True).first() or User.objects.first()

    if not user:
        print("错误：系统中没有找到任何用户，无法创建任务。请先注册一个用户。")
        return

    print(f"使用用户: {user.username}")

    # 1. 检查或创建配置
    config, created = MidsceneConfig.objects.get_or_create(
        name='默认Chrome配置',
        defaults={
            'description': '用于测试的默认Chrome浏览器配置',
            'api_key': 'sk-test-mock-key', # 模拟的 key
            'base_url': 'https://api.midscene.ai/v1',
            'created_by': user,
            'is_active': True
        }
    )
    
    if created:
        print(f"已创建新配置: {config.name}")
    else:
        print(f"使用现有配置: {config.name}")

    # 2. 创建任务
    task_name = '百度搜索测试 - test'
    natural_language = '打开 https://www.baidu.com，在搜索框输入 "test"，点击"百度一下"按钮'
    
    task = MidsceneTask.objects.create(
        config=config,
        name=task_name,
        description='验证Midscene功能的测试任务，自动在百度搜索关键词',
        natural_language=natural_language,
        status='PENDING', # 等待执行
        created_by=user
    )

    print("-" * 30)
    print(f"✅ 成功插入测试数据！")
    print(f"任务ID: {task.id}")
    print(f"任务名称: {task.name}")
    print(f"指令内容: {task.natural_language}")
    print(f"关联配置: {config.name}")
    print("-" * 30)

if __name__ == '__main__':
    run()
