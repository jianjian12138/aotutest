from apps.core_platform.views.base import BaseProjectViewSet
from apps.core_platform.permissions import TenantAwareViewSetMixin
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
                except Exception:
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



from .project_views import StandardPagination

class UiTestCaseModuleViewSet(BaseProjectViewSet):
    """UI测试用例模块视图集

    第六轮批次2：核查该历史遗留形式挂靠 —— 自定义 get_queryset 首行即
    super().get_queryset()，基类 BaseProjectViewSet 的项目归属校验实际已生效，
    未发现跨租户越权；本次改为显式声明自管 + 收口 _apply_tenant_scope。
    """
    tenant_scope_self_managed = True
    tenant_scope_self_managed_reason = (
        'get_queryset 以 super().get_queryset() 起步，完整继承 BaseProjectViewSet 的归属边界：'
        '携带 project_id 时校验该项目的 owner/members（传他人 project_id 返回空集），'
        '未携带时因 UiTestCaseModule 无 created_by 字段而直接 none()，两路均 fail-closed；'
        '其后仅追加 parent__isnull 层级筛选，不放宽任何可见性。'
        '模型有 project 外键但 UiProject 无 organization 字段，自动解析会命中 '
        'project__organization 导致 FieldError，故声明自管'
    )
    queryset = UiTestCaseModule.objects.all()
    serializer_class = UiTestCaseModuleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['order', 'created_at']
    ordering = ['order', 'created_at']
    filterset_fields = ['project', 'parent']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 处理在 schema build 或 request 缺失情况下的安全访问
        # （无 request 时不调 _apply_tenant_scope：该分支仅用于 schema 生成，不对外返回数据）
        if getattr(self, 'swagger_fake_view', False) or not hasattr(self, 'request') or not hasattr(self.request, 'query_params'):
            return queryset

        # 默认只返回顶级模块（如果没有显式请求特定父模块）
        parent_id = self.request.query_params.get('parent')
        get_all = self.request.query_params.get('get_all')
        if parent_id is None and not get_all:
            return self._apply_tenant_scope(queryset.filter(parent__isnull=True))
        return self._apply_tenant_scope(queryset)

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """获取模块树形结构，支持通过project过滤"""
        queryset = self.filter_queryset(self.get_queryset())
        # 对于树，我们只获取顶级节点（get_queryset中默认只返回顶级节点），
        # 序列化器 UiTestCaseModuleSerializer 会自动递归序列化 children。
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def batch_update_order(self, request):
        """批量更新模块排序（租户安全整改：仅允许操作归属当前用户可见项目的模块）"""
        user = request.user
        items = request.data.get('items', [])
        if not items:
            return Response({'error': '未提供排序数据'}, status=status.HTTP_400_BAD_REQUEST)

        updated_modules = []
        is_privileged = user.is_staff or user.is_superuser
        for index, item_id in enumerate(items):
            module = UiTestCaseModule.objects.filter(id=item_id).first()
            if module is None:
                continue
            proj = module.project
            is_owner = proj.owner_id == (user.id if user else None)
            is_member = user.is_authenticated and proj.members.filter(id=user.id).exists()
            if not (is_privileged or is_owner or is_member):
                continue
            module.order = index
            module.save()
            updated_modules.append(module)

        serializer = self.get_serializer(updated_modules, many=True)
        return Response(serializer.data)


