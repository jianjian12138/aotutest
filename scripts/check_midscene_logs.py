import os
import sys
import django

# 设置 Django 环境
sys.path.append('d:\\TEST')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.midscene.models import MidsceneTask

def check_logs():
    # 获取最近的一个失败任务
    task = MidsceneTask.objects.filter(status='FAILED').order_by('-start_time').first()
    
    if not task:
        print("没有找到失败的任务")
        return

    print(f"任务ID: {task.id}")
    print(f"任务名称: {task.name}")
    print(f"错误日志:\n{task.logs}")

if __name__ == '__main__':
    check_logs()
