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

class TestSuiteViewSet(TenantAwareViewSetMixin, BaseProjectViewSet):
    queryset = TestSuite.objects.all()
    # UiProject 无 organization 字段，租户锚点为项目负责人 owner
    org_field = 'project__owner'
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['project']
    search_fields = ['name', 'description']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return TestSuiteCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TestSuiteUpdateSerializer
        elif self.action == 'retrieve':
            return TestSuiteWithScriptsSerializer
        return TestSuiteSerializer

    def perform_destroy(self, instance):
        log_operation('delete', 'suite', instance.id, instance.name, self.
            request.user)
        instance.delete()

    @action(detail=True, methods=['get'])
    def scripts(self, request, pk=None):
        """获取测试套件中的所有脚本"""
        test_suite = self.get_object()
        scripts = test_suite.suite_scripts.all()
        serializer = TestSuiteScriptSerializer(scripts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_script(self, request, pk=None):
        """向测试套件添加脚本"""
        self.get_object()
        data = request.data
        data['test_suite'] = pk
        serializer = TestSuiteScriptSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'])
    def remove_script(self, request, pk=None, script_id=None):
        """从测试套件移除脚本"""
        test_suite = self.get_object()
        try:
            suite_script = TestSuiteScript.objects.get(test_suite=
                test_suite, id=script_id)
            suite_script.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except TestSuiteScript.DoesNotExist:
            return Response({'error': '脚本不存在于该测试套件中'}, status=status.
                HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['get'])
    def test_cases(self, request, pk=None):
        """获取测试套件中的所有测试用例"""
        test_suite = self.get_object()
        test_cases = test_suite.suite_test_cases.all()
        serializer = TestSuiteTestCaseSerializer(test_cases, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_test_case(self, request, pk=None):
        """向测试套件添加测试用例"""
        test_suite = self.get_object()
        test_case_id = request.data.get('test_case_id')
        order = request.data.get('order', 0)
        try:
            # 先校验待加入的用例属于当前租户，再在已校验的 test_suite 上走关系访问创建
            test_case = self.scoped_get(TestCase, org_field='project__owner',
                id=test_case_id)
            suite_test_case = test_suite.suite_test_cases.create(test_case=
                test_case, order=order)
            serializer = TestSuiteTestCaseSerializer(suite_test_case)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.
                HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'])
    def remove_test_case(self, request, pk=None):
        """从测试套件移除测试用例"""
        test_suite = self.get_object()
        test_case_id = request.data.get('test_case_id')
        try:
            from ..models import TestSuiteTestCase
            # test_suite 已由 get_object() 完成租户校验，经其关系访问定位关联记录
            suite_test_case = test_suite.suite_test_cases.get(test_case_id=
                test_case_id)
            suite_test_case.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except TestSuiteTestCase.DoesNotExist:
            return Response({'error': '测试用例不存在于该测试套件中'}, status=status.
                HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def update_test_case_order(self, request, pk=None):
        """更新测试套件中测试用例的顺序"""
        test_suite = self.get_object()
        test_case_orders = request.data.get('test_case_orders', [])
        try:
            from ..models import TestSuiteTestCase
            for item in test_case_orders:
                TestSuiteTestCase.objects.filter(test_suite=test_suite,
                    test_case_id=item['test_case_id']).update(order=item[
                    'order'])
            return Response({'message': '顺序更新成功'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.
                HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def run_suite(self, request, pk=None):
        """执行测试套件"""
        test_suite = self.get_object()
        test_case_count = test_suite.suite_test_cases.count()
        if test_case_count == 0:
            return Response({'error': '该测试套件未包含任何测试用例，无法执行'}, status=status
                .HTTP_400_BAD_REQUEST)
        engine = request.data.get('engine', 'playwright')
        browser = request.data.get('browser', 'chrome')
        headless = request.data.get('headless', False)
        environment_id = request.data.get('environment_id')
        test_suite.execution_status = 'running'
        test_suite.save()
        try:
            import threading
            from ..executor import TestExecutor

            def run_test():
                executor = TestExecutor(
                    test_suite=test_suite, 
                    engine=engine, 
                    browser=browser, 
                    headless=headless, 
                    executed_by=request.user,
                    environment_id=environment_id
                )
                executor.run()
            thread = threading.Thread(target=run_test)
            thread.daemon = True
            thread.start()
            log_operation('run', 'suite', test_suite.id, test_suite.name,
                request.user)
            return Response({'message': '测试套件开始执行', 'suite_id': test_suite.
                id, 'test_case_count': test_case_count, 'engine': engine,
                'browser': browser, 'headless': headless}, status=status.
                HTTP_200_OK)
        except Exception as e:
            test_suite.execution_status = 'failed'
            test_suite.save()
            return Response({'error': str(e)}, status=status.
                HTTP_500_INTERNAL_SERVER_ERROR)


class TestExecutionViewSet(BaseProjectViewSet):
    queryset = TestExecution.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['project', 'test_suite', 'test_script', 'status',
        'environment', 'executed_by']
    search_fields = ['error_message']
    ordering = ['-created_at']
    ordering = ['-created_at']
    pagination_class = StandardPagination

    def get_serializer_class(self):
        if self.action == 'create':
            return TestExecutionCreateSerializer
        return TestExecutionSerializer

    @action(detail=True, methods=['post'], url_path='generate-rca')
    def generate_rca(self, request, pk=None):
        """生成 AI 根因分析报告"""
        execution = self.get_object()
        
        execution.ai_rca_status = 'ANALYZING'
        execution.save(update_fields=['ai_rca_status'])
        
        import threading
        from apps.assistant.rca_service import RCAService
        threading.Thread(target=RCAService.analyze_ui_execution, args=(execution.id,)).start()
        
        return Response({'message': 'RCA 诊断任务已提交', 'status': 'ANALYZING'})

    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        """运行测试执行（真实执行能力本期未交付）"""
        self.get_object()
        return Response(
            {'error': '该能力本期未交付', 'status': 'not_implemented'},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )

    @action(detail=True, methods=['post'])
    def abort(self, request, pk=None):
        """中止测试执行"""
        execution = self.get_object()
        if execution.status == 'RUNNING':
            execution.status = 'ABORTED'
            execution.finished_at = timezone.now()
            execution.save()
            return Response(TestExecutionSerializer(execution).data)
        return Response({'error': '测试执行未在运行中'}, status=status.
            HTTP_400_BAD_REQUEST)

    def perform_destroy(self, instance):
        suite_name = (instance.test_suite.name if instance.test_suite else
            f'执行记录#{instance.id}')
        log_operation('delete', 'report', instance.id, suite_name, self.
            request.user)
        instance.delete()


class ScreenshotViewSet(BaseProjectViewSet):
    queryset = Screenshot.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = ScreenshotSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['execution']


class OperationRecordViewSet(TenantAwareViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """操作记录视图集（只读）"""
    queryset = OperationRecord.objects.all()
    serializer_class = OperationRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['operation_type', 'resource_type', 'user']
    org_field = 'user'  # 第六轮批次2：OperationRecord 仅含 user 外键，按操作者收敛

    def get_queryset(self):
        # 第六轮批次2：接入统一租户隔离 —— 操作记录按操作者收敛，非本人不可见（管理员全量）
        queryset = self._apply_tenant_scope(OperationRecord.objects.all()
            ).order_by('-created_at')
        limit = self.request.query_params.get('limit', None)
        if limit:
            try:
                limit = int(limit)
                queryset = queryset[:limit]
            except ValueError:
                pass
        return queryset


class UiDeviceViewSet(BaseProjectViewSet):
    queryset = UiDevice.objects.all()
    serializer_class = UiDeviceSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status', 'platform']
    search_fields = ['name', 'device_id']
    permission_classes = [IsAuthenticated]

    # 收尾批次：统一 RBAC 语义——平台不存在"超级读者"。
    # 此前 staff_has_full_access 继承自 BaseProjectViewSet(=True)，使 admin 在
    # _apply_tenant_scope 中可越权读取全部租户的设备；而 Project/ApiProject 已按
    # owner|members + created_by 严格 fail-closed。这里显式关闭 admin 全量可见，
    # 使 UiDevice 与 Project 保持一致的严格隔离：admin 也仅能读取其所属组织设备，
    # 无组织归属的 admin 与任何普通用户一样看不到他租户数据（get_queryset 与
    # @action 内的 scoped_queryset 均走同一 org 过滤，行为一致）。
    staff_has_full_access = False

    # 第六轮批次2 #157：UiDevice 现已具备 organization 字段，直接按组织收口，
    # 取代 BaseProjectViewSet 对无 project/created_by 模型的 fail-closed 空集。
    def get_queryset(self):
        return self._apply_tenant_scope(UiDevice.objects.all())

    def perform_create(self, serializer):
        org = getattr(self.request.user, 'organization', None)
        serializer.save(organization=org, created_by=self.request.user)

    def perform_destroy(self, instance):
        log_operation('delete', 'ui_device', instance.id, instance.name,
            self.request.user)
        instance.delete()

    @action(detail=False, methods=['get'])
    def refresh(self, request):
        """刷新设备列表"""
        from ..utils.device_manager import DeviceManager
        # 第六轮批次2 #157：设备归属到刷新操作发起人的组织，避免全局设备池越权
        org = getattr(request.user, 'organization', None)
        android_devices = DeviceManager.get_android_devices()
        ios_devices = DeviceManager.get_ios_devices()
        current_device_ids = set()
        for dev in (android_devices + ios_devices):
            device_id = dev['device_id']
            current_device_ids.add(device_id)
            device_type = dev.get('type', 'real')
            self.scoped_queryset(UiDevice, 'organization').update_or_create(
                device_id=device_id, defaults={
                    'name': dev['name'], 'platform': dev['platform'],
                    'type': device_type, 'status': dev['status'],
                    'version': dev['version'], 'last_online': timezone.now(),
                    'organization': org, 'created_by': request.user})
        # 仅将本组织（含未归属存量）离线设备置 offline，不越权操作他组织设备
        offline_qs = self.scoped_queryset(UiDevice, 'organization').exclude(
            device_id__in=current_device_ids)
        offline_qs.update(status='offline')
        return Response({'status': 'ok', 'count': len(current_device_ids)})

    @action(detail=False, methods=['post'])
    def connect_remote(self, request):
        """连接远程设备 (无需先创建记录)"""
        ip = request.data.get('ip')
        port = request.data.get('port', '5555')
        if not ip:
            return Response({'error': 'IP address required'}, status=400)
        # 严格校验 IP/端口格式：device_id 由 ip:port 拼装，
        # 不校验则可伪造任意 device_id 覆盖他人已注册设备记录
        from django.core.exceptions import ValidationError
        from django.core.validators import validate_ipv46_address
        try:
            validate_ipv46_address(str(ip))
            port = int(port)
            if not 1 <= port <= 65535:
                raise ValueError('port out of range')
        except (ValidationError, TypeError, ValueError):
            return Response({'error': 'Invalid IP or port'}, status=400)
        from ..utils.device_manager import DeviceManager
        success, msg = DeviceManager.connect_android_remote(ip, port)
        if success:
            # 第六轮批次2 #157：远程设备归属到操作发起人组织，禁止跨租户挂载
            org = getattr(request.user, 'organization', None)
            remote_key = f'{ip}:{port}'
            remote_name = f'Remote Android ({ip})'
            self.scoped_queryset(UiDevice, 'organization').update_or_create(
                device_id=remote_key,
                defaults={'name': remote_name, 'platform': 'android',
                'status': 'online', 'last_online': timezone.now(),
                'organization': org, 'created_by': request.user})
            return Response({'status': 'connected', 'msg': msg})
        else:
            return Response({'error': msg}, status=500)

    @action(detail=True, methods=['post'])
    def connect(self, request, pk=None):
        """连接设备 (Android Remote)"""
        device = self.get_object()
        if device.platform != 'android':
            return Response({'error':
                'Only Android supports remote connect'}, status=400)
        ip = request.data.get('ip')
        port = request.data.get('port', '5555')
        if not ip:
            return Response({'error': 'IP address required'}, status=400)
        from ..utils.device_manager import DeviceManager
        success, msg = DeviceManager.connect_android_remote(ip, port)
        if success:
            device.status = 'online'
            device.save()
            return Response({'status': 'connected', 'msg': msg})
        else:
            return Response({'error': msg}, status=500)

    @action(detail=True, methods=['post'])
    def disconnect(self, request, pk=None):
        """断开设备"""
        device = self.get_object()
        from ..utils.device_manager import DeviceManager
        success, msg = DeviceManager.disconnect_android(device.device_id)
        if success:
            device.status = 'offline'
            device.save()
            return Response({'status': 'disconnected', 'msg': msg})
        else:
            return Response({'error': msg}, status=500)

    @action(detail=True, methods=['get'])
    def screenshot(self, request, pk=None):
        """获取设备实时截图"""
        device = self.get_object()
        from ..utils.device_manager import DeviceManager
        if device.platform != 'android':
            return Response({'error': 'Not supported'}, status=400)
        image_data = DeviceManager.get_screenshot_bytes(device.device_id)
        if image_data:
            return HttpResponse(image_data, content_type='image/png')
        else:
            return Response({'error': 'Failed to capture screenshot'},
                status=500)


class ExecutionNodeViewSet(BaseProjectViewSet):
    """执行节点视图集"""
    queryset = ExecutionNode.objects.all()
    serializer_class = ExecutionNodeSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        # 节点注册/轮询必须认证，禁止匿名伪造执行节点
        if self.action in ['register', 'recorder_command']:
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(detail=False, methods=['post'])
    def register(self, request):
        """节点注册/心跳（须认证）"""
        name = request.data.get('name')
        token = request.data.get('token')
        ip_address = request.data.get('ip_address')
        node_type = request.data.get('node_type', 'execution')
        capabilities = request.data.get('capabilities', {})
        if not token or len(str(token).strip()) < 8:
            return Response({'error': 'Token required (>=8 chars)'}, status=400)
        if not name:
            return Response({'error': 'Name required'}, status=400)
        node, created = ExecutionNode.objects.update_or_create(
            token=str(token).strip(),
            defaults={'name': name, 'ip_address': ip_address, 'status': 'online',
                      'node_type': node_type, 'last_heartbeat': timezone.now(),
                      'capabilities': capabilities})
        return Response({'status': 'registered', 'node_id': node.id, 'name':
            node.name})

    @action(detail=False, methods=['get'])
    def recorder_command(self, request):
        """获取录制指令"""
        token = request.query_params.get('token')
        if not token:
            return Response({'error': 'Token required'}, status=400)
        return Response({'command': None})
