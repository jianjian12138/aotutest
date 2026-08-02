from apps.core_platform.views.base import BaseProjectViewSet
from apps.core_platform.permissions import TenantAwareViewSetMixin
from apps.notifications.models import NotificationConfig, NotificationLog
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db import models
from django.utils import timezone
from django.http import HttpResponse, FileResponse, Http404, HttpResponseNotFound
from django.views.static import serve
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import requests
import time
import os
import json
import logging
import uuid
import subprocess
from datetime import datetime, timedelta
from ..models import ApiProject, ApiCollection, ApiRequest, Environment, RequestHistory, TestSuite, TestExecution, TestSuiteRequest, ScheduledTask, TaskExecutionLog, TaskNotificationSetting, OperationLog, ApiImportTask, ApiTestCaseModule, ApiTestCase, ApiTestCaseStep, ApiTestCaseExecution, TestSuiteTestCase
from apps.core_platform.models import GlobalParameter
from ..import_utils import parse_openapi_spec
from ..serializers import ApiProjectSerializer, ApiCollectionSerializer, ApiRequestSerializer, ApiTestCaseModuleSerializer, ApiTestCaseSerializer, ApiTestCaseStepSerializer, ApiTestCaseExecutionSerializer, TestSuiteTestCaseSerializer, EnvironmentSerializer, RequestHistorySerializer, TestSuiteSerializer, TestSuiteRequestSerializer, TestExecutionSerializer, UserSerializer, ScheduledTaskSerializer, TaskExecutionLogSerializer, NotificationConfigSerializer, NotificationLogSerializer, TaskNotificationSettingSerializer, NotificationConfigDetailSerializer, NotificationLogDetailSerializer, TaskNotificationSettingDetailSerializer, OperationLogSerializer
logger = logging.getLogger(__name__)
from ..utils import execute_assertions, execute_test_case
from ..operation_logger import log_operation
User = get_user_model()
from rest_framework.pagination import PageNumberPagination
from .project_views import StandardPagination

