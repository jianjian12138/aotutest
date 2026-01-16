from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.api_testing.models import ScheduledTask
from apps.api_testing.views import ScheduledTaskViewSet
import time
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '运行定时任务调度器'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='检查间隔（秒），默认60秒'
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='只执行一次检查，不循环'
        )

    def handle(self, *args, **options):
        interval = options['interval']
        run_once = options['once']
        
        self.stdout.write(f"启动定时任务调度器，检查间隔: {interval}秒")
        
        view = ScheduledTaskViewSet()
        
        while True:
            try:
                self.check_and_run_tasks(view)
                
                if run_once:
                    break
                    
                time.sleep(interval)
                
            except KeyboardInterrupt:
                self.stdout.write("调度器已停止")
                break
            except Exception as e:
                logger.error(f"调度器运行出错: {e}")
                self.stdout.write(f"调度器运行出错: {e}")
                if run_once:
                    break
                time.sleep(interval)

    def check_and_run_tasks(self, view):
        """检查并运行到期的定时任务"""
        now = timezone.now()
        
        # 获取所有活跃的定时任务
        active_tasks = ScheduledTask.objects.filter(status='ACTIVE')
        
        for task in active_tasks:
            if task.should_run_now():
                self.stdout.write(f"执行定时任务: {task.name}")
                try:
                    # 创建执行日志
                    from apps.api_testing.models import TaskExecutionLog
                    execution_log = TaskExecutionLog.objects.create(
                        task=task,
                        status='PENDING'
                    )
                    
                    # 调用任务执行方法
                    view._execute_task_async(task, execution_log)
                    
                    self.stdout.write(f"任务 {task.name} 执行完成")
                    
                except Exception as e:
                    logger.error(f"执行任务 {task.name} 时出错: {e}")
                    self.stdout.write(f"执行任务 {task.name} 时出错: {e}")
            else:
                # 输出调试信息
                if task.next_run_time:
                    time_diff = (task.next_run_time - now).total_seconds()
                    if time_diff > 0:
                        self.stdout.write(f"任务 {task.name} 还需等待 {int(time_diff)} 秒")