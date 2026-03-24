from apps.core_platform.views.base import BaseProjectViewSet
from apps.notifications.models import NotificationConfig, NotificationLog
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db import models
from django.utils import timezone
from django.conf import settings
import os
import logging
import json
import re
import random
import time
from ..models import UiProject, LocatorStrategy, Element, TestScript, TestSuite, TestSuiteScript, TestExecution, Screenshot, ElementGroup, PageObject, PageObjectElement, ScriptStep, ScriptElementUsage, TestCase, TestCaseStep, TestCaseExecution, OperationRecord, UiTestCaseModule, UiScheduledTask, UiTaskNotificationSetting, AICase, AIExecutionRecord, UiDevice, ExecutionNode
from ..serializers import UiProjectSerializer, UiProjectCreateSerializer, UiProjectUpdateSerializer, LocatorStrategySerializer, ElementSerializer, ElementEnhancedSerializer, TestScriptSerializer, TestScriptCreateSerializer, TestScriptUpdateSerializer, TestSuiteSerializer, TestSuiteCreateSerializer, TestSuiteUpdateSerializer, TestSuiteWithScriptsSerializer, TestSuiteScriptSerializer, TestSuiteTestCaseSerializer, TestExecutionSerializer, TestExecutionCreateSerializer, ScreenshotSerializer, ElementGroupSerializer, ElementGroupCreateSerializer, PageObjectSerializer, PageObjectCreateSerializer, PageObjectElementSerializer, ScriptStepSerializer, ScriptElementUsageSerializer, ScriptAnalysisSerializer, ElementValidationSerializer, CodeGenerationSerializer, TestCaseSerializer, TestCaseStepSerializer, TestCaseExecutionSerializer, TestCaseRunSerializer, OperationRecordSerializer, UiTestCaseModuleSerializer, UiScheduledTaskSerializer, NotificationConfigSerializer, NotificationLogSerializer, UiTaskNotificationSettingSerializer, AICaseSerializer, AIExecutionRecordSerializer, UiDeviceSerializer, ExecutionNodeSerializer
from ..operation_logger import log_operation
from ..services.case_generator import CaseGenerator
logger = logging.getLogger(__name__)
User = get_user_model()


def extract_step_info(s, step_index):
    """提取步骤信息的辅助函数，确保返回可读的步骤描述"""
    step_info = {'step': step_index}
    if hasattr(s, 'action'):
        action_data = s.action
        if isinstance(action_data, str):
            step_info['action'] = action_data
        elif hasattr(action_data, '__dict__'):
            attrs = {}
            for key in ['type', 'description', 'goal', 'coordinate', 'text',
                'output', 'result']:
                if hasattr(action_data, key):
                    value = getattr(action_data, key)
                    if isinstance(value, str):
                        attrs[key] = value
                    elif callable(value):
                        attrs[key] = getattr(value, '__name__', str(value))
                    else:
                        attrs[key] = str(value)
            if attrs:
                step_info['action'] = attrs
        else:
            step_info['action'] = str(action_data)
    elif hasattr(s, 'model_output'):
        output_data = s.model_output
        if isinstance(output_data, str):
            step_info['action'] = output_data
        elif hasattr(output_data, '__dict__'):
            attrs = {'type': 'model_output'}
            for key in ['action', 'description', 'goal', 'coordinate', 'text']:
                if hasattr(output_data, key):
                    value = getattr(output_data, key)
                    attrs[key] = str(value) if value else None
            step_info['action'] = attrs
        else:
            step_info['action'] = str(output_data)
    elif hasattr(s, '__dict__'):
        attrs = {}
        for key in dir(s):
            if not key.startswith('_'):
                try:
                    value = getattr(s, key)
                    if not callable(value):
                        attrs[key] = str(value)
                except:
                    pass
        if attrs:
            step_info['action'] = attrs
    elif callable(s):
        step_info['action'
            ] = f"<Action: {getattr(s, '__name__', 'unknown action')}>"
    else:
        step_info['action'] = str(s)
    return step_info


from rest_framework.pagination import PageNumberPagination




class AICaseViewSet(BaseProjectViewSet):
    queryset = AICase.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = AICaseSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.
        OrderingFilter]
    filterset_fields = ['project']
    search_fields = ['name', 'description', 'task_description']
    ordering = ['-created_at']

    @action(detail=False, methods=['post'], url_path='create_api_case')
    def create_api_case(self, request):
        """Special endpoint to create API AI Case and optionally generate structured test case"""
        project_id = request.data.get('project_id')
        name = request.data.get('name')
        task_description = request.data.get('task_description')
        save_as_case = request.data.get('save_as_case', False)
        from apps.api_testing.models import ApiProject, ApiTestCase, ApiTestCaseStep
        try:
            project = ApiProject.objects.get(id=project_id)
        except ApiProject.DoesNotExist:
            return Response({'error': 'API Project not found'}, status=
                status.HTTP_404_NOT_FOUND)
        if save_as_case:
            from apps.api_testing.ai_agent import generate_api_case_data_sync
            case_data_list = generate_api_case_data_sync(task_description)
            if not case_data_list:
                return Response({'error':
                    'Failed to generate API test case steps'}, status=
                    status.HTTP_500_INTERNAL_SERVER_ERROR)
            api_test_case = ApiTestCase.objects.create(project=project,
                name=name, description=task_description, status='ready',
                created_by=request.user)
            for i, step_data in enumerate(case_data_list):
                ApiTestCaseStep.objects.create(test_case=api_test_case,
                    step_number=i + 1, name=step_data.get('name',
                    f'Step {i + 1}'), description=step_data.get(
                    'description', ''), method=step_data.get('method',
                    'GET').upper(), url=step_data.get('url', ''), headers=
                    step_data.get('headers', {}), params=step_data.get(
                    'params', {}), body=step_data.get('body', {}),
                    assertions=step_data.get('assertions', []),
                    extract_rules=step_data.get('extract', []))
            return Response({'message':
                'API Test Case created successfully', 'id': api_test_case.id})
        return Response({'message': 'No action taken (save_as_case=False)'})

    def perform_destroy(self, instance):
        log_operation('delete', 'ai_case', instance.id, instance.name, self
            .request.user)
        instance.delete()

    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        """执行 AI 用例"""
        ai_case = self.get_object()
        execution_record = AIExecutionRecord.objects.create(project=ai_case
            .project, ai_case=ai_case, case_name=ai_case.name,
            task_description=ai_case.task_description, execution_mode=
            ai_case.execution_mode, status='running', executed_by=request.
            user, logs='正在分析任务...\n')
        import threading
        from asgiref.sync import sync_to_async

        def run_task():
            STOP_SIGNALS[execution_record.id] = False
            try:

                async def should_stop_async():
                    if STOP_SIGNALS.get(execution_record.id, False):
                        return True
                    await sync_to_async(execution_record.refresh_from_db)()
                    return execution_record.status == 'stopped'

                def should_stop():
                    return STOP_SIGNALS.get(execution_record.id, False)
                if ai_case.execution_mode == 'mobile':
                    from .ai_mobile import BasePhoneAgent
                    from ..models import UiDevice
                    import asyncio
                    device = UiDevice.objects.filter(status='online').first()
                    if not device:
                        execution_record.logs += '错误: 未找到在线的移动设备，无法执行移动端任务。\n'
                        execution_record.status = 'failed'
                        execution_record.save()
                        return
                    execution_record.logs += (
                        f'已选择设备: {device.name} ({device.device_id})\n')
                    execution_record.save()

                    async def run_mobile_async():
                        agent = await sync_to_async(BasePhoneAgent)(device_id
                            =device.device_id, case_name=ai_case.name)
                        agent.execution_record = execution_record

                        async def mobile_callback(data):
                            if data.get('type') == 'log':
                                content = data.get('content', '')
                                execution_record.logs += content + '\n'
                                await sync_to_async(execution_record.save)(
                                    update_fields=['logs'])
                        await agent.run_task(ai_case.task_description,
                            callback=mobile_callback, should_stop=
                            should_stop_async)
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(run_mobile_async())
                    finally:
                        loop.close()
                elif ai_case.execution_mode == 'vision_web':
                    from .ai_vision_web import VisionWebAgent
                    from playwright.async_api import async_playwright
                    import asyncio

                    async def run_vision_web_async():
                        async with async_playwright() as p:
                            browser = await p.chromium.launch(headless=False)
                            context = await browser.new_context(viewport={
                                'width': 1280, 'height': 720})
                            page = await context.new_page()
                            agent = VisionWebAgent(page, case_name=ai_case.name
                                )
                            agent.execution_record = execution_record

                            async def web_callback(data):
                                if data.get('type') == 'log':
                                    content = data.get('content', '')
                                    execution_record.logs += content + '\n'
                                    await sync_to_async(execution_record.save)(
                                        update_fields=['logs'])
                            await agent.run_task(ai_case.task_description,
                                callback=web_callback, should_stop=
                                should_stop_async)
                            await context.close()
                            await browser.close()
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(run_vision_web_async())
                    finally:
                        loop.close()
                else:
                    from .ai_agent import run_full_process_sync

                    async def on_analysis_complete(planned_tasks):
                        execution_record.planned_tasks = planned_tasks
                        execution_record.logs += '任务分析完成，开始执行...\n'
                        await sync_to_async(execution_record.save)()

                    async def on_step_update(step_info):
                        try:
                            if step_info.get('type') == 'log':
                                content = step_info.get('content')
                                if content:
                                    execution_record.logs += content
                                    await sync_to_async(execution_record.save)(
                                        )
                                return
                            task_id = step_info.get('task_id')
                            status = step_info.get('status')
                            if task_id and status:
                                updated = False
                                for task in execution_record.planned_tasks:
                                    if task['id'] == task_id:
                                        task['status'] = status
                                        updated = True
                                        break
                                if updated:
                                    await sync_to_async(execution_record.save)(
                                        )
                        except Exception as e:
                            print(f'更新步骤状态失败: {e}')
                    history = run_full_process_sync(ai_case.
                        task_description, analysis_callback=
                        on_analysis_complete, step_callback=on_step_update,
                        should_stop=should_stop)
                    if should_stop():
                        execution_record.status = 'stopped'
                        execution_record.logs += '\n[System] 任务已由用户停止。'
                    else:
                        execution_record.status = 'passed'
                        execution_record.logs += '\n执行完成。'
                        if execution_record.planned_tasks:
                            total_tasks = len(execution_record.planned_tasks)
                            completed_tasks = len([t for t in
                                execution_record.planned_tasks if t.get(
                                'status') == 'completed'])
                            pending_tasks = len([t for t in
                                execution_record.planned_tasks if t.get(
                                'status') == 'pending'])
                            logger.info(
                                f'🏁 Task completion summary: {completed_tasks}/{total_tasks} tasks completed, {pending_tasks} pending'
                                )
                    execution_record.end_time = timezone.now()
                    execution_record.duration = (execution_record.end_time -
                        execution_record.start_time).total_seconds()
                    steps = []
                    if history:
                        if hasattr(history, 'steps'):
                            steps = [extract_step_info(s, i) for i, s in
                                enumerate(history.steps)]
                    execution_record.steps_completed = steps
                    if execution_record.planned_tasks:
                        self._auto_mark_completed_tasks(execution_record)
                    self._process_gif_recording(execution_record, history)
                    execution_record.save()
            except Exception as e:
                execution_record.status = 'failed'
                execution_record.end_time = timezone.now()
                execution_record.duration = (execution_record.end_time -
                    execution_record.start_time).total_seconds()
                execution_record.logs += f'\n执行出错: {str(e)}'
                execution_record.save()
            finally:
                if execution_record.id in STOP_SIGNALS:
                    del STOP_SIGNALS[execution_record.id]
        thread = threading.Thread(target=run_task)
        thread.daemon = True
        thread.start()
        return Response({'message': 'AI 用例开始执行', 'execution_id':
            execution_record.id})


