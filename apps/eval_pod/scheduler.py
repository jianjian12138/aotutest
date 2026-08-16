"""P3-16 平台内部调度守护核心。

tick() 扫描到期（next_run_at <= now）且启用的调度，逐个触发评测运行并推送 IM 通知，
随后更新 last_run_* / next_run_at。由 management 命令 run_eval_schedules 周期性调用，
无需外部 crontab / Celery beat。
"""
from django.utils import timezone

from .models import EvalSchedule
from . import runners, notifiers


def tick(agent_fn=None, notify=True):
    """执行所有到期调度，返回处理条数。"""
    now = timezone.now()
    due = EvalSchedule.objects.filter(enabled=True, next_run_at__lte=now)
    processed = 0
    for s in due:
        try:
            run = runners.run_scheduled_eval(s, agent_fn=agent_fn)
            s.last_run_id = run.id
            s.last_status = 'OK'
            s.last_error = ''
            if notify and s.notify_channels:
                text = notifiers.build_run_summary(run, s)
                notifiers.notify_im(s.notify_channels, f'评测调度完成：{s.name}', text)
        except Exception as exc:  # noqa: BLE001
            s.last_status = 'ERROR'
            s.last_error = str(exc)[:500]
            if notify and s.notify_channels:
                notifiers.notify_im(
                    s.notify_channels, f'评测调度失败：{s.name}',
                    f'错误：{str(exc)[:300]}',
                )
        s.last_run_at = now
        s.next_run_at = s.compute_next_run(now)
        s.save()
        processed += 1
    return processed
