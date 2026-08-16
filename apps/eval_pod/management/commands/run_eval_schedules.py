"""P3-16 平台内部调度守护进程入口。

运行方式：
    python manage.py run_eval_schedules --once            # 仅扫描一次到期调度
    python manage.py run_eval_schedules --loop --interval 60   # 常驻守护，每 60s 扫描一次

--once 适合接入 CI / 系统 cron 周期性调用；--loop 即平台内置调度进程（无需外部 crontab）。
outputs 自动产出：调度配置了 agent_config 时经 call_model_sync 同步调用；生产也可在命令层
注入自定义 agent_fn（见 runners.run_scheduled_eval）。通知走 notifiers（飞书/企微/钉钉）。
"""
import time

from django.core.management.base import BaseCommand

from apps.eval_pod import scheduler


class Command(BaseCommand):
    help = 'P3-16 内部调度守护：扫描到期定时评测调度并执行 + 推送 IM 通知'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='仅执行一次扫描后退出')
        parser.add_argument('--loop', action='store_true', help='常驻守护，周期性扫描')
        parser.add_argument('--interval', type=int, default=60,
                            help='--loop 模式下的扫描间隔（秒），默认 60')
        parser.add_argument('--no-notify', action='store_true', help='跳过 IM 通知')

    def handle(self, *args, **options):
        notify = not options['no_notify']
        if options['once']:
            count = scheduler.tick(notify=notify)
            self.stdout.write(self.style.SUCCESS(f'[run_eval_schedules] 本次处理 {count} 条到期调度'))
            return
        # 默认 --loop 常驻
        self.stdout.write(self.style.WARNING(
            f'[run_eval_schedules] 启动内部调度守护，间隔 {options["interval"]}s（Ctrl+C 退出）'
        ))
        try:
            while True:
                count = scheduler.tick(notify=notify)
                if count:
                    self.stdout.write(self.style.SUCCESS(f'[run_eval_schedules] 处理 {count} 条到期调度'))
                time.sleep(options['interval'])
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('[run_eval_schedules] 守护进程已停止'))