class AIExecutionRecordViewSet(BaseProjectViewSet):
    """AI执行记录视图集"""
    queryset = AIExecutionRecord.objects.all()
    serializer_class = AIExecutionRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['project', 'ai_case', 'status']
    ordering = ['-start_time']

    def perform_destroy(self, instance):
        name = (instance.case_name if instance.case_name else
            f'AI执行记录#{instance.id}')
        log_operation('delete', 'ai_execution', instance.id, name, self.
            request.user)
        instance.delete()

    @action(detail=False, methods=['post'])
    def batch_delete(self, request):
        """批量删除AI执行记录"""
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'error': '请选择要删除的记录'}, status=status.
                HTTP_400_BAD_REQUEST)
        queryset = self.get_queryset()
        deleted_count, _ = queryset.filter(id__in=ids).delete()
        return Response({'message': f'成功删除 {deleted_count} 条记录'})

    @action(detail=False, methods=['post'], url_path='run_adhoc')
    def run_adhoc(self, request):
        """执行临时 AI 任务"""
        project_id = request.data.get('project_id')
        task_description = request.data.get('task_description')
        execution_mode = request.data.get('execution_mode', 'text')
        enable_gif = request.data.get('enable_gif', True)
        device_id = request.data.get('device_id')
        model_config_id = request.data.get('model_config_id')
        browser_type = request.data.get('browser_type', 'chrome')
        reference_image = request.FILES.get('reference_image')
        logger.info(
            f'Run Adhoc Task: execution_mode={execution_mode}, device_id={device_id}, model_config_id={model_config_id}, browser_type={browser_type}, task={task_description[:50]}...'
            )
        if not project_id or not task_description:
            return Response({'error': '缺少必要参数'}, status=status.
                HTTP_400_BAD_REQUEST)
        if reference_image:
            try:
                import os
                import time
                from django.conf import settings
                from django.core.files.storage import default_storage
                from django.core.files.base import ContentFile
                temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp',
                    'reference_images')
                os.makedirs(temp_dir, exist_ok=True)
                filename = (
                    f'ref_{request.user.id}_{int(time.time())}_{reference_image.name}'
                    )
                file_path = default_storage.save(
                    f'temp/reference_images/{filename}', ContentFile(
                    reference_image.read()))
                media_url = getattr(settings, 'MEDIA_URL', '/media/')
                full_url = f'{media_url}{file_path}'
                task_description += (
                    f'\n\n[System Note] User uploaded a reference image: {full_url}'
                    )
            except Exception as e:
                logger.error(f'Failed to save reference image: {e}')
        try:
            project = UiProject.objects.get(id=project_id)
        except UiProject.DoesNotExist:
            return Response({'error': '项目不存在'}, status=status.
                HTTP_404_NOT_FOUND)
        execution_record = AIExecutionRecord.objects.create(project=project,
            case_name='Adhoc Task', task_description=task_description,
            execution_mode=execution_mode, status='running', executed_by=
            request.user, logs=
            f"""正在分析任务... (Mode: {execution_mode}, Device: {device_id})
""")
        import threading
        from asgiref.sync import sync_to_async
        from .ai_agent import run_full_process_sync

        def run_task():
            STOP_SIGNALS[execution_record.id] = False
            try:

                async def should_stop_async():
                    if STOP_SIGNALS.get(execution_record.id, False):
                        return True
                    await sync_to_async(execution_record.refresh_from_db)()
                    return execution_record.status == 'stopped'

                def should_stop_sync():
                    if STOP_SIGNALS.get(execution_record.id, False):
                        return True
                    execution_record.refresh_from_db()
                    return execution_record.status == 'stopped'
                if execution_mode == 'mobile':
                    if not device_id:
                        raise ValueError('Mobile mode requires device_id')
                    from .ai_mobile import BasePhoneAgent
                    import asyncio

                    async def run_mobile_async():
                        agent = await sync_to_async(BasePhoneAgent)(device_id
                            =device_id, case_name=
                            f'Mobile Task {execution_record.id}',
                            model_config_id=model_config_id)
                        agent.execution_record = execution_record

                        async def mobile_callback(data):
                            if data.get('type') == 'log':
                                content = data.get('content', '')
                                execution_record.logs += content + '\n'
                                await sync_to_async(execution_record.save)(
                                    update_fields=['logs'])
                        await agent.run_task(task_description, callback=
                            mobile_callback, should_stop=should_stop_async)
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(run_mobile_async())
                    finally:
                        loop.close()
                elif execution_mode == 'api':
                    from apps.api_testing.ai_agent import run_api_task_sync

                    async def on_analysis_complete(planned_tasks):
                        execution_record.planned_tasks = planned_tasks
                        execution_record.logs += '任务分析完成，开始执行...\n'
                        await sync_to_async(execution_record.save)()

                    async def on_step_update(step_info):
                        try:
                            if step_info.get('type') == 'log':
                                content = step_info.get('content')
                                if content:
                                    execution_record.logs += content
                                    await sync_to_async(execution_record.save)(
                                        update_fields=['logs'])
                                return
                            task_id = step_info.get('task_id')
                            status = step_info.get('status')
                            if task_id and status:
                                updated = False
                                if execution_record.planned_tasks:
                                    for task in execution_record.planned_tasks:
                                        if str(task['id']) == str(task_id):
                                            task['status'] = status
                                            updated = True
                                            break
                                if updated:
                                    await sync_to_async(execution_record.save)(
                                        update_fields=['planned_tasks'])
                        except Exception as e:
                            logger.error(f'更新步骤状态失败: {e}', exc_info=True)
                    run_api_task_sync(task_description, analysis_callback=
                        on_analysis_complete, step_callback=on_step_update,
                        should_stop=should_stop_async, model_config_id=
                        model_config_id)
                else:
                    from .ai_agent import run_full_process_sync

                    async def on_analysis_complete(planned_tasks):
                        execution_record.planned_tasks = planned_tasks
                        execution_record.logs += '任务分析完成，开始执行...\n'
                        await sync_to_async(execution_record.save)()

                    async def on_step_update(step_info):
                        try:
                            if step_info.get('type') == 'log':
                                content = step_info.get('content')
                                if content:
                                    execution_record.logs += content
                                    await sync_to_async(execution_record.save)(
                                        update_fields=['logs'])
                                return
                            task_id = step_info.get('task_id')
                            status = step_info.get('status')
                            logger.info(
                                f'DEBUG: on_step_update received: task_id={task_id}, status={status}'
                                )
                            if task_id and status:
                                updated = False
                                if execution_record.planned_tasks:
                                    for task in execution_record.planned_tasks:
                                        if str(task['id']) == str(task_id):
                                            old_status = task.get('status', 'pending')
                                            task['status'] = status
                                            updated = True
                                            logger.info(
                                                f'DEBUG: Updated task {task_id} from {old_status} to {status}'
                                                )
                                            break
                                if updated:
                                    await sync_to_async(execution_record.save)(
                                        update_fields=['planned_tasks'])
                                else:
                                    logger.warning(
                                        f'DEBUG: Task ID {task_id} not found in planned_tasks: {execution_record.planned_tasks}'
                                        )
                        except Exception as e:
                            logger.error(f'更新步骤状态失败: {e}', exc_info=True)
                    history = run_full_process_sync(task_description,
                        analysis_callback=on_analysis_complete,
                        step_callback=on_step_update, should_stop=
                        should_stop_async, execution_mode=execution_mode,
                        enable_gif=enable_gif, case_name=task_description[:
                        50] if task_description else 'Adhoc Task',
                        model_config_id=model_config_id, browser_type=
                        browser_type)
                    steps = []
                    if history:
                        if hasattr(history, 'steps'):
                            steps = [extract_step_info(s, i) for i, s in
                                enumerate(history.steps)]
                    execution_record.steps_completed = steps
                    if execution_record.planned_tasks:
                        self._auto_mark_completed_tasks(execution_record)
                    self._process_gif_recording(execution_record, history)
                if should_stop_sync():
                    execution_record.status = 'stopped'
                    execution_record.logs += '\n[System] 任务已由用户停止。'
                else:
                    if execution_mode != 'mobile':
                        execution_record.status = 'passed'
                        execution_record.logs += '\n执行完成。'
                    if execution_record.planned_tasks:
                        total_tasks = len(execution_record.planned_tasks)
                        completed_tasks = len([t for t in execution_record.
                            planned_tasks if t.get('status') == 'completed'])
                        pending_tasks = len([t for t in execution_record.
                            planned_tasks if t.get('status') == 'pending'])
                        logger.info(
                            f'🏁 Task completion summary: {completed_tasks}/{total_tasks} tasks completed, {pending_tasks} pending'
                            )
                execution_record.end_time = timezone.now()
                execution_record.duration = (execution_record.end_time -
                    execution_record.start_time).total_seconds()
                execution_record.save()
            except Exception as e:
                execution_record.status = 'failed'
                execution_record.end_time = timezone.now()
                execution_record.duration = (execution_record.end_time -
                    execution_record.start_time).total_seconds()
                execution_record.logs += f'\n执行出错: {str(e)}'
                execution_record.save()
            finally:
                if execution_record.id in STOP_SIGNALS:
                    del STOP_SIGNALS[execution_record.id]
        thread = threading.Thread(target=run_task)
        thread.daemon = True
        thread.start()
        return Response({'message': 'AI 任务开始执行', 'execution_id':
            execution_record.id})

    @action(detail=True, methods=['post'], url_path='stop')
    def stop_task(self, request, pk=None):
        """停止正在执行的任务"""
        try:
            execution_id = int(pk)
            if execution_id in STOP_SIGNALS:
                STOP_SIGNALS[execution_id] = True
                return Response({'message': '已发送停止信号'})
            else:
                record = self.get_object()
                if record.status == 'running':
                    record.status = 'stopped'
                    record.end_time = timezone.now()
                    record.logs += '\n[System] 任务被强制标记为停止（未在运行队列中找到）。'
                    record.save()
                    return Response({'message': '任务已标记为停止'})
                return Response({'message': '任务不在运行中'}, status=status.
                    HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.
                HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='run_agent_browser')
    def run_agent_browser(self, request):
        """流式运行 Agent Browser"""
        from django.http import StreamingHttpResponse
        import queue
        import threading
        import json
        from apps.core_platform.models import UiProject
        from django.utils import timezone
        
        url = request.data.get('url')
        task_description = request.data.get('task_description')
        model_config_id = request.data.get('model_config_id')
        enable_planning = request.data.get('enable_planning', True)
        enable_script_gen = request.data.get('enable_script_gen', True)
        enable_visual_diff = request.data.get('enable_visual_diff', False)
        browser_type = request.data.get('browser_type', 'chrome')
        
        if not url or not task_description:
            return Response({'error': 'URL and task_description are required'}, status=status.HTTP_400_BAD_REQUEST)
            
        full_instruction = f"URL: {url}\nTask: {task_description}"
        project = UiProject.objects.first()
        
        execution_record = AIExecutionRecord.objects.create(
            project=project,
            case_name='Agent Browser Task',
            task_description=full_instruction,
            execution_mode='vision_web',
            status='running',
            executed_by=request.user,
            logs="Web Agent started via Server-Sent Events..."
        )
        
        q = queue.Queue()
        
        async def analysis_callback(planned_tasks):
            steps = [t.get('description', '') for t in planned_tasks]
            q.put({"type": "planning", "steps": steps})
            
        async def step_callback(step_info):
            q.put(step_info)
            
        def should_stop_sync():
            return False
            
        async def should_stop_async():
            return False
            
        def run_agent_thread():
            import asyncio
            from .ai_agent import run_full_process_sync
            try:
                res = run_full_process_sync(
                    task_description=full_instruction,
                    analysis_callback=analysis_callback,
                    step_callback=step_callback,
                    should_stop=should_stop_async,
                    execution_mode='vision_web',
                    enable_gif=False,
                    case_name=f"AgentBrowser_{execution_record.id}",
                    model_config_id=model_config_id,
                    browser_type=browser_type
                )
                
                script_content = ""
                if enable_script_gen:
                    from .ai_agent import generate_script_content_sync
                    q.put({"type": "log", "content": "Generating Playwright script..."})
                    script_content = generate_script_content_sync(full_instruction, mode='web', model_config_id=model_config_id)
                
                q.put({
                    "type": "completed", 
                    "status": "passed", 
                    "steps_count": len(res.steps) if hasattr(res, 'steps') else 0,
                    "script": script_content
                })
                execution_record.status = 'passed'
            except Exception as e:
                import traceback
                traceback.print_exc()
                q.put({"type": "error", "content": str(e)})
                execution_record.status = 'failed'
                execution_record.logs += f"\nError: {e}"
            finally:
                q.put({"type": "stream_end"})
                execution_record.end_time = timezone.now()
                execution_record.duration = (execution_record.end_time - execution_record.start_time).total_seconds()
                execution_record.save()
                
        threading.Thread(target=run_agent_thread, daemon=True).start()
        
        def event_stream():
            while True:
                msg = q.get()
                if msg.get("type") == "stream_end":
                    break
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                
        return StreamingHttpResponse(event_stream(), content_type='text/event-stream')

    @action(detail=False, methods=['post'], url_path='generate_e2e_script')
    def generate_e2e_script(self, request):
        url = request.data.get('url')
        task_description = request.data.get('task_description')
        model_config_id = request.data.get('model_config_id')
        
        if not url or not task_description:
            return Response({'error': 'URL and task_description required'}, status=status.HTTP_400_BAD_REQUEST)
            
        full_instruction = f"URL: {url}\nTask: {task_description}"
        from .ai_agent import generate_script_content_sync
        try:
            script_content = generate_script_content_sync(full_instruction, mode='web', model_config_id=model_config_id)
            return Response({"script": script_content, "steps": []})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='inspect_page')
    def inspect_page(self, request):
        mode = 'url'
        url = request.data.get('url')
        device_id = request.data.get('device_id')
        model_config_id = request.data.get('model_config_id')
        
        if 'image' in request.FILES:
            mode = 'image'
        elif device_id:
            mode = 'device'
            
        import asyncio
        import base64
        
        # In Django views, run synchronous code using loop.run_until_complete
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            from .ai_vision_web import VisionWebAgent
            
            if mode == 'url':
                if not url:
                    return Response({'error': 'URL required'}, status=status.HTTP_400_BAD_REQUEST)
                from playwright.async_api import async_playwright
                
                async def run_url_inspect():
                    async with async_playwright() as p:
                        browser = await p.chromium.launch(headless=True)
                        context = await browser.new_context()
                        page = await context.new_page()
                        agent = VisionWebAgent(page, model_config_id=model_config_id)
                        res = await agent.inspect_page(url)
                        await browser.close()
                        return res
                result = loop.run_until_complete(run_url_inspect())
                return Response(result)
                
            elif mode == 'image':
                img_file = request.FILES['image']
                img_bytes = img_file.read()
                
                async def run_img_inspect():
                    agent = VisionWebAgent(None, model_config_id=model_config_id)
                    return await agent.inspect_image(img_bytes)
                    
                result = loop.run_until_complete(run_img_inspect())
                return Response(result)
                
            elif mode == 'device':
                from .ai_mobile import BasePhoneAgent
                
                async def run_dev_inspect():
                    phone_agent = BasePhoneAgent(device_id, model_config_id=model_config_id)
                    b64 = await phone_agent._get_screenshot_base64()
                    if not b64:
                        raise Exception("Failed to get device screenshot")
                    agent = VisionWebAgent(None, model_config_id=model_config_id)
                    return await agent.inspect_image(base64.b64decode(b64))
                    
                result = loop.run_until_complete(run_dev_inspect())
                return Response(result)
                
        except Exception as e:
            logger.error(f"Inspect error: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            try:
                loop.close()
            except:
                pass

    def _process_gif_recording(self, execution_record, history):
        """
        处理GIF录制文件
        在执行完成后查找生成的GIF文件并保存路径到数据库
        """
        try:
            import os
            from django.conf import settings
            from datetime import datetime
            default_gif_path = os.path.join(os.getcwd(), 'agent_history.gif')
            if os.path.exists(default_gif_path):
                import shutil
                gif_dir = os.path.join(settings.MEDIA_ROOT, 'ai_recording')
                os.makedirs(gif_dir, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                safe_case_name = ''.join([(c if c.isalnum() or c in (' ',
                    '_', '-') else '_') for c in execution_record.case_name])
                new_gif_filename = f'{safe_case_name}_{timestamp}.gif'
                new_gif_path = os.path.join(gif_dir, new_gif_filename)
                shutil.move(default_gif_path, new_gif_path)
                relative_path = os.path.join('media', 'ai_recording',
                    new_gif_filename)
                execution_record.gif_path = relative_path
                logger.info(f'✅ GIF recording saved to: {relative_path}')
            else:
                logger.warning(f'⚠️ GIF file not found at: {default_gif_path}')
        except Exception as e:
            logger.warning(f'⚠️ Failed to process GIF recording: {e}')

    def _auto_mark_completed_tasks(self, execution_record):
        """
        自动标记已完成的任务
        通过分析执行历史和当前任务状态，自动标记那些已经执行但未被标记完成的任务
        """
        try:
            initial_completed = 0
            initial_pending = 0
            if execution_record.planned_tasks:
                initial_completed = len([t for t in execution_record.
                    planned_tasks if t.get('status') == 'completed'])
                initial_pending = len([t for t in execution_record.
                    planned_tasks if t.get('status') == 'pending'])
                logger.info(
                    f'📊 Before auto-mark: {initial_completed} completed, {initial_pending} pending tasks'
                    )
            if (execution_record.status == 'passed' and execution_record.
                planned_tasks):
                auto_marked_count = 0
                for task in execution_record.planned_tasks:
                    if task.get('status') == 'pending':
                        task['status'] = 'completed'
                        auto_marked_count += 1
                        logger.info(
                            f"🔒 Auto-marked task {task['id']} as completed")
                if auto_marked_count > 0:
                    logger.info(
                        f'✨ Auto-marked {auto_marked_count} tasks as completed'
                        )
                else:
                    logger.info('📋 No pending tasks needed auto-marking')
        except Exception as e:
            logger.warning(f'⚠️ Failed to auto-mark completed tasks: {e}')

    @action(detail=True, methods=['get'], url_path='report')
    def generate_report(self, request, pk=None):
        """
        生成AI执行报告

        Query Parameters:
            report_type: 报告类型 (summary/detailed/performance)，默认为 summary

        Returns:
            执行报告数据
        """
        try:
            record = self.get_object()
            report_type = request.query_params.get('report_type', 'summary')
            from .reports import AIExecutionReportGenerator
            generator = AIExecutionReportGenerator(record)
            if report_type == 'detailed':
                report = generator.generate_detailed_report()
            elif report_type == 'performance':
                report = generator.generate_performance_report()
            else:
                report = generator.generate_summary_report()
            return Response({'success': True, 'data': report, 'report_type':
                report_type})
        except Exception as e:
            logger.error(f'生成AI执行报告失败: {e}', exc_info=True)
            return Response({'success': False, 'error': str(e)}, status=
                status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='export-pdf')
    def export_pdf(self, request, pk=None):
        """
        导出AI执行报告为PDF

        Query Parameters:
            report_type: 报告类型 (summary/detailed/performance)，默认为 summary

        Returns:
            PDF文件下载
        """
        try:
            record = self.get_object()
            report_type = request.query_params.get('report_type', 'summary')
            from .reports import AIExecutionReportGenerator
            from .pdf_generator import AIReportPDFGenerator
            generator = AIExecutionReportGenerator(record)
            if report_type == 'detailed':
                report_data = generator.generate_detailed_report()
            elif report_type == 'performance':
                report_data = generator.generate_performance_report()
            else:
                report_data = generator.generate_summary_report()
            pdf_generator = AIReportPDFGenerator(report_data, report_type)
            pdf_buffer = pdf_generator.generate()
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            safe_case_name = ''.join([(c if c.isalnum() or c in (' ', '_',
                '-') else '_') for c in record.case_name])
            filename = f'AI_Report_{safe_case_name}_{timestamp}.pdf'
            response = HttpResponse(pdf_buffer.getvalue(), content_type=
                'application/pdf')
            response['Content-Disposition'
                ] = f'attachment; filename="{filename}"'
            response['Content-Length'] = len(pdf_buffer.getvalue())
            return response
        except ImportError as e:
            logger.error(f'PDF生成库未安装: {e}')
            return Response({'success': False, 'error':
                'PDF生成功能需要安装 reportlab 库，请运行: pip install reportlab'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f'导出PDF失败: {e}', exc_info=True)
            return Response({'success': False, 'error': str(e)}, status=
                status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='inspect_page')
    def inspect_page(self, request):
        """Smart Inspector: Analyze page (URL or Image or ADB Device) and extract elements"""
        url = request.data.get('url')
        image = request.FILES.get('image')
        device_id = request.data.get('device_id')
        if not url and not image and not device_id:
            return Response({'error':
                'URL, Image file or Device ID is required'}, status=status.
                HTTP_400_BAD_REQUEST)
        from .ai_vision_web import VisionWebAgent
        from playwright.async_api import async_playwright
        import asyncio
        from .utils.device_manager import DeviceManager
        from apps.requirement_analysis.models import AIModelConfig
        import os
        config_obj = AIModelConfig.objects.filter(role='writer', is_active=True
            ).first()
        api_key = config_obj.api_key if config_obj else os.getenv(
            'OPENAI_API_KEY', '')
        base_url = config_obj.base_url if config_obj else os.getenv(
            'OPENAI_BASE_URL', 'https://api.openai.com/v1')
        model_name = config_obj.model_name if config_obj else 'gpt-4o'
        if device_id:
            try:
                screenshot_bytes = DeviceManager.get_screenshot_bytes(device_id
                    )
                if not screenshot_bytes:
                    return Response({'error':
                        'Failed to capture device screenshot'}, status=
                        status.HTTP_500_INTERNAL_SERVER_ERROR)

                def run_device_inspection_sync(api_key=api_key, base_url=
                    base_url, model_name=model_name, screenshot_bytes=
                    screenshot_bytes):
                    import asyncio
                    import threading
                    from queue import Queue
                    result_queue = Queue()

                    def worker():
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                        async def _async_task():
                            agent = VisionWebAgent(page=None, case_name=
                                f'Smart Inspection (Device {device_id})',
                                api_key=api_key, base_url=base_url,
                                model_name=model_name)
                            return await agent.inspect_image(screenshot_bytes)
                        try:
                            res = loop.run_until_complete(_async_task())
                            result_queue.put(res)
                        except Exception as e:
                            result_queue.put(e)
                        finally:
                            loop.close()
                    t = threading.Thread(target=worker)
                    t.start()
                    t.join()
                    res = result_queue.get()
                    if isinstance(res, Exception):
                        raise res
                    return res
                result = run_device_inspection_sync()
                return Response(result)
            except Exception as e:
                logger.error(f'Device inspection failed: {e}')
                return Response({'error': str(e)}, status=status.
                    HTTP_500_INTERNAL_SERVER_ERROR)
        if image:
            try:
                image_bytes = image.read()

                def run_image_inspection_sync(api_key=api_key, base_url=
                    base_url, model_name=model_name, image_bytes=image_bytes):
                    import asyncio
                    import threading
                    from queue import Queue
                    result_queue = Queue()

                    def worker():
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                        async def _async_task():
                            agent = VisionWebAgent(page=None, case_name=
                                'Smart Inspection (Image)', api_key=api_key,
                                base_url=base_url, model_name=model_name)
                            return await agent.inspect_image(image_bytes)
                        try:
                            res = loop.run_until_complete(_async_task())
                            result_queue.put(res)
                        except Exception as e:
                            result_queue.put(e)
                        finally:
                            loop.close()
                    t = threading.Thread(target=worker)
                    t.start()
                    t.join()
                    res = result_queue.get()
                    if isinstance(res, Exception):
                        raise res
                    return res
                result = run_image_inspection_sync()
                return Response(result)
            except Exception as e:
                logger.error(f'Image inspection failed: {e}')
                return Response({'error': str(e)}, status=status.
                    HTTP_500_INTERNAL_SERVER_ERROR)

        def run_inspection_sync(api_key=api_key, base_url=base_url,
            model_name=model_name, url=url):
            """
            Synchronous wrapper that runs Playwright in a fresh thread with its own event loop.
            This completely avoids Django's async/sync context issues.
            """
            import asyncio
            import threading
            from queue import Queue
            result_queue = Queue()

            def worker():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                async def _async_task():
                    async with async_playwright() as p:
                        try:
                            browser = await p.chromium.launch(headless=True,
                                channel='chrome')
                        except Exception:
                            try:
                                browser = await p.chromium.launch(headless=True
                                    )
                            except Exception as e:
                                logger.warning(
                                    f'Chromium launch failed: {e}, trying msedge'
                                    )
                                browser = await p.chromium.launch(headless=
                                    True, channel='msedge')
                        context = await browser.new_context(viewport={
                            'width': 1280, 'height': 720})
                        page = await context.new_page()
                        agent = VisionWebAgent(page, case_name=
                            'Smart Inspection', api_key=api_key, base_url=
                            base_url, model_name=model_name)
                        return await agent.inspect_page(url)
                try:
                    res = loop.run_until_complete(_async_task())
                    result_queue.put(res)
                except Exception as e:
                    result_queue.put(e)
                finally:
                    loop.close()
            t = threading.Thread(target=worker)
            t.start()
            t.join()
            res = result_queue.get()
            if isinstance(res, Exception):
                raise res
            return res
        try:
            result = run_inspection_sync()
            return Response(result)
        except Exception as e:
            logger.error(f'Inspection failed: {e}')
            return Response({'error': str(e)}, status=status.
                HTTP_500_INTERNAL_SERVER_ERROR)