class ScheduledTaskViewSet(BaseProjectViewSet):
    """定时任务视图集"""
    queryset = ScheduledTask.objects.all()
    serializer_class = ScheduledTaskSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'last_run_time']
    ordering = ['-created_at']

    @action(detail=True, methods=['post'])
    def run_now(self, request, pk=None):
        """立即执行定时任务"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info('=== run_now 方法被调用 ===')
        task = self.get_object()
        logger.info(f'获取任务对象: {task.id} - {task.name}')
        if not request.user.is_staff and task.created_by != request.user:
            logger.info('权限检查失败')
            return Response({'error': '无权执行此任务'}, status=status.
                HTTP_403_FORBIDDEN)
        try:
            execution_log = TaskExecutionLog.objects.create(task=task,
                status='PENDING', executed_by=request.user)
            logger.info(f'创建执行日志: {execution_log.id}')
            logger.info('调用 _execute_task_async 方法')
            self._execute_task_async(task, execution_log)
            logger.info('任务开始执行')
            return Response({'message': '任务已开始执行', 'execution_id':
                execution_log.id}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': f'执行任务失败: {str(e)}'}, status=status.
                HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """激活定时任务"""
        task = self.get_object()
        if task.status == 'ACTIVE':
            return Response({'error': '任务已经是激活状态'}, status=status.
                HTTP_400_BAD_REQUEST)
        task.status = 'ACTIVE'
        task.next_run_time = task.calculate_next_run()
        task.save()
        return Response({'message': '任务已激活', 'next_run_time': task.
            next_run_time}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """暂停定时任务"""
        task = self.get_object()
        if task.status == 'PAUSED':
            return Response({'error': '任务已经是暂停状态'}, status=status.
                HTTP_400_BAD_REQUEST)
        task.status = 'PAUSED'
        task.next_run_time = None
        task.save()
        return Response({'message': '任务已暂停'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def execution_logs(self, request, pk=None):
        """获取任务执行日志"""
        task = self.get_object()
        if not request.user.is_staff and task.created_by != request.user:
            return Response({'error': '无权查看此任务的执行日志'}, status=status.
                HTTP_403_FORBIDDEN)
        logs = TaskExecutionLog.objects.filter(task=task).order_by(
            '-created_at')
        page = self.paginate_queryset(logs)
        if page is not None:
            serializer = TaskExecutionLogSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = TaskExecutionLogSerializer(logs, many=True)
        return Response(serializer.data)

    def _execute_task_async(self, task, execution_log):
        """异步执行任务"""
        import threading
        import logging
        logger = logging.getLogger(__name__)
        logger.info('=== _execute_task_async 方法被调用 ===')

        def execute():
            try:
                execution_log.status = 'RUNNING'
                execution_log.start_time = timezone.now()
                execution_log.save()
                if task.task_type == 'TEST_SUITE':
                    result = self._execute_test_suite(task)
                elif task.task_type == 'API_REQUEST':
                    result = self._execute_api_request(task)
                else:
                    raise ValueError(f'未知的任务类型: {task.task_type}')
                execution_log.status = 'COMPLETED'
                execution_log.end_time = timezone.now()
                execution_log.result = result
                execution_log.save()
                task.update_run_stats(success=True)
                task.last_result = result
                task.save()
                logger.info('=== 开始检查发送成功通知 ===')
                notification_setting = None
                if hasattr(task, 'notification_settings'):
                    try:
                        notification_setting = (task.notification_settings.
                            first())
                        logger.info(f'获取到通知设置: {notification_setting}')
                        if notification_setting:
                            logger.info(
                                f'通知设置详情 - ID: {notification_setting.id}, 是否启用: {notification_setting.is_enabled}, 成功通知: {notification_setting.notify_on_success}'
                                )
                        else:
                            logger.info('没有找到通知设置')
                    except Exception as e:
                        logger.error(f'获取任务通知设置时出错: {e}')
                        import traceback
                        traceback.print_exc()
                else:
                    logger.info('任务没有notification_settings属性')
                if notification_setting and notification_setting.is_enabled:
                    logger.info('通知设置已启用，准备发送成功通知')
                    if notification_setting.notify_on_success:
                        logger.info('调用 _send_notification 方法发送成功通知')
                        self._send_notification(task, execution_log,
                            success=True)
                    else:
                        logger.info('通知设置中未启用成功通知')
                else:
                    logger.info('通知设置未启用或不存在，跳过成功通知')
                logger.info('=== 结束检查发送成功通知 ===')
            except Exception as e:
                execution_log.status = 'FAILED'
                execution_log.end_time = timezone.now()
                execution_log.error_message = str(e)
                execution_log.save()
                task.update_run_stats(success=False)
                task.error_message = str(e)
                task.save()
                logger.info('=== 开始检查发送失败通知 ===')
                notification_setting = None
                if hasattr(task, 'notification_settings'):
                    try:
                        notification_setting = (task.notification_settings.
                            first())
                        logger.info(f'获取到通知设置（失败情况）: {notification_setting}')
                        if notification_setting:
                            logger.info(
                                f'通知设置详情（失败情况） - ID: {notification_setting.id}, 是否启用: {notification_setting.is_enabled}, 失败通知: {notification_setting.notify_on_failure}'
                                )
                        else:
                            logger.info('没有找到通知设置（失败情况）')
                    except Exception as e:
                        logger.error(f'获取任务通知设置时出错（失败情况）: {e}')
                        import traceback
                        traceback.print_exc()
                else:
                    logger.info('任务没有notification_settings属性（失败情况）')
                if notification_setting and notification_setting.is_enabled:
                    logger.info('通知设置已启用，准备发送失败通知')
                    if notification_setting.notify_on_failure:
                        logger.info('调用 _send_notification 方法发送失败通知')
                        self._send_notification(task, execution_log,
                            success=False)
                    else:
                        logger.info('通知设置中未启用失败通知')
                else:
                    logger.info('通知设置未启用或不存在，跳过失败通知')
                logger.info('=== 结束检查发送失败通知 ===')
        thread = threading.Thread(target=execute)
        thread.daemon = True
        thread.start()

    def _execute_test_suite(self, task):
        """执行测试套件"""
        from ..utils import execute_test_suite
        result = execute_test_suite(task.test_suite, task.environment, task
            .created_by)
        return result

    def _execute_api_request(self, task):
        """执行API请求"""
        from ..utils import execute_api_request
        result = execute_api_request(task.api_request, task.environment,
            task.created_by)
        return result

    def _send_notification(self, task, execution_log, success=True):
        """发送通知邮件"""
        try:
            import logging
            logger = logging.getLogger(__name__)
            from django.core.mail import send_mail
            logger.info('=== _send_notification 方法被调用 ===')
            logger.info(f'任务ID: {task.id}, 任务名称: {task.name}, 执行状态: {success}')
            notification_setting = None
            if hasattr(task, 'notification_settings'):
                try:
                    notification_setting = task.notification_settings.first()
                    logger.info(f'获取到通知设置: {notification_setting}')
                except Exception as e:
                    logger.error(f'获取任务通知设置时出错: {e}')
                    import traceback
                    traceback.print_exc()
            if not notification_setting:
                logger.warning(f'任务 {task.id} 没有通知设置')
                return
            logger.info(
                f'通知设置详情 - ID: {notification_setting.id}, 是否启用: {notification_setting.is_enabled}'
                )
            if not notification_setting.is_enabled:
                logger.info(f'任务 {task.id} 的通知设置未启用')
                return
            execution_status = 'success' if success else 'failed'
            should_notify = notification_setting.should_notify(execution_status
                )
            logger.info(
                f'执行状态: {execution_status}, should_notify结果: {should_notify}')
            if not should_notify:
                logger.info(f'根据执行状态 {execution_status}，不应该发送通知')
                return
            logger.info('通过了通知条件检查')
            notification_config = notification_setting.get_notification_config(
                )
            has_config = notification_config is not None
            has_custom_bots = bool(notification_setting.custom_webhook_bots)
            has_custom_recipients = (notification_setting.custom_recipients
                .exists())
            has_task_emails = hasattr(task, 'notify_emails') and bool(task.
                notify_emails)
            if not (has_config or has_custom_bots or has_custom_recipients or
                has_task_emails):
                logger.warning('没有找到通知配置且无自定义设置（任务邮箱列表也为空）')
                return
            if notification_config:
                logger.info(f'找到了通知配置: {notification_config.name}')
            else:
                logger.info('使用自定义通知设置')
            logger.info(f'通知类型: {notification_setting.notification_type}')
            if notification_setting.notification_type in ['email', 'both']:
                logger.info('发送邮件通知')
                self._send_email_notification(task, execution_log,
                    notification_setting, notification_config, success)
            if notification_setting.notification_type in ['webhook', 'both']:
                logger.info('发送Webhook通知')
                self._send_webhook_notification(task, execution_log,
                    notification_setting, notification_config, success)
        except Exception as e:
            logger.error(f'发送通知失败: {str(e)}', exc_info=True)

    def _send_email_notification(self, task, execution_log,
        notification_setting, notification_config, success):
        """发送邮件通知"""
        try:
            import logging
            logger = logging.getLogger(__name__)
            from django.core.mail import send_mail
            logger.info('=== 开始发送邮件通知 ===')
            subject = f"定时任务执行{'成功' if success else '失败'}: {task.name}"
            summary_info = '无详细信息'
            if execution_log.result:
                result_data = execution_log.result
                summary_fields = {'success': result_data.get('success'),
                    'execution_id': result_data.get('execution_id'),
                    'passed_count': result_data.get('passed_count'),
                    'failed_count': result_data.get('failed_count'),
                    'total_count': result_data.get('total_count')}
                summary_info = '\n'.join([f'{k}: {v}' for k, v in
                    summary_fields.items() if v is not None])
            message = f"""
            任务名称: {task.name}
            执行状态: {'成功' if success else '失败'}
            执行时间: {execution_log.created_at.strftime('%Y-%m-%d %H:%M:%S')}
            任务类型: {'测试套件执行' if task.task_type == 'TEST_SUITE' else 'API请求执行'}

            执行概要:
            {summary_info}

            错误信息:
            {execution_log.error_message if execution_log.error_message else '无错误信息'}
            """
            recipients = []
            if notification_setting.custom_recipients.exists():
                recipients = [user.email for user in notification_setting.
                    custom_recipients.all() if user.email]
                logger.info(f'使用自定义收件人: {recipients}')
            if hasattr(task, 'notify_emails') and task.notify_emails:
                if isinstance(task.notify_emails, list):
                    recipients.extend(task.notify_emails)
                else:
                    recipients.append(task.notify_emails)
                logger.info(f'添加任务表单中的通知邮箱: {task.notify_emails}')
            recipients = list(set(recipients))
            logger.info(f'最终收件人列表: {recipients}')
            if not recipients:
                logger.warning('没有找到任何邮件收件人')
                return
            from_email = settings.DEFAULT_FROM_EMAIL
            logger.info(f'准备发送邮件，发件人: {from_email}, 收件人: {recipients}')
            send_mail(subject=subject, message=message, from_email=
                from_email, recipient_list=recipients, fail_silently=False)
            logger.info('邮件发送成功')
            NotificationLog.objects.create(task=task, task_name=task.name,
                notification_type='task_execution', sender_name='系统邮件通知',
                sender_email=from_email, recipient_info=[{'email': email} for
                email in recipients], notification_content=message, status=
                'success', sent_at=timezone.now())
        except Exception as e:
            logger.error(f'发送邮件通知失败: {str(e)}', exc_info=True)
            try:
                NotificationLog.objects.create(task=task, task_name=task.
                    name, notification_type='task_execution', sender_name=
                    '系统邮件通知', sender_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_info=[{'email': email} for email in
                    recipients] if 'recipients' in locals() else [],
                    notification_content=f'发送邮件通知失败: {str(e)}', status=
                    'failed', error_message=str(e))
            except Exception:
                pass

    def _send_webhook_notification(self, task, execution_log,
        notification_setting, notification_config, success):
        """发送Webhook通知"""
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.info('=== 开始发送Webhook通知 ===')
            all_webhook_bots = []
            if notification_config:
                bots = notification_config.get_webhook_bots()
                for bot in bots:
                    if bot.get('enabled', True):
                        all_webhook_bots.append(bot)
            if notification_setting.custom_webhook_bots:
                logger.info(
                    f'发现自定义Webhook机器人配置: {len(notification_setting.custom_webhook_bots)}个'
                    )
                for bot_type, bot_config in notification_setting.custom_webhook_bots.items(
                    ):
                    bot_data = {'type': bot_type, 'name': bot_config.get(
                        'name', f'自定义{bot_type}机器人'), 'webhook_url':
                        bot_config.get('webhook_url'), 'enabled':
                        bot_config.get('enabled', True)}
                    if bot_type == 'dingtalk' and bot_config.get('secret'):
                        bot_data['secret'] = bot_config.get('secret')
                    if bot_data.get('enabled', True) and bot_data.get(
                        'webhook_url'):
                        all_webhook_bots.append(bot_data)
            if not all_webhook_bots:
                logger.warning('没有找到任何启用的webhook机器人配置')
                return
            logger.info(f'总共找到 {len(all_webhook_bots)} 个待发送的webhook机器人')
            status_text = '成功' if success else '失败'
            'green' if success else 'red'
            for bot in all_webhook_bots:
                if not bot.get('enabled', True) or not bot.get('webhook_url'):
                    logger.info(f"跳过未启用或无URL的机器人: {bot.get('name', 'Unknown')}"
                        )
                    continue
                bot_type = bot.get('type', 'unknown')
                webhook_url = bot['webhook_url']
                logger.info(
                    f"发送通知到 {bot_type} 机器人: {bot.get('name', 'Unknown')}")
                if bot_type == 'wechat':
                    message_data = {'msgtype': 'markdown', 'markdown': {
                        'content':
                        f"""**定时任务执行{status_text}**

