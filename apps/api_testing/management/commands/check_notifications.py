from django.core.management.base import BaseCommand
from apps.api_testing.models import ScheduledTask, TaskNotificationSetting

class Command(BaseCommand):
    help = '检查通知设置状态'

    def handle(self, *args, **options):
        self.stdout.write("=== 检查通知设置状态 ===")
        
        # 检查定时任务和通知设置
        tasks = ScheduledTask.objects.all()
        settings = TaskNotificationSetting.objects.all()
        
        self.stdout.write(f"定时任务数量: {tasks.count()}")
        self.stdout.write(f"通知设置数量: {settings.count()}")
        
        self.stdout.write("\n定时任务详情:")
        for task in tasks:
            self.stdout.write(f"- ID: {task.id}, Name: {task.name}")
            self.stdout.write(f"  成功时通知: {task.notify_on_success}")
            self.stdout.write(f"  失败时通知: {task.notify_on_failure}")
            
            # 检查通知设置
            notification_setting = task.notification_settings.first()
            if notification_setting:
                self.stdout.write(f"  通知设置: ID {notification_setting.id}, 类型 {notification_setting.notification_type}, 启用 {notification_setting.is_enabled}")
            else:
                self.stdout.write(f"  通知设置: 未找到")
        
        self.stdout.write("\n独立的通知设置详情:")
        for setting in settings:
            self.stdout.write(f"- ID: {setting.id}, Task ID: {setting.task_id}")
            self.stdout.write(f"  类型: {setting.notification_type}, 启用: {setting.is_enabled}")
            self.stdout.write(f"  成功通知: {setting.notify_on_success}, 失败通知: {setting.notify_on_failure}")
        
        self.stdout.write("\n=== 检查完成 ===")