from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class NotificationConfig(models.Model):
    """统一通知配置模型"""
    CONFIG_TYPE_CHOICES = [
        ('webhook_feishu', '飞书机器人'),
        ('webhook_wechat', '企业微信机器人'),
        ('webhook_dingtalk', '钉钉机器人'),
    ]

    name = models.CharField(max_length=100, verbose_name='配置名称', help_text='用于标识该通知配置的名称')
    config_type = models.CharField(max_length=20, choices=CONFIG_TYPE_CHOICES, default='webhook_feishu', verbose_name='配置类型')
    webhook_bots = models.JSONField(default=dict, blank=True, null=True, verbose_name='Webhook机器人配置', help_text='飞书、企业微信、钉钉机器人配置')
    is_default = models.BooleanField(default=False, verbose_name='是否默认配置')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')

    enable_ui_automation = models.BooleanField(default=True, verbose_name='启用UI自动化通知')
    enable_api_testing = models.BooleanField(default=True, verbose_name='启用接口测试通知')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='创建者')

    class Meta:
        db_table = 'notifications_config'
        verbose_name = '统一通知配置'
        verbose_name_plural = '统一通知配置'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['config_type']),
            models.Index(fields=['is_default']),
            models.Index(fields=['created_by']),
        ]

    def __str__(self):
        return f"{self.name} - {self.get_config_type_display()}"

    def get_webhook_bots(self):
        """获取配置的所有webhook机器人"""
        bots = []
        if self.webhook_bots:
            for bot_type, bot_config in self.webhook_bots.items():
                bot_data = {
                    'type': bot_type,
                    'name': bot_config.get('name', f'{bot_type}机器人'),
                    'webhook_url': bot_config.get('webhook_url'),
                    'enabled': bot_config.get('enabled', True)
                }
                if bot_type == 'dingtalk' and bot_config.get('secret'):
                    bot_data['secret'] = bot_config.get('secret')
                bots.append(bot_data)
        return bots


class NotificationLog(models.Model):
    """统一通知日志模型"""
    NOTIFICATION_TYPES = [
        ('task_execution', '定时任务执行'),
        ('test_suite_execution', '测试套件执行'),
        ('test_case_execution', '测试用例执行'),
        ('api_request_execution', '单接口/单脚本执行'),
        ('system_alert', '系统警告'),
        ('manual', '手动通知'),
    ]

    STATUS_CHOICES = [
        ('pending', '待发送'),
        ('sending', '发送中'),
        ('success', '发送成功'),
        ('failed', '发送失败'),
        ('cancelled', '已取消'),
    ]

    module = models.CharField(max_length=50, blank=True, null=True, verbose_name='来源模块')
    task_id = models.IntegerField(null=True, blank=True, verbose_name='任务ID')
    task_name = models.CharField(max_length=200, verbose_name='任务名称', help_text='相关任务的名称')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, verbose_name='通知类型')
    sender_name = models.CharField(max_length=100, verbose_name='发件人姓名')
    sender_email = models.EmailField(verbose_name='发件人邮箱', blank=True, null=True)
    recipient_info = models.JSONField(verbose_name='收件人信息', help_text='接收通知的用户信息')
    webhook_bot_info = models.JSONField(default=dict, blank=True, null=True, verbose_name='Webhook机器人信息')
    notification_content = models.TextField(verbose_name='通知内容', help_text='发送的通知内容')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='发送状态')
    error_message = models.TextField(blank=True, null=True, verbose_name='错误信息', help_text='发送失败时的错误信息')
    response_info = models.JSONField(default=dict, blank=True, null=True, verbose_name='响应信息', help_text='接收方返回的响应信息')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='发送时间')
    retry_count = models.IntegerField(default=0, verbose_name='重试次数', help_text='已重试的次数')
    is_retried = models.BooleanField(default=False, verbose_name='是否已重试')

    class Meta:
        db_table = 'notifications_log'
        verbose_name = '统一通知日志'
        verbose_name_plural = '统一通知日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"[{self.module}] {self.task_name} - {self.get_notification_type_display()} - {self.status}"

    def get_recipient_names(self):
        """获取收件人姓名列表"""
        if self.recipient_info:
            if isinstance(self.recipient_info, list):
                recipient_list = []
                for rec in self.recipient_info:
                    email = rec.get('email', '')
                    name = rec.get('name', '')
                    if name and email:
                        recipient_list.append(f"{name}（{email}）")
                    elif email:
                        recipient_list.append(email)
                    else:
                        recipient_list.append('未知用户')
                return ', '.join(recipient_list)
            elif isinstance(self.recipient_info, dict):
                email = self.recipient_info.get('email', '')
                name = self.recipient_info.get('name', '')
                if name and email:
                    return f"{name}（{email}）"
                elif email:
                    return email
                else:
                    return '未知用户'
        return "未知收件人"

    def get_retry_status(self):
        """获取重试状态"""
        if self.is_retried:
            return f"已重试 {self.retry_count} 次"
        return "未重试"