任务名称: {task.name}

执行状态: {status_text}

执行时间: {execution_log.created_at.strftime('%Y-%m-%d %H:%M:%S')}

任务类型: {'测试套件执行' if task.task_type == 'TEST_SUITE' else 'API请求执行'}"""
                        }}
                elif bot_type == 'feishu':
                    message_data = {'msg_type': 'interactive', 'card': {
                        'elements': [{'tag': 'div', 'text': {'content':
                        f"""**定时任务执行{status_text}**
任务名称: {task.name}
执行状态: {status_text}
执行时间: {execution_log.created_at.strftime('%Y-%m-%d %H:%M:%S')}
任务类型: {'测试套件执行' if task.task_type == 'TEST_SUITE' else 'API请求执行'}"""
                        , 'tag': 'lark_md'}}], 'header': {'title': {
                        'content': f'定时任务执行{status_text}', 'tag':
                        'plain_text'}, 'template': 'green' if success else
                        'red'}}}
                elif bot_type == 'dingtalk':
                    message_data = {'msgtype': 'markdown', 'markdown': {
                        'title': f'定时任务执行{status_text}', 'text':
                        f"""**定时任务执行{status_text}**

任务名称: {task.name}

执行状态: {status_text}

执行时间: {execution_log.created_at.strftime('%Y-%m-%d %H:%M:%S')}