class TestCaseViewSet(TenantAwareViewSetMixin, BaseProjectViewSet):
    """测试用例视图集"""
    queryset = TestCase.objects.all()
    # UiProject 无 organization 字段，租户锚点为项目负责人 owner
    org_field = 'project__owner'
    serializer_class = TestCaseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.
        OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'name', 'priority', 'status'
        ]
    ordering = ['-created_at']
    filterset_fields = ['project', 'module', 'status', 'priority', 'created_by']

    @action(detail=False, methods=['post'])
    def upload_record(self, request):
        """上传录制生成的代码"""
        code = request.data.get('code')
        project_id = request.data.get('project_id')
        name = request.data.get('name', '录制用例')
        if not code or not project_id:
            return Response({'error': 'Code and Project ID required'},
                status=400)
        try:
            steps = CaseGenerator.parse_playwright_code(code)
            # 先按租户校验项目归属，再在已校验的 project 上走关系访问创建用例
            project = self.scoped_get(UiProject, org_field='owner', id=
                project_id)
            test_case = project.test_cases.create(name=name, created_by=
                request.user, status='draft', description='由 Playwright 录制生成')
            for step in steps:
                TestCaseStep.objects.create(test_case=test_case,
                    step_number=step['step_order'], action_type=step[
                    'action_type'], description=step['description'],
                    action_type_id=None, input_value=step.get('input_value',
                    ''), assert_type=step.get('assert_type', ''),
                    assert_value=step.get('assert_value', ''), wait_time=1000)
            return Response({'status': 'success', 'case_id': test_case.id,
                'steps_count': len(steps)})
        except Exception as e:
            logger.error(f'Failed to process recorded code: {e}')
            return Response({'error': str(e)}, status=500)

    def _process_steps(self, instance, steps_data):
        """处理步骤数据，包括自动创建页面对象和元素"""
        if not steps_data:
            return
        page_name = 'Common_Page'
        page_object = None
        for step in steps_data:
            desc = step.get('description', '')
            if 'Navigate to URL:' in desc:
                try:
                    url = desc.split('Navigate to URL:')[-1].strip()
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    path = parsed.path
                    fragment = parsed.fragment
                    if fragment:
                        clean_fragment = fragment.lstrip('/')
                        if clean_fragment:
                            page_name = clean_fragment.replace('/', '_'
                                ).capitalize()
                    elif path and path != '/':
                        page_name = path.lstrip('/').replace('/', '_'
                            ).capitalize()
                    if len(page_name) > 50:
                        page_name = page_name[:50]
                except Exception:
                    pass
                break
        try:
            page_object, _ = PageObject.objects.get_or_create(project=
                instance.project, name=page_name, defaults={'class_name':
                f"{page_name.replace('_', '')}Page", 'description':
                f'Auto-generated page object for {page_name}', 'created_by':
                self.request.user})
            element_group, _ = ElementGroup.objects.get_or_create(project=
                instance.project, name=page_name, defaults={'description':
                f'Auto-generated group for {page_name}'})
        except Exception as e:
            logger.warning(f'自动创建页面对象/分组失败: {e}')
            element_group = None
        created_count = 0
        for i, step_data in enumerate(steps_data):
            if hasattr(step_data, 'dict'):
                step_data = step_data.dict()
            else:
                step_data = dict(step_data)
            step_data['test_case'] = instance.id
            step_data['step_number'] = i + 1
            temp_locator = step_data.get('temp_locator')
            if temp_locator and not step_data.get('element'
                ) and not step_data.get('element_id'):
                try:
                    strategy_name = step_data.get('temp_strategy', 'css')
                    if strategy_name not in ['css', 'xpath', 'name', 'id']:
                        strategy_name = 'css'
                    try:
                        strategy = LocatorStrategy.objects.get(name=
                            strategy_name)
                    except LocatorStrategy.DoesNotExist:
                        strategy = LocatorStrategy.objects.filter(name__iexact
                            =strategy_name).first()
                        if not strategy:
                            strategy = LocatorStrategy.objects.filter(name=
                                'css').first()
                    if strategy:
                        element = Element.objects.filter(project=instance.
                            project, locator_value=temp_locator,
                            locator_strategy=strategy).first()
                        if not element:
                            import time
                            base_name = 'Auto_Element'
                            desc = step_data.get('description', '')
                            if 'Click element:' in desc:
                                suffix = desc.split(':')[-1].strip().replace(
                                    '"', '').replace("'", '')
                                suffix = re.sub('[^\\w\\-_]', '_', suffix)
                                if suffix:
                                    base_name = f'Auto_{suffix[:30]}'
                            elif 'Fill element' in desc:
                                parts = desc.split(' with ')
                                if len(parts) > 0:
                                    suffix = parts[0].replace('Fill element',
                                        '').strip()
                                    suffix = re.sub('[^\\w\\-_]', '_', suffix)
                                    if suffix:
                                        base_name = f'Auto_{suffix[:30]}'
                            element_name = (
                                f'{base_name}_{int(time.time())}_{i}')
                            element = Element.objects.create(project=
                                instance.project, name=element_name,
                                element_type='BUTTON' if step_data.get(
                                'action_type') == 'click' else 'INPUT',
                                locator_strategy=strategy, locator_value=
                                temp_locator, created_by=self.request.user,
                                description=
                                'Automatically generated from script conversion'
                                , force_action=step_data.get('force_action',
                                False), page=page_name, group=element_group)
                        if page_object and element:
                            try:
                                if not element.group and element_group:
                                    element.group = element_group
                                    element.page = page_name
                                    element.save(update_fields=['group',
                                        'page'])
                                method_name = element.name.lower().replace(
                                    'auto_', '')
                                if not PageObjectElement.objects.filter(
                                    page_object=page_object, element=element
                                    ).exists():
                                    if PageObjectElement.objects.filter(
                                        page_object=page_object,
                                        method_name=method_name).exists():
                                        method_name = (
                                            f'{method_name}_{int(time.time())}')
                                    PageObjectElement.objects.create(
                                        page_object=page_object, element=
                                        element, method_name=method_name,
                                        is_property=True)
                            except Exception as e_po:
                                logger.warning(f'关联页面对象失败: {e_po}')
                        step_data['element'] = element.id
                except Exception as e:
                    logger.warning(f'自动创建元素失败: {str(e)}')
            if 'element_id' in step_data:
                step_data['element'] = step_data.pop('element_id')
            step_data.pop('id', None)
            step_data.pop('element_name', None)
            step_data.pop('element_locator', None)
            step_data.pop('created_at', None)
            step_data.pop('expanded', None)
            try:
                TestCaseStep.objects.filter(test_case=instance, step_number
                    =step_data.get('step_number', i + 1)).delete()
                TestCaseStep.objects.create(test_case=instance, step_number
                    =step_data.get('step_number', i + 1), action_type=
                    step_data.get('action_type', 'click'), element_id=
                    step_data.get('element') if step_data.get('element') else
                    None, input_value=step_data.get('input_value', ''),
                    wait_time=step_data.get('wait_time', 1000), assert_type
                    =step_data.get('assert_type', ''), assert_value=
                    step_data.get('assert_value', ''), description=
                    step_data.get('description', ''), enable_debug_capture=
                    step_data.get('enable_debug_capture', False))
                created_count += 1
            except Exception as e:
                logger.error(f'创建步骤 {i + 1} 失败: {str(e)}')
                logger.error(f'步骤数据: {step_data}')
                from rest_framework.exceptions import ValidationError
                raise ValidationError(f'步骤 {i + 1} 创建失败: {str(e)}')
        logger.info(f'成功创建了 {created_count} 个新步骤')

    @action(detail=True, methods=['post'])
    def copy_case(self, request, pk=None):
        """复制测试用例"""
        test_case = self.get_object()
        try:
            new_case = TestCase.objects.create(project=test_case.project,
                name=f'{test_case.name}_copy', description=test_case.
                description, priority=test_case.priority, status=test_case.
                status, created_by=request.user)
            steps = test_case.steps.all().order_by('step_number')
            new_steps = []
            for step in steps:
                new_steps.append(TestCaseStep(test_case=new_case,
                    step_number=step.step_number, action_type=step.
                    action_type, element=step.element, input_value=step.
                    input_value, wait_time=step.wait_time, assert_type=step
                    .assert_type, assert_value=step.assert_value,
                    description=step.description, enable_debug_capture=step
                    .enable_debug_capture))
            if new_steps:
                TestCaseStep.objects.bulk_create(new_steps)
            log_operation('create', 'test_case', new_case.id, new_case.name,
                request.user)
            serializer = self.get_serializer(new_case)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f'复制测试用例失败: {str(e)}')
            return Response({'error': f'复制失败: {str(e)}'}, status=status.
                HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_update(self, serializer):
        from django.db import transaction
        logger.info(f'收到更新请求: {self.request.data}')
        steps_data_raw = self.request.data.get('steps')
        logger.info(
            f'raw steps: {steps_data_raw}, type: {type(steps_data_raw)}')
        try:
            with transaction.atomic():
                instance = serializer.save()
                log_operation('edit', 'test_case', instance.id, instance.
                    name, self.request.user)
                steps_data = self.request.data.get('steps')
                logger.info(
                    f'更新测试用例 {instance.id} 的步骤数据: {len(steps_data) if steps_data else 0} 个步骤'
                    )
                if steps_data is not None:
                    existing_steps_count = instance.steps.count()
                    instance.steps.all().delete()
                    logger.info(f'删除了 {existing_steps_count} 个现有步骤')
                    self._process_steps(instance, steps_data)
        except Exception as e:
            logger.error(f'更新测试用例失败: {str(e)}')
            from rest_framework.exceptions import ValidationError
            raise ValidationError(f'更新失败: {str(e)}')

    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        """运行单个测试用例 - 支持选择Playwright或Selenium执行引擎"""
        test_case = self.get_object()
        try:
            engine_type = request.data.get('engine', 'playwright')
            execution = TestCaseExecution.objects.create(test_case=
                test_case, project=test_case.project, execution_source=
                'manual', status='running', engine=engine_type, browser=
                request.data.get('browser', 'chrome'), headless=request.
                data.get('headless', False), created_by=request.user,
                started_at=timezone.now())
            if engine_type == 'selenium':
                from ..selenium_engine import SeleniumTestEngine
                browser_type = request.data.get('browser', 'chrome')
                is_available, error_msg = (SeleniumTestEngine.
                    check_browser_available(browser_type))
                if not is_available:
                    logger.error(f'Selenium 浏览器检查失败: {error_msg}')
                    execution.status = 'failed'
                    execution.error_message = error_msg
                    execution.execution_logs = f"""浏览器检查失败

{error_msg}

建议：
1. 请确认已安装 {browser_type.capitalize()} 浏览器
2. 或者尝试使用其他浏览器（Chrome、Firefox、Edge）
3. 或者使用 Playwright 引擎（支持自动下载浏览器）"""
                    execution.finished_at = timezone.now()
                    execution.save()
                    return Response({'success': False, 'logs': execution.
                        execution_logs, 'screenshots': [], 'execution_time':
                        0, 'errors': [{'message':
                        f'{browser_type.capitalize()} 浏览器不可用', 'details':
                        error_msg, 'step_number': None, 'action_type':
                        '浏览器检查', 'element': '', 'description': '执行前浏览器环境检查'
                        }]}, status=status.HTTP_400_BAD_REQUEST)
            else:
                import asyncio
                import threading
                from ..playwright_engine import PlaywrightTestEngine
            start_time = time.time()
            test_steps = list(test_case.steps.all().order_by('step_number'))
            logger.info(f'执行测试用例 {test_case.id}: 找到 {len(test_steps)} 个步骤')
            steps_data = []
            for step in test_steps:
                step_data = {'step': step, 'action_type': step.action_type,
                    'description': step.description, 'input_value': step.
                    input_value, 'wait_time': step.wait_time, 'assert_type':
                    step.assert_type, 'assert_value': step.assert_value}
                if step.element:
                    step_data['element_data'] = {'locator_strategy': step.
                        element.locator_strategy.name if step.element.
                        locator_strategy else 'css', 'locator_value': step.
                        element.locator_value, 'name': step.element.name,
                        'wait_timeout': step.element.wait_timeout,
                        'force_action': step.element.force_action}
                else:
                    step_data['element_data'] = None
                steps_data.append(step_data)
            step_results = []
            execution_logs = []
            execution_logs.append(f"测试用例 '{test_case.name}' 开始执行")
            execution_logs.append(
                f"执行时间: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
            execution_logs.append(f'执行引擎: {engine_type.upper()}')
            device_id = request.data.get('device_id')
            device_info = None
            if device_id:
                try:
                    # UiDevice 模型无 organization/project/created_by 等租户字段，
                    # 无法解析归属路径，统一走 scoped_get 按 fail-closed 处理：
                    # 非管理员取不到设备时降级为“未找到”，不再允许按 ID 直取他人设备。
                    device = self.scoped_get(UiDevice, id=device_id)
                    device_info = f'{device.name} ({device.device_id})'
                except Exception as e:
                    execution_logs.append(f'⚠ 指定设备ID {device_id} 未找到: {str(e)}'
                        )
            if engine_type in ['airtest', 'appium']:
                if device_info:
                    execution_logs.append(f'执行设备: {device_info}')
                else:
                    execution_logs.append(f'执行设备: 自动连接')
            else:
                execution_logs.append(
                    f"浏览器: {request.data.get('browser', 'chrome').capitalize()}"
                    )
                headless_mode = request.data.get('headless', False)
                mode_text = '无头模式' if headless_mode else '有头模式'
                execution_logs.append(f'执行模式: {mode_text}')
            execution_logs.append(f'执行用户: {request.user.username}')
            if test_case.project.base_url and engine_type not in ['airtest',
                'appium']:
                execution_logs.append(f'项目基础URL: {test_case.project.base_url}')
            execution_logs.append('')
            screenshots = []
            detailed_errors = []
            execution_result = {'status': 'passed', 'error_message': None}
            if engine_type == 'appium':
                execution_logs.append('========== Appium引擎执行 ==========')
                if device_info:
                    execution_logs.append(f'使用设备: {device_info}')
                else:
                    execution_logs.append('⚠ 未指定设备，将尝试自动连接')
                execution_logs.append('✗ Appium引擎正在开发中，敬请期待')
                execution_logs.append('')
                execution_result['status'] = 'failed'
                execution_result['error_message'] = 'Appium引擎正在开发中，敬请期待'
                detailed_errors.append({'step_number': None, 'action_type':
                    '引擎选择', 'element': '', 'message': 'Appium引擎正在开发中',
                    'details': 'Appium引擎目前处于开发阶段，尚未完全实现', 'description':
                    '选择了Appium引擎'})
            elif engine_type == 'airtest':
                execution_logs.append('========== Airtest引擎执行 ==========')
                if device_info:
                    execution_logs.append(f'使用设备: {device_info}')
                else:
                    execution_logs.append('⚠ 未指定设备，将尝试自动连接')

                def run_airtest_test():
                    """使用Airtest执行测试"""
                    try:
                        from airtest.core.api import auto_setup, connect_device, touch, text, sleep, exists, Template
                        from airtest.core.error import AirtestError
                        execution_logs.append('========== 连接设备 ==========')
                        dev = None
                        if device_id:
                            try:
                                from ..models import UiDevice
                                # 同上：UiDevice 无租户字段，按 fail-closed 取用
                                db_device = self.scoped_get(UiDevice, id=
                                    device_id)
                                connect_str = (
                                    f'android:///{db_device.device_id}')
                                if db_device.platform == 'ios':
                                    connect_str = (
                                        f'ios:///{db_device.device_id}')
                                execution_logs.append(f'正在连接设备: {connect_str}')
                                dev = connect_device(connect_str)
                            except Exception as e:
                                execution_logs.append(f'✗ 指定设备连接失败: {str(e)}')
                                return False
                        if not dev:
                            try:
                                execution_logs.append('尝试自动连接本地Android设备...')
                                dev = connect_device('android:///')
                            except Exception as e:
                                execution_logs.append(f'✗ 自动连接设备失败: {str(e)}')
                                execution_result['status'] = 'failed'
                                execution_result['error_message'
                                    ] = f'无法连接到任何设备: {str(e)}'
                                return False
                        execution_logs.append(f'✓ 设备连接成功')
                        log_dir = os.path.join(settings.MEDIA_ROOT,
                            'airtest_logs', str(execution.id))
                        os.makedirs(log_dir, exist_ok=True)
                        auto_setup(__file__, logdir=log_dir)
                        try:
                            from airtest.core.android.android import Android
                            if isinstance(dev, Android):
                                execution_logs.append('尝试唤醒屏幕...')
                                try:
                                    dev.wake()
                                except Exception as wake_err:
                                    if 'decode' not in str(wake_err):
                                        logger.warning(f'唤醒屏幕失败: {wake_err}')
                        except Exception:
                            pass
                        if steps_data:
                            execution_logs.append(
                                '========== 执行测试步骤 ==========')
                            step_count = len(steps_data)
                            for i, step_info in enumerate(steps_data, 1):
                                execution_logs.append(
                                    f'========== 开始执行步骤 {i}/{step_count} =========='
                                    )
                                step_info['step']
                                action_type = step_info['action_type']
                                description = step_info['description']
                                element_data = step_info['element_data']
                                input_value = step_info['input_value']
                                wait_time = step_info['wait_time']
                                execution_logs.append(
                                    f'步骤 {i}: {description or action_type}')
                                try:
                                    if action_type == 'click':
                                        if element_data and element_data[
                                            'locator_strategy'] == 'IMAGE':
                                            img_path = os.path.join(settings.
                                                MEDIA_ROOT, element_data[
                                                'locator_value'])
                                            if os.path.exists(img_path):
                                                execution_logs.append(
                                                    f"  点击图片: {element_data['name']}")
                                                touch(Template(img_path))
                                            else:
                                                raise FileNotFoundError(
                                                    f'图片文件未找到: {img_path}')
                                        else:
                                            execution_logs.append(
                                                f"  ⚠ 暂不支持非图片的点击定位: {element_data.get('locator_strategy') if element_data else 'None'}"
                                                )
                                    elif action_type == 'fill':
                                        execution_logs.append(
                                            f'  输入文本: {input_value}')
                                        text(input_value)
                                    elif action_type == 'wait':
                                        wait_sec = wait_time / 1000.0
                                        execution_logs.append(f'  等待: {wait_sec}秒')
                                        sleep(wait_sec)
                                    execution_logs.append(f'  ✓ 步骤执行成功')
                                    step_results.append({'step_number': i,
                                        'action_type': action_type,
                                        'success': True})
                                except Exception as e:
                                    execution_logs.append(
                                        f'  ✗ 步骤执行失败: {str(e)}')
                                    execution_result['status'] = 'failed'
                                    execution_result['error_message'] = str(e)
                                    step_results.append({'step_number': i,
                                        'action_type': action_type,
                                        'success': False, 'error': str(e)})
                                    return False
                            execution_logs.append('========== 执行完成 ==========')
                            return True
                        else:
                            execution_logs.append('⚠ 没有测试步骤')
                            return True
                    except Exception as e:
                        execution_logs.append(f'✗ Airtest执行异常: {str(e)}')
                        execution_result['status'] = 'failed'
                        execution_result['error_message'] = str(e)
                        return False
                thread = threading.Thread(target=run_airtest_test)
                thread.start()
                thread.join()
            elif engine_type == 'selenium':

                def run_test_selenium():
                    """使用Selenium执行测试"""
                    browser_type = request.data.get('browser', 'chrome')
                    headless = request.data.get('headless', False)
                    device_name = request.data.get('device_name')
                    engine = SeleniumTestEngine(browser_type=browser_type,
                        headless=headless, device_name=device_name)
                    try:
                        execution_logs.append('========== 初始化浏览器 ==========')
                        try:
                            engine.start()
                            mode_text = '无头模式' if headless else '有头模式'
                            execution_logs.append(
                                f'✓ {browser_type.capitalize()} 浏览器启动成功 (Selenium, {mode_text})'
                                )
                            execution_logs.append('')
                        except Exception as browser_error:
                            execution_logs.append(
                                f'✗ {browser_type.capitalize()} 浏览器启动失败')
                            execution_logs.append(f'  错误: {str(browser_error)}'
                                )
                            execution_logs.append('')
                            execution_result['status'] = 'failed'
                            execution_result['error_message'] = (
                                f'{browser_type.capitalize()} 浏览器启动失败: {str(browser_error)}'
                                )
                            detailed_errors.append({'step_number': None,
                                'action_type': '浏览器启动', 'element': '',
                                'message':
                                f'{browser_type.capitalize()} 浏览器启动失败',
                                'details': str(browser_error),
                                'description': '执行前浏览器启动检查'})
                            return False
                        if test_case.project.base_url:
                            execution_logs.append(
                                '========== 导航到测试页面 ==========')
                            success, nav_log = engine.navigate(test_case.
                                project.base_url)
                            execution_logs.append(nav_log)
                            execution_logs.append('')
                            if not success:
                                execution_result['status'] = 'failed'
                                execution_result['error_message'] = '导航到测试页面失败'
                                return False
                        if steps_data:
                            execution_logs.append(
                                '========== 执行测试步骤 ==========')
                            step_count = len(steps_data)
                            execution_logs.append(f'共有 {step_count} 个步骤需要执行')
                            execution_logs.append('')
                            for i, step_info in enumerate(steps_data, 1):
                                execution_logs.append(
                                    f'========== 开始执行步骤 {i}/{step_count} =========='
                                    )
                                execution_logs.append(f'步骤 {i}/{step_count}:')
                                step = step_info['step']
                                action_type = step_info['action_type']
                                description = step_info['description']
                                element_data = step_info['element_data']
                                action_choices_dict = dict(TestCaseStep.
                                    ACTION_TYPE_CHOICES)
                                action_type_text = action_choices_dict.get(
                                    action_type, action_type)
                                execution_logs.append(
                                    f'  操作: {action_type_text}')
                                if description:
                                    execution_logs.append(
                                        f'  说明: {description}')
                                if element_data:
                                    execution_logs.append(
                                        f"  元素: {element_data['name']}")
                                    execution_logs.append(
                                        f"  定位器: {element_data['locator_strategy']}={element_data['locator_value']}"
                                        )
                                else:
                                    execution_logs.append(f'  (此步骤不需要元素)')
                                try:
                                    (success, step_log, screenshot_base64) = (
                                        engine.execute_step(step, 
                                        element_data or {}))
                                    execution_logs.append(f'  {step_log}')
                                    execution_logs.append('')
                                    step_results.append({'step_number': i,
                                        'action_type': action_type,
                                        'description': description or '',
                                        'success': success, 'error': None if
                                        success else step_log})
                                    if not success:
                                        logger.info(
                                            f'[调试-Selenium] 步骤 {i} 执行失败，设置状态为 failed'
                                            )
                                        execution_result['status'] = 'failed'
                                        element_info = element_data['name'
                                            ] if element_data else '未知元素'
                                        execution_result['error_message'
                                            ] = step_log
                                        logger.info(
                                            f'[调试-Selenium] execution_result = {execution_result}'
                                            )
                                        detailed_errors.append({'step_number':
                                            i, 'action_type': action_type_text,
                                            'element': element_info, 'message':
                                            f'步骤 {i}/{step_count} 执行失败',
                                            'details': step_log, 'description':
                                            description or ''})
                                        if not screenshot_base64:
                                            screenshot_base64 = (engine.
                                                capture_screenshot())
                                        if screenshot_base64:
                                            screenshots.append({'url':
                                                screenshot_base64, 'description':
                                                f'步骤 {i} 失败截图: {description or action_type_text}'
                                                , 'step_number': i, 'timestamp':
                                                timezone.now().isoformat()})
                                            execution_logs.append(f'  📸 失败截图已捕获')
                                        return False
                                    if (action_type == 'screenshot' and
                                        screenshot_base64):
                                        screenshots.append({'url':
                                            screenshot_base64, 'description':
                                            f"步骤 {i}: {description or '手动截图'}",
                                            'step_number': i, 'timestamp':
                                            timezone.now().isoformat()})
                                except Exception as e:
                                    execution_logs.append(
                                        f'  ✗ 步骤执行异常: {str(e)}')
                                    import traceback
                                    tb_str = traceback.format_exc()
                                    execution_logs.append(
                                        f'  [调试] 异常堆栈:\n{tb_str}')
                                    step_results.append({'step_number': i,
                                        'action_type': action_type,
                                        'description': description or '',
                                        'success': False, 'error': str(e)})
                                    execution_result['status'] = 'failed'
                                    execution_result['error_message'
                                        ] = f'步骤 {i} 执行异常: {str(e)}'
                                    element_info = element_data['name'
                                        ] if element_data else '未知元素'
                                    detailed_errors.append({'step_number':
                                        i, 'action_type': action_type_text,
                                        'element': element_info, 'message':
                                        f'步骤 {i}/{step_count} 执行异常',
                                        'details':
                                        f"""异常: {str(e)}

堆栈跟踪:
{tb_str}""",
                                        'description': description or ''})
                                    try:
                                        screenshot_base64 = (engine.
                                            capture_screenshot())
                                        if screenshot_base64:
                                            screenshots.append({'url':
                                                screenshot_base64, 'description':
                                                f'步骤 {i} 异常截图: {str(e)}',
                                                'step_number': i, 'timestamp':
                                                timezone.now().isoformat()})
                                    except Exception:
                                        pass
                                    return False
                            execution_logs.append(
                                f'========== 执行完成 ({step_count} 个步骤全部通过) =========='
                                )
                            return True
                        else:
                            execution_logs.append('警告: 测试用例没有定义任何步骤')
                            return True
                    finally:
                        execution_logs.append('')
                        execution_logs.append('========== 清理资源 ==========')
                        engine.stop()
                        execution_logs.append('✓ 浏览器已关闭')
                import threading
                test_thread = threading.Thread(target=run_test_selenium)
                test_thread.start()
                test_thread.join()
            elif engine_type == 'minium':

                def run_test_minium():
                    """使用Minium执行测试"""
                    try:
                        from ..minium_engine import MiniumTestEngine
                        project_path = getattr(test_case.project, 'minium_project_path', None)
                        engine = MiniumTestEngine(project_path=project_path)
                        execution_logs.append('========== 初始化微信开发者工具 ==========')
                        engine.start()
                        execution_logs.append('✓ Minium引擎启动成功')
                        execution_logs.append('')

                        if steps_data:
                            execution_logs.append('========== 执行测试步骤 ==========')
                            step_count = len(steps_data)
                            for i, step_info in enumerate(steps_data, 1):
                                execution_logs.append(f'========== 开始执行步骤 {i}/{step_count} ==========')
                                step = step_info['step']
                                action_type = step_info['action_type']
                                description = step_info['description']
                                element_data = step_info['element_data']

                                execution_logs.append(f'  操作: {action_type}')
                                if description:
                                    execution_logs.append(f'  说明: {description}')
                                    
                                try:
                                    if action_type == 'urlJump':
                                        success, step_log = engine.navigate(step.input_value)
                                        screenshot_base64 = None
                                    else:
                                        success, step_log, screenshot_base64 = engine.execute_step(step, element_data or {})
                                        
                                    execution_logs.append(f'  {step_log}')
                                    execution_logs.append('')
                                    step_results.append({
                                        'step_number': i,
                                        'action_type': action_type,
                                        'description': description or '',
                                        'success': success,
                                        'error': None if success else step_log
                                    })

                                    if not success:
                                        execution_result['status'] = 'failed'
                                        execution_result['error_message'] = step_log
                                        if not screenshot_base64:
                                            screenshot_base64 = engine.capture_screenshot()
                                        if screenshot_base64:
                                            screenshots.append({
                                                'url': screenshot_base64,
                                                'description': f'步骤 {i} 失败截图: {description or action_type}',
                                                'step_number': i,
                                                'timestamp': timezone.now().isoformat()
                                            })
                                        return False
                                        
                                    if action_type == 'screenshot' and screenshot_base64:
                                        screenshots.append({
                                            'url': screenshot_base64,
                                            'description': f"步骤 {i}: {description or '手动截图'}",
                                            'step_number': i,
                                            'timestamp': timezone.now().isoformat()
                                        })
                                        
                                except Exception as e:
                                    execution_logs.append(f'  ✗ 步骤执行异常: {str(e)}')
                                    step_results.append({
                                        'step_number': i,
                                        'action_type': action_type,
                                        'description': description or '',
                                        'success': False,
                                        'error': str(e)
                                    })
                                    execution_result['status'] = 'failed'
                                    execution_result['error_message'] = f'步骤 {i} 执行异常: {str(e)}'
                                    try:
                                        screenshot_base64 = engine.capture_screenshot()
                                        if screenshot_base64:
                                            screenshots.append({
                                                'url': screenshot_base64,
                                                'description': f'步骤 {i} 异常截图: {str(e)}',
                                                'step_number': i,
                                                'timestamp': timezone.now().isoformat()
                                            })
                                    except Exception:
                                        pass
                                    return False
                            execution_logs.append(f'========== 执行完成 ({step_count} 个步骤全部通过) ==========')
                            return True
                        else:
                            execution_logs.append('警告: 测试用例没有定义任何步骤')
                            return True
                    except Exception as e:
                        # 第六轮批次2：环境未就绪（minium/开发者工具缺失）不得伪装成执行结果，
                        # 打上标记由 API 层返回 501 Not Implemented
                        from ..minium_engine import MiniumNotAvailableError
                        if isinstance(e, MiniumNotAvailableError):
                            execution_logs.append(f'✗ 微信小程序测试能力未就绪: {str(e)}')
                            execution_result['status'] = 'failed'
                            execution_result['error_message'] = f'[CAPABILITY_UNAVAILABLE] {e}'
                            return False
                        execution_logs.append(f'✗ Minium执行异常: {str(e)}')
                        execution_result['status'] = 'failed'
                        execution_result['error_message'] = str(e)
                        return False
                    finally:
                        execution_logs.append('')
                        execution_logs.append('========== 清理资源 ==========')
                        engine.stop()

                import threading
                test_thread = threading.Thread(target=run_test_minium)
                test_thread.start()
                test_thread.join()
            else:

                def run_test_in_thread():
                    """在独立线程中运行异步测试"""

                    async def run_test():
                        """异步执行测试"""
                        browser_map = {'chrome': 'chrome', 'firefox':
                            'firefox', 'safari': 'webkit'}
                        browser_type = browser_map.get(request.data.get(
                            'browser', 'chrome'), 'chromium')
                        headless = request.data.get('headless', False)
                        environment_id = request.data.get('environment_id')
                        device_name = request.data.get('device_name')
                        engine = PlaywrightTestEngine(browser_type=
                            browser_type, headless=headless, environment_id=environment_id, device_name=device_name)
                        try:
                            execution_logs.append(
                                '========== 初始化浏览器 ==========')
                            await engine.start()
                            mode_text = '无头模式' if headless else '有头模式'
                            execution_logs.append(
                                f'✓ {browser_type.capitalize()} 浏览器启动成功 (Playwright, {mode_text})'
                                )
                            execution_logs.append('')
                            if test_case.project.base_url:
                                execution_logs.append(
                                    '========== 导航到测试页面 ==========')
                                success, nav_log = await engine.navigate(
                                    test_case.project.base_url)
                                execution_logs.append(nav_log)
                                execution_logs.append('')
                                if not success:
                                    execution_result['status'] = 'failed'
                                    execution_result['error_message'
                                        ] = '导航到测试页面失败'
                                    return False
                            if steps_data:
                                execution_logs.append(
                                    '========== 执行测试步骤 ==========')
                                step_count = len(steps_data)
                                execution_logs.append(
                                    f'共有 {step_count} 个步骤需要执行')
                                execution_logs.append('')
                                for i, step_info in enumerate(steps_data, 1):
                                    execution_logs.append(
                                        f'========== 开始执行步骤 {i}/{step_count} =========='
                                        )
                                    execution_logs.append(
                                        f'步骤 {i}/{step_count}:')
                                    step = step_info['step']
                                    action_type = step_info['action_type']
                                    description = step_info['description']
                                    element_data = step_info['element_data']
                                    action_choices_dict = dict(TestCaseStep
                                        .ACTION_TYPE_CHOICES)
                                    action_type_text = action_choices_dict.get(
                                        action_type, action_type)
                                    execution_logs.append(
                                        f'  操作: {action_type_text}')
                                    if description:
                                        execution_logs.append(
                                            f'  说明: {description}')
                                    if element_data:
                                        execution_logs.append(
                                            f"  元素: {element_data['name']}")
                                        execution_logs.append(
                                            f"  定位器: {element_data['locator_strategy']}={element_data['locator_value']}"
                                            )
                                    else:
                                        execution_logs.append(f'  (此步骤不需要元素)')
                                    try:
                                        execution_logs.append(f'  [调试] 准备执行步骤...')
                                        (success, step_log, screenshot_base64,
                                            debug_data) = (await engine.
                                            execute_step(step, element_data or
                                            {}, project_config=test_case.
                                            project.debug_config))
                                        execution_logs.append(
                                            f'  [调试] 步骤执行完成, success={success}')
                                        execution_logs.append(f'  {step_log}')
                                        execution_logs.append('')
                                        step_results.append({'step_number': i,
                                            'action_type': action_type,
                                            'description': description or '',
                                            'success': success, 'error': None if
                                            success else step_log, 'debug_data':
                                            debug_data})
                                        if not success:
                                            execution_logs.append(
                                                f'  [调试] 检测到步骤失败,准备处理...')
                                            execution_result['status'] = 'failed'
                                            element_info = element_data['name'
                                                ] if element_data else '未知元素'
                                            execution_result['error_message'
                                                ] = step_log
                                            detailed_errors.append({'step_number':
                                                i, 'action_type': action_type_text,
                                                'element': element_info, 'message':
                                                f'步骤 {i}/{step_count} 执行失败',
                                                'details': step_log, 'description':
                                                description or ''})
                                            if not screenshot_base64:
                                                screenshot_base64 = (await engine.
                                                    capture_screenshot())
                                        if screenshot_base64:
                                            screenshots.append({'url':
                                                screenshot_base64, 'description':
                                                f'步骤 {i} 失败截图: {description or action_type_text}'
                                                , 'step_number': i, 'timestamp':
                                                timezone.now().isoformat()})
                                            execution_logs.append(f'  📸 失败截图已捕获')
                                            execution_logs.append(
                                                f'  [调试] 步骤失败,准备退出执行...')
                                            return False
                                        if (action_type == 'screenshot' and
                                            screenshot_base64):
                                            screenshots.append({'url':
                                                screenshot_base64, 'description':
                                                f"步骤 {i}: {description or '手动截图'}",
                                                'step_number': i, 'timestamp':
                                                timezone.now().isoformat()})
                                        execution_logs.append(
                                            f'  [调试] 步骤 {i} 成功完成,准备执行下一步...')
                                    except Exception as e:
                                        execution_logs.append(
                                            f'  ✗ 步骤执行异常: {str(e)}')
                                        execution_logs.append(
                                            f'  [调试] 异常详情: {repr(e)}')
                                        import traceback
                                        tb_str = traceback.format_exc()
                                        execution_logs.append(
                                            f'  [调试] 异常堆栈:\n{tb_str}')
                                        step_results.append({'step_number': i,
                                            'action_type': action_type,
                                            'description': description or '',
                                            'success': False, 'error': str(e)})
                                        execution_result['status'] = 'failed'
                                        execution_result['error_message'
                                            ] = f'步骤 {i} 执行异常: {str(e)}'
                                        element_info = element_data['name'
                                            ] if element_data else '未知元素'
                                        detailed_errors.append({'step_number':
                                            i, 'action_type': action_type_text,
                                            'element': element_info, 'message':
                                            f'步骤 {i}/{step_count} 执行异常',
                                            'details':
                                            f"""异常: {str(e)}

堆栈跟踪:
{tb_str}""",
                                            'description': description or ''})
                                        try:
                                            screenshot_base64 = (await engine.
                                                capture_screenshot())
                                            if screenshot_base64:
                                                screenshots.append({'url':
                                                    screenshot_base64, 'description':
                                                    f'步骤 {i} 异常截图: {str(e)}',
                                                    'step_number': i, 'timestamp':
                                                    timezone.now().isoformat()})
                                        except Exception:
                                            pass
                                        execution_logs.append(
                                            f'  [调试] 发生异常,准备退出执行...')
                                        return False
                                execution_logs.append(
                                    f'========== 执行完成 ({step_count} 个步骤全部通过) =========='
                                    )
                                return True
                            else:
                                execution_logs.append('警告: 测试用例没有定义任何步骤')
                                return True
                        except Exception as e:
                            logger.error(f'Playwright执行异常: {str(e)}')
                            execution_logs.append(f'✗ 致命错误: {str(e)}')
                            import traceback
                            execution_logs.append(
                                f'  [调试] 异常堆栈:\n{traceback.format_exc()}')
                            execution_result['status'] = 'failed'
                            execution_result['error_message'
                                ] = f'引擎执行错误: {str(e)}'
                            return False
                        finally:
                            execution_logs.append('')
                            execution_logs.append('========== 清理资源 ==========')
                            await engine.stop()
                            execution_logs.append('✓ 浏览器已关闭')
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(run_test())
                    finally:
                        loop.close()
                import threading
                test_thread = threading.Thread(target=run_test_in_thread)
                test_thread.start()
                test_thread.join()
            total_time = round(time.time() - start_time, 2)
            execution_logs.append('')
            execution_logs.append('执行环境信息:')
            execution_logs.append(f'- 执行引擎: {engine_type.upper()}')
            if engine_type in ['airtest', 'appium']:
                if device_info:
                    execution_logs.append(f'- 执行设备: {device_info}')
                else:
                    execution_logs.append(f'- 执行设备: 自动连接/未知')
            else:
                execution_logs.append(
                    f"- 浏览器: {request.data.get('browser', 'chrome').capitalize()}"
                    )
                execution_logs.append(f'- 屏幕分辨率: 1920x1080')
            execution_logs.append(f'- 总执行时间: {total_time}秒')
            if screenshots:
                execution_logs.append(f'- 截图数量: {len(screenshots)} 张')
            logger.info(
                f"[调试] 准备保存执行结果: execution_result['status'] = {execution_result['status']}"
                )
            execution.status = execution_result['status']
            execution.error_message = execution_result['error_message'] or ''
            if step_results:
                execution.execution_logs = json.dumps(step_results,
                    ensure_ascii=False)
            else:
                execution.execution_logs = json.dumps([{'step_number': 0,
                    'action_type': 'system', 'description': '执行日志',
                    'success': True, 'error': '\n'.join(execution_logs),
                    'debug_data': None}], ensure_ascii=False)
            execution.execution_time = total_time
            execution.finished_at = timezone.now()
            execution.screenshots = screenshots
            execution.save()
            logger.info(f'[调试] 执行结果已保存: execution.status = {execution.status}')
            TestCaseExecutionSerializer(execution)
            errors = []
            if detailed_errors:
                for error in detailed_errors:
                    errors.append({'message': error['message'], 'details':
                        error['details'], 'step_number': error[
                        'step_number'], 'action_type': error['action_type'],
                        'element': error['element'], 'description': error[
                        'description']})
            elif execution.error_message:
                errors.append({'message': execution.error_message,
                    'details': ''})
            log_operation('run', 'test_case', test_case.id, test_case.name,
                request.user)
            # 第六轮批次2：执行能力未就绪时如实返回 501，不以"执行失败"含糊带过
            if (execution.error_message or '').startswith('[CAPABILITY_UNAVAILABLE]'):
                return Response({'success': False, 'capability_unavailable': True,
                    'logs': execution.execution_logs, 'screenshots': screenshots,
                    'execution_time': execution.execution_time, 'errors': errors,
                    'message': execution.error_message.replace(
                        '[CAPABILITY_UNAVAILABLE] ', '', 1)},
                    status=status.HTTP_501_NOT_IMPLEMENTED)
            return Response({'success': execution.status == 'passed',
                'logs': execution.execution_logs, 'screenshots':
                screenshots, 'execution_time': execution.execution_time,
                'errors': errors})
        except Exception as e:
            logger.error(f'执行测试用例失败: {str(e)}')
            import traceback
            traceback.print_exc()
            return Response({'success': False, 'logs':
                f'执行失败: {str(e)}\n\n{traceback.format_exc()}',
                'screenshots': [], 'execution_time': 0, 'errors': [{
                'message': str(e), 'stack': traceback.format_exc()}]},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def batch_run(self, request):
        """批量运行测试用例"""
        test_case_ids = request.data.get('test_case_ids', [])
        request.data.get('project_id')
        if not test_case_ids:
            return Response({'error': '请选择要运行的测试用例'}, status=status.
                HTTP_400_BAD_REQUEST)
        results = []
        for test_case_id in test_case_ids:
            try:
                test_case = TestCase.objects.get(id=test_case_id)
                results.append({'test_case_id': test_case_id,
                    'test_case_name': test_case.name, 'status': 'passed'})
            except TestCase.DoesNotExist:
                results.append({'test_case_id': test_case_id,
                    'test_case_name': '未知', 'status': 'error', 'error':
                    '测试用例不存在'})
        return Response({'results': results})

    def perform_destroy(self, instance):
        log_operation('delete', 'test_case', instance.id, instance.name,
            self.request.user)
        instance.delete()


class TestCaseStepViewSet(BaseProjectViewSet):
    """测试用例步骤视图集"""
    queryset = TestCaseStep.objects.all()
    serializer_class = TestCaseStepSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ['step_number']
    ordering = ['step_number']
    filterset_fields = ['test_case', 'action_type']


class TestCaseExecutionViewSet(BaseProjectViewSet):
    """测试用例执行记录视图集"""
    queryset = TestCaseExecution.objects.all().select_related('test_case',
        'project', 'test_suite', 'executed_by')
    serializer_class = TestCaseExecutionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.
        OrderingFilter]
    search_fields = ['test_case__name', 'error_message']
    ordering_fields = ['created_at', 'started_at', 'finished_at', 'status']
    ordering = ['-created_at']
    filterset_fields = ['project', 'test_suite', 'test_case', 'status',
        'execution_source']
    pagination_class = StandardPagination

    def perform_destroy(self, instance):
        name = (instance.test_case.name if instance.test_case else
            f'执行记录#{instance.id}')
        log_operation('delete', 'report', instance.id, name, self.request.user)
        instance.delete()

    @action(detail=False, methods=['post'], url_path='batch-delete')
    def batch_delete(self, request):
        """批量删除执行记录"""
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'error': '未提供要删除的记录ID'}, status=status.
                HTTP_400_BAD_REQUEST)
        queryset = self.get_queryset()
        deleted_count, _ = queryset.filter(id__in=ids).delete()
        return Response({'message': f'成功删除 {deleted_count} 条记录'})
