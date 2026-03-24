from apps.notifications.models import NotificationConfig, NotificationLog
from django.utils import timezone
from .models import ScheduledTask, TaskExecutionLog
from .executor import TaskExecutor
import logging

logger = logging.getLogger(__name__)

def execute_scheduled_task(task_id):
    """
    执行定时任务的 Celery Task
    """
    try:
        task = ScheduledTask.objects.get(id=task_id)
    except ScheduledTask.DoesNotExist:
        logger.error(f"Task with id {task_id} not found.")
        return

    # 创建执行日志
    log = TaskExecutionLog.objects.create(
        task=task,
        status='RUNNING',
        start_time=timezone.now()
    )

    try:
        # 更新任务最后运行时间
        task.last_run_time = timezone.now()
        task.total_runs += 1
        task.save(update_fields=['last_run_time', 'total_runs'])

        # 执行具体逻辑
        executor = TaskExecutor(task)
        result = executor.run()

        # 更新日志为成功
        log.status = 'SUCCESS'
        log.end_time = timezone.now()
        log.duration = (log.end_time - log.start_time).total_seconds()
        log.result = result
        log.save()

        # 更新任务统计
        task.successful_runs += 1
        task.save(update_fields=['successful_runs'])

        # 发送通知 (如果配置了成功通知)
        if task.notify_on_success and task.notification_config:
            executor.send_notification(status='SUCCESS', result=result)

    except Exception as e:
        logger.exception(f"Error executing task {task_id}: {str(e)}")
        
        # 更新日志为失败
        log.status = 'FAILED'
        log.end_time = timezone.now()
        log.duration = (log.end_time - log.start_time).total_seconds()
        log.error_message = str(e)
        log.save()

        # 更新任务统计
        task.failed_runs += 1
        task.save(update_fields=['failed_runs'])

        # 发送通知 (如果配置了失败通知)
        if task.notify_on_failure and task.notification_config:
            # Re-instantiate executor just for notification if needed, or handle statically
            # Ideally executor instance is alive, but if it crashed during run(), we might need a fresh one or helper
            try:
                executor = TaskExecutor(task)
                executor.send_notification(status='FAILED', error=str(e))
            except:
                pass
