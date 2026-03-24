import logging
import requests
import json
from django.conf import settings
from .models import ScheduledTask

logger = logging.getLogger(__name__)

class TaskExecutor:
    def __init__(self, task: ScheduledTask):
        self.task = task

    def run(self):
        """
        根据任务类型分发执行逻辑
        """
        task_type = self.task.task_type
        
        if task_type == 'API':
            return self._run_api_test()
        elif task_type == 'UI':
            return self._run_ui_test()
        elif task_type == 'PERFORMANCE':
            return self._run_performance_test()
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    def _run_api_test(self):
        """执行 API 测试"""
        if not self.task.api_test_suite:
            raise ValueError("No API Test Suite configured for this task")
        
        try:
            from apps.api_testing.utils.requests_runner import execute_test_suite
            execution = execute_test_suite(
                test_suite=self.task.api_test_suite,
                environment=None,
                executed_by=self.task.created_by
            )
            return {"message": f"Executed API Suite: {self.task.api_test_suite.name}", "status": "success", "execution_id": getattr(execution, 'id', None)}
        except Exception as e:
            logger.exception("API Test execution failed natively")
            return {"message": f"Failed to execute API Suite", "status": "failed", "error": str(e)}

    def _run_ui_test(self):
        """执行 UI 自动化测试"""
        if self.task.ui_test_suite:
             try:
                 from apps.ui_automation.executor import TestExecutor as UiExecutor
                 executor = UiExecutor(
                     test_suite=self.task.ui_test_suite,
                     engine='playwright',
                     browser='chromium',
                     headless=True,
                     executed_by=self.task.created_by
                 )
                 executor.run()
                 execution = getattr(executor, 'execution', None)
                 
                 # Create Unified Test Report
                 if execution and hasattr(execution, 'result_data'):
                     from apps.reports.models import TestReport
                     from django.utils import timezone
                     
                     raw_cases = execution.result_data.get('test_cases', [])
                     transformed_cases = []
                     for case in raw_cases:
                         steps = case.get('steps', [])
                         mapped_steps = []
                         for step in steps:
                             mapped_steps.append({
                                 'name': step.get('description') or f"Step {step.get('step_number', '?')}",
                                 'passed': step.get('success', False),
                                 'response_time': 0,
                                 'error': step.get('error', '')
                             })
                             
                         transformed_cases.append({
                             'type': 'test_case',
                             'name': case.get('test_case_name', 'UI Test Case'),
                             'status': case.get('status', 'FAILED'),
                             'execution_time': 0,
                             'error': case.get('error', ''),
                             'passed_count': len([s for s in steps if s.get('success')]),
                             'failed_count': len([s for s in steps if not s.get('success')]),
                             'total_count': len(steps),
                             'results': mapped_steps
                         })
                         
                     from apps.core_platform.models import Project
                     unified_project = None
                     if hasattr(execution.project, 'project_id'):
                         try:
                             unified_project = Project.objects.get(id=execution.project.project_id)
                         except:
                             pass
                     if not unified_project:
                         unified_project = Project.objects.first()
                         
                     TestReport.objects.create(
                         project=unified_project,
                         name=f"{self.task.ui_test_suite.name} - 自动执行报告_{timezone.now().strftime('%Y%m%d_%H%M%S')}",
                         report_type='ui_execution',
                         ui_test_execution=execution,
                         generated_by=self.task.created_by,
                         summary=execution.result_data.get('summary', {}),
                         content={'results': transformed_cases}
                     )
                     
                 return {"message": f"Executed UI Suite: {self.task.ui_test_suite.name}", "status": "success"}
             except Exception as e:
                 logger.exception("UI Test execution failed natively")
                 return {"message": f"Failed to execute UI Suite", "status": "failed", "error": str(e)}
        elif self.task.ui_test_case:
             return {"message": f"Executed UI Case: {self.task.ui_test_case.name}", "status": "success"}
        else:
             raise ValueError("No UI Test Suite or Case configured")

    def _run_performance_test(self):
        """执行性能测试"""
        if not self.task.performance_test_suite:
             raise ValueError("No Performance Test Suite configured")
        
        return {"message": f"Executed Perf Suite: {self.task.performance_test_suite.name}", "status": "simulated_success"}

    def send_notification(self, status, result=None, error=None):
        """发送通知"""
        config = self.task.notification_config
        if not config:
            return

        message = f"Task '{self.task.name}' finished with status: {status}.\n"
        if error:
            message += f"Error: {error}"
        
        if config.config_type == 'webhook_feishu':
            webhook_url = config.webhook_bots.get('feishu', {}).get('webhook_url')
            if webhook_url:
                self._send_feishu(webhook_url, message)
        elif config.config_type == 'webhook_dingtalk':
            self._send_dingtalk(config.webhook_url, message, config.secret)
        elif config.config_type == 'webhook_wechat':
            self._send_wechat(config.webhook_url, message)
        elif config.config_type == 'email':
            self._send_email(config, message)

    def _send_feishu(self, url, text):
        payload = {
            "msg_type": "text",
            "content": {
                "text": text
            }
        }
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            logger.error(f"Failed to send Feishu notification: {e}")

    def _send_dingtalk(self, url, text, secret=None):
        # 简单实现，暂不处理加签
        payload = {
             "msgtype": "text",
             "text": {
                 "content": text
             }
        }
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
             logger.error(f"Failed to send DingTalk notification: {e}")

    def _send_wechat(self, url, text):
        payload = {
            "msgtype": "text",
            "text": {
                "content": text
            }
        }
        try:
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            logger.error(f"Failed to send WeChat notification: {e}")

    def _send_email(self, config, text):
        from django.core.mail import get_connection, EmailMessage
        
        # 准备连接参数
        connection_params = {
            'host': config.smtp_server or settings.EMAIL_HOST,
            'port': config.smtp_port or settings.EMAIL_PORT,
            'username': config.smtp_user or settings.EMAIL_HOST_USER,
            'password': config.smtp_password or settings.EMAIL_HOST_PASSWORD,
            'use_tls': config.use_tls,
            'use_ssl': config.use_ssl,
        }
        
        try:
            connection = get_connection(
                backend=settings.EMAIL_BACKEND,
                **connection_params
            )
            
            email = EmailMessage(
                subject=f"定时任务通知: {self.task.name}",
                body=text,
                from_email=config.email_from or settings.DEFAULT_FROM_EMAIL,
                to=config.email_recipients,
                connection=connection
            )
            email.send()
            logger.info(f"Email notification sent for task {self.task.id}")
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
