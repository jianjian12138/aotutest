import time
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.api_testing.models import ScheduledTask, TaskExecutionLog
from apps.api_testing.views import ScheduledTaskViewSet

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '运行接口测试定时任务调度器'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('接口测试定时任务调度器已启动...'))
        
        viewset = ScheduledTaskViewSet()
        
        while True:
            try:
                # 获取所有激活状态且到达执行时间的任务
                now = timezone.now()
                tasks = ScheduledTask.objects.filter(
                    status='ACTIVE',
                    next_run_time__lte=now
                )
                
                if tasks.exists():
                    self.stdout.write(f"发现 {tasks.count()} 个待执行任务")
                    
                    for task in tasks:
                        self.stdout.write(f"正在执行任务: {task.name} (ID: {task.id})")
                        try:
                            # 立即更新下次运行时间，防止在任务执行期间被重复触发
                            old_next_run = task.next_run_time
                            task.next_run_time = task.calculate_next_run()
                            task.save(update_fields=['next_run_time'])
                            
                            # 创建执行日志
                            execution_log = TaskExecutionLog.objects.create(
                                task=task,
                                status='PENDING'
                            )
                            
                            # 使用 ViewSet 中的异步执行逻辑
                            viewset._execute_task_async(task, execution_log)
                            self.stdout.write(self.style.SUCCESS(f"任务 {task.name} 已触发执行，下次执行时间: {task.next_run_time}"))
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"触发任务 {task.name} 失败: {str(e)}"))
                            task.error_message = str(e)
                            task.save()
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"调度器运行异常: {str(e)}"))
            
            # 每隔 10 秒检查一次，提高灵敏度
            time.sleep(10)