任务类型: {'测试套件执行' if task.task_type == 'TEST_SUITE' else 'API请求执行'}"""
                        }}
                    secret = bot.get('secret')
                    if secret:
                        import hmac
                        import hashlib
                        import base64
                        import urllib.parse
                        timestamp = str(round(time.time() * 1000))
                        string_to_sign = f'{timestamp}\n{secret}'
                        string_to_sign_enc = string_to_sign.encode('utf-8')
                        secret_enc = secret.encode('utf-8')
                        hmac_code = hmac.new(secret_enc, string_to_sign_enc,
                            digestmod=hashlib.sha256).digest()
                        sign = urllib.parse.quote_plus(base64.b64encode(
                            hmac_code))
                        if '?' in webhook_url:
                            webhook_url += (
                                f'&timestamp={timestamp}&sign={sign}')
                        else:
                            webhook_url += (
                                f'?timestamp={timestamp}&sign={sign}')
                        logger.info(f'钉钉机器人签名验证 - 时间戳: {timestamp}')
                        logger.info(f'签名字符串: {string_to_sign}')
                        logger.info(f'生成的签名: {sign}')
                        logger.info(f'最终URL: {webhook_url}')
                    else:
                        logger.info('钉钉机器人未配置签名密钥，使用无签名模式')
                else:
                    message_data = {'text':
                        f"""定时任务执行{status_text}
