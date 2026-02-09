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
        
        # 调用 API Testing 模块的执行逻辑
        # 假设 apps.api_testing.services.TestSuiteExecutor 存在
        # 这里需要根据实际的 api_testing 模块实现进行调整
        from apps.api_testing.models import TestSuite
        # 模拟调用，实际需替换为真实调用
        # executor = TestSuiteExecutor(self.task.api_test_suite)
        # return executor.run()
        
        return {"message": f"Executed API Suite: {self.task.api_test_suite.name}", "status": "simulated_success"}

    def _run_ui_test(self):
        """执行 UI 自动化测试"""
        if self.task.ui_test_suite:
             # 执行测试套件
             return {"message": f"Executed UI Suite: {self.task.ui_test_suite.name}", "status": "simulated_success"}
        elif self.task.ui_test_case:
             # 执行单个用例
             return {"message": f"Executed UI Case: {self.task.ui_test_case.name}", "status": "simulated_success"}
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
            self._send_feishu(config.webhook_url, message)
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