任务名称: {task.name}
执行状态: {status_text}
执行时间: {execution_log.created_at.strftime('%Y-%m-%d %H:%M:%S')}
任务类型: {'测试套件执行' if task.task_type == 'TEST_SUITE' else 'API请求执行'}"""
                        }
                try:
                    response = requests.post(webhook_url, json=message_data,
                        headers={'Content-Type': 'application/json'},
                        timeout=10)
                    response.raise_for_status()
                    logger.info(
                        f'Webhook通知发送成功 - {bot_type}: {response.status_code}')
                    NotificationLog.objects.create(task=task, task_name=
                        task.name, notification_type='task_execution',
                        sender_name=f'系统Webhook通知-{bot_type}', sender_email
                        ='', recipient_info=[], webhook_bot_info={
                        'bot_type': bot_type, 'bot_name': bot.get('name',
                        'Unknown'), 'webhook_url': webhook_url[:50] + '...' if
                        len(webhook_url) > 50 else webhook_url},
                        notification_content=json.dumps(message_data,
                        ensure_ascii=False), status='success', sent_at=
                        timezone.now(), response_info={'status_code':
                        response.status_code, 'response_text': response.
                        text[:500]})
                except requests.exceptions.RequestException as e:
                    logger.error(f'Webhook通知发送失败 - {bot_type}: {str(e)}')
                    try:
                        NotificationLog.objects.create(task=task, task_name
                            =task.name, notification_type='task_execution',
                            sender_name=f'系统Webhook通知-{bot_type}',
                            sender_email='', recipient_info=[],
                            webhook_bot_info={'bot_type': bot_type,
                            'bot_name': bot.get('name', 'Unknown'),
                            'webhook_url': webhook_url[:50] + '...' if len(
                            webhook_url) > 50 else webhook_url},
                            notification_content=json.dumps(message_data,
                            ensure_ascii=False), status='failed',
                            error_message=str(e), sent_at=timezone.now())
                    except Exception:
                        pass
            logger.info('=== 结束发送Webhook通知 ===')
        except Exception as e:
            logger.error(f'发送Webhook通知失败: {str(e)}', exc_info=True)


class TaskExecutionLogViewSet(TenantAwareViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """任务执行日志视图集"""
    queryset = TaskExecutionLog.objects.all()
    serializer_class = TaskExecutionLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['task', 'status']
    ordering = ['-created_at']
    org_field = 'task__created_by'  # 第六轮批次2：等价于原手工过滤 task__created_by=user

    def get_queryset(self):
        # 第六轮批次2：接入统一租户隔离（org_field=task__created_by，仅看自己创建任务的执行日志）
        return self._apply_tenant_scope(
            TaskExecutionLog.objects.all()
        ).select_related('task', 'executed_by')


class NotificationConfigViewSet(BaseProjectViewSet):
    """通知配置视图集

    第六轮批次2：修复形式挂靠 —— 原 get_queryset 为
    Q(created_by=user) | Q(is_default=True)，其中 is_default 分支只按状态字段过滤、
    无任何归属校验，任一登录用户都能读到他人默认配置的 webhook_bots
    （含 webhook_url 与钉钉 secret），属真实跨租户密钥泄露。
    本模型承载密钥，按“宁可收紧”处置：收口到 _apply_tenant_scope（created_by 归属；
    管理员仍全量），不再放行他人的 is_default 配置。
    """
    queryset = NotificationConfig.objects.all()
    serializer_class = NotificationConfigSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['is_active', 'is_default', 'config_type']
    search_fields = ['name', 'sender_name', 'sender_email']
    ordering = ['-created_at']
    # NotificationConfig 无 organization/project 字段，租户锚点为创建者
    org_field = 'created_by'
    # 原实现对管理员同样只放行 created_by=user + is_default，若在此启用 staff 全量会
    # 让管理员新看到全平台配置的 webhook 密钥 —— 属可见性放宽，故关闭 staff 直通，
    # 保证改造后每一类用户的可见集合都是原集合的子集（与 UI 侧同名视图现有行为亦一致）。
    staff_has_full_access = False

    def get_queryset(self):
        queryset = NotificationConfig.objects.all()
        config_type = self.request.query_params.get('config_type', None)
        if config_type:
            queryset = queryset.filter(config_type=config_type)
        return self._apply_tenant_scope(queryset.distinct())

    @action(detail=True, methods=['post'], url_path='add-bot')
    def add_webhook_bot(self, request, pk=None):
        """添加Webhook机器人配置"""
        config = self.get_object()
        bot_type = request.data.get('bot_type')
        name = request.data.get('name')
        webhook_url = request.data.get('webhook_url')
        if not all([bot_type, name, webhook_url]):
            return Response({'error': '请提供完整的机器人信息'}, status=status.
                HTTP_400_BAD_REQUEST)
        webhook_bots = config.webhook_bots or {}
        webhook_bots[bot_type] = {'name': name, 'webhook_url': webhook_url,
            'enabled': True}
        config.webhook_bots = webhook_bots
        config.save()
        serializer = NotificationConfigDetailSerializer(config)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='remove-bot')
    def remove_webhook_bot(self, request, pk=None):
        """移除Webhook机器人配置"""
        config = self.get_object()
        bot_type = request.data.get('bot_type')
        if not bot_type:
            return Response({'error': '请提供机器人类型'}, status=status.
                HTTP_400_BAD_REQUEST)
        webhook_bots = config.webhook_bots or {}
        if bot_type in webhook_bots:
            del webhook_bots[bot_type]
            config.webhook_bots = webhook_bots
            config.save()
            return Response({'message': f'{bot_type}机器人已移除'})
        return Response({'error': '未找到该机器人配置'}, status=status.
            HTTP_404_NOT_FOUND)


class NotificationLogViewSet(TenantAwareViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """通知日志视图集"""
    queryset = NotificationLog.objects.all()
    serializer_class = NotificationLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'notification_type']
    ordering = ['-created_at']
    org_field = None  # 第六轮批次2：NotificationLog 仅含 task_id(int)，无租户外键；自定义 get_queryset 反查
    # 第六轮批次2：显式声明自管租户过滤，并在 return 分支收口 _apply_tenant_scope。
    tenant_scope_self_managed = True
    tenant_scope_self_managed_reason = (
        '已核实 NotificationLog.task_id 是裸 IntegerField（无外键，见 apps/notifications/models.py:77），'
        '模型无 organization / project / created_by 任一租户字段，自动解析必然 fail-closed 清零、'
        '让用户看不到自己任务的通知；写 task__xxx 多跳路径则直接 FieldError 500。'
        '故由 get_queryset 反查归属：先取 Q(owner=user)|Q(members=user) 的 ApiProject，'
        '再取其下 TestSuite / ApiCollection 关联的 ScheduledTask 以及 created_by=user 的任务，'
        '按 task_id__in 收敛，未命中即空集（fail-closed），边界不弱于组织级隔离'
    )

    def get_queryset(self):
        user = self.request.user
        # 第六轮批次2：接入统一租户隔离
        # NotificationLog 仅有 task_id(int) 与 module，无 task 外键；
        # 原 get_queryset 使用 task__test_suite__project 等路径会因模型无 task 关系而 FieldError。
        # 改为反查当前用户可访问的 ScheduledTask id 集合做租户收敛（fail-closed，无匹配则空集）。
        proj_ids = ApiProject.objects.filter(models.Q(owner=user) | models.Q(
            members=user)).values_list('id', flat=True)
        suite_ids = TestSuite.objects.filter(project_id__in=proj_ids
            ).values_list('id', flat=True)
        coll_ids = ApiCollection.objects.filter(project_id__in=proj_ids
            ).values_list('id', flat=True)
        task_ids = list(ScheduledTask.objects.filter(models.Q(
            test_suite_id__in=suite_ids) | models.Q(
            api_request__collection_id__in=coll_ids) | models.Q(
            created_by=user)).values_list('id', flat=True))
        return self._apply_tenant_scope(NotificationLog.objects.filter(
            task_id__in=task_ids).order_by('-created_at'))

    @action(detail=True, methods=['get'], url_path='detail')
    def get_notification_detail(self, request, pk=None):
        """获取通知详情"""
        notification = self.get_object()
        serializer = NotificationLogDetailSerializer(notification)
        return Response(serializer.data)


class TaskNotificationSettingViewSet(BaseProjectViewSet):
    """定时任务通知设置视图集"""
    queryset = TaskNotificationSetting.objects.all()
    serializer_class = TaskNotificationSettingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['task', 'is_enabled']
    ordering = ['-created_at']

    @action(detail=True, methods=['post'], url_path='update-settings')
    def update_notification_settings(self, request, pk=None):
        """更新通知设置"""
        setting = self.get_object()
        serializer = TaskNotificationSettingDetailSerializer(setting, data=
            request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


