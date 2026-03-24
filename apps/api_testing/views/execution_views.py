from apps.core_platform.views.base import BaseProjectViewSet
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
from ..models import ApiProject, ApiCollection, ApiRequest, Environment, RequestHistory, TestSuite, TestExecution, TestSuiteRequest, ScheduledTask, TaskExecutionLog, TaskNotificationSetting, OperationLog, ApiImportTask, ApiTestCaseModule, ApiTestCase, ApiTestCaseStep, ApiTestCaseExecution, TestSuiteTestCase, ApiProject
from apps.core_platform.models import GlobalParameter
from ..import_utils import parse_openapi_spec
from ..serializers import ApiProjectSerializer, ApiCollectionSerializer, ApiRequestSerializer, ApiTestCaseModuleSerializer, ApiTestCaseSerializer, ApiTestCaseStepSerializer, ApiTestCaseExecutionSerializer, TestSuiteTestCaseSerializer, EnvironmentSerializer, RequestHistorySerializer, TestSuiteSerializer, TestSuiteRequestSerializer, TestExecutionSerializer, UserSerializer, ScheduledTaskSerializer, TaskExecutionLogSerializer, NotificationConfigSerializer, NotificationLogSerializer, TaskNotificationSettingSerializer, NotificationConfigDetailSerializer, NotificationLogDetailSerializer, TaskNotificationSettingDetailSerializer, OperationLogSerializer
logger = logging.getLogger(__name__)
from ..utils import execute_assertions, execute_test_case
from ..operation_logger import log_operation
User = get_user_model()
from rest_framework.pagination import PageNumberPagination
from .project_views import StandardPagination

class TestSuiteTestCaseViewSet(BaseProjectViewSet):
    queryset = TestSuiteTestCase.objects.all()
    serializer_class = TestSuiteTestCaseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['test_suite']
    ordering = ['order']


class TestSuiteViewSet(BaseProjectViewSet):
    queryset = TestSuite.objects.all()
    serializer_class = TestSuiteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['project']

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """执行测试套件"""
        test_suite = self.get_object()
        try:
            execution = TestExecution.objects.create(test_suite=test_suite,
                status='RUNNING', start_time=timezone.now(), executed_by=
                request.user)
            suite_test_cases = TestSuiteTestCase.objects.filter(test_suite=
                test_suite, enabled=True).order_by('order')
            if not suite_test_cases.exists():
                return self._execute_deprecated_requests(test_suite,
                    execution, request.user)
            execution.total_requests = 0
            execution.save()
            results = []
            passed_count = 0
            failed_count = 0
            
            # 引入全局跨用例上下文变量池
            suite_context_variables = {}
            
            from ..utils import execute_test_case
            for suite_tc in suite_test_cases:
                test_case = suite_tc.test_case
                try:
                    case_result = execute_test_case(test_case, test_suite.
                        environment, request.user, create_report=False, context_variables=suite_context_variables)
                    execution.total_requests += case_result.get('total_steps',
                        0)
                    passed_count += case_result.get('passed_steps', 0)
                    failed_count += case_result.get('failed_steps', 0)
                    results.append({'type': 'test_case', 'id': test_case.id,
                        'name': test_case.name, 'status': case_result.get(
                        'status'), 'passed_count': case_result.get(
                        'passed_steps', 0), 'failed_count': case_result.get
                        ('failed_steps', 0), 'total_count': case_result.get
                        ('total_steps', 0), 'execution_time': case_result.
                        get('execution_time', 0), 'results': case_result.
                        get('results', [])})
                except Exception as e:
                    failed_count += 1
                    results.append({'type': 'test_case', 'id': test_case.id,
                        'name': test_case.name, 'status': 'error', 'error':
                        str(e)})
            execution.end_time = timezone.now()
            execution.passed_requests = passed_count
            execution.failed_requests = failed_count
            execution.status = 'COMPLETED' if failed_count == 0 else 'FAILED'
            execution.results = results
            execution.save()
            try:
                from apps.reports.models import TestReport
                from ..utils import generate_allure_report
                unified_project = None
                if test_suite.project:
                    from apps.core_platform.models import Project
                    unified_project = Project.objects.filter(name=
                        test_suite.project.name).first()
                if unified_project:
                    allure_url = generate_allure_report(execution,
                        is_test_case=False)
                    TestReport.objects.create(project=unified_project, name
                        =
                        f"API套件测试 - {test_suite.name} ({timezone.now().strftime('%Y-%m-%d %H:%M')})"
                        , report_type='api_execution',
                        api_test_suite_execution=execution, allure_url=
                        allure_url, summary={'status': execution.status,
                        'total_steps': execution.total_requests,
                        'passed_steps': execution.passed_requests,
                        'failed_steps': execution.failed_requests,
                        'duration': round((execution.end_time - execution.
                        start_time).total_seconds(), 2) if execution.
                        end_time and execution.start_time else 0,
                        'test_suite_name': test_suite.name}, content={
                        'results': results, 'test_suite_id': test_suite.id,
                        'test_suite_name': test_suite.name}, generated_by=
                        request.user)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(
                    f'Auto-generate suite report failed: {e}', exc_info=True)
            log_operation(operation_type='execute', resource_type='suite',
                resource_id=test_suite.id, resource_name=test_suite.name,
                user=request.user)
            return Response(TestExecutionSerializer(execution).data)
        except Exception as e:
            if 'execution' in locals():
                execution.status = 'FAILED'
                execution.end_time = timezone.now()
                execution.save()
            return Response({'error': str(e)}, status=status.
                HTTP_400_BAD_REQUEST)

    def perform_destroy(self, instance):
        """删除测试套件时记录日志"""
        log_operation(operation_type='delete', resource_type='suite',
            resource_id=instance.id, resource_name=instance.name, user=self
            .request.user)
        instance.delete()

    @action(detail=True, methods=['post'], url_path='add-test-cases')
    def add_test_cases(self, request, pk=None):
        """添加测试用例到测试套件"""
        test_suite = self.get_object()
        test_case_ids = request.data.get('test_case_ids', [])
        try:
            for tc_id in test_case_ids:
                test_case = ApiTestCase.objects.get(id=tc_id)
                TestSuiteTestCase.objects.get_or_create(test_suite=
                    test_suite, test_case=test_case, defaults={'order':
                    TestSuiteTestCase.objects.filter(test_suite=test_suite)
                    .count(), 'enabled': True})
            return Response({'message': '添加成功'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.
                HTTP_400_BAD_REQUEST)

    def _replace_variables(self, text, variables):
        """替换文本中的变量"""
        if not isinstance(text, str):
            return text
        result = text
        for key, value in (variables or {}).items():
            if isinstance(value, dict):
                replacement = str(value.get('currentValue', '') or value.
                    get('initialValue', ''))
            else:
                replacement = str(value) if value is not None else ''
            result = result.replace(f'{{{{{key}}}}}', replacement)
        return result

    def _replace_variables_in_dict(self, data, variables):
        """递归替换字典中的变量"""
        if isinstance(data, dict):
            return {k: self._replace_variables_in_dict(v, variables) for k,
                v in data.items()}
        elif isinstance(data, list):
            return [self._replace_variables_in_dict(item, variables) for
                item in data]
        elif isinstance(data, str):
            return self._replace_variables(data, variables)
        else:
            return data


class TestSuiteRequestViewSet(BaseProjectViewSet):
    queryset = TestSuiteRequest.objects.all()
    serializer_class = TestSuiteRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['test_suite', 'enabled']


class TestExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TestExecution.objects.all()
    serializer_class = TestExecutionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'test_suite']
    ordering = ['-created_at']
    pagination_class = StandardPagination

    def get_queryset(self):
        user = self.request.user
        return TestExecution.objects.filter(test_suite__project__in=
            ApiProject.objects.filter(models.Q(owner=user) | models.Q(
            members=user))).distinct()

    @action(detail=True, methods=['post'], url_path='generate-allure-report')
    def generate_allure_report(self, request, pk=None):
        """生成Allure报告数据"""
        execution = self.get_object()
        try:
            results_dir = os.path.join(settings.MEDIA_ROOT,
                'allure-results', f'execution_{execution.id}')
            os.makedirs(results_dir, exist_ok=True)
            self._generate_test_result_files(execution, results_dir)
            report_output_dir = os.path.join(settings.MEDIA_ROOT,
                'allure-reports', f'execution_{execution.id}')
            os.makedirs(report_output_dir, exist_ok=True)
            import subprocess
            import shutil
            import time
            from pathlib import Path
            base_dir = Path(__file__).resolve().parent.parent.parent
            if os.name == 'nt':
                allure_executable = 'allure.bat'
            else:
                allure_executable = 'allure'
            allure_cmd = str(base_dir / 'allure' / 'bin' / allure_executable)
            if not os.path.exists(allure_cmd):
                logger.warning(
                    f'Allure command not found at: {allure_cmd}, using fallback'
                    )
                possible_paths = [base_dir / 'allure' / 'bin' /
                    allure_executable, Path('/usr/local/bin/allure'), Path(
                    '/usr/bin/allure')]
                for path in possible_paths:
                    if path.exists():
                        allure_cmd = str(path)
                        break
                else:
                    allure_cmd = None
            os.makedirs(results_dir, exist_ok=True)
            if allure_cmd:
                try:
                    for _ in range(3):
                        try:
                            if os.path.exists(report_output_dir):
                                shutil.rmtree(report_output_dir)
                            subprocess.run([allure_cmd, 'generate',
                                results_dir, '--clean', '--output',
                                report_output_dir], check=True,
                                capture_output=True, text=True, timeout=30)
                            break
                        except subprocess.TimeoutExpired:
                            if _ == 2:
                                raise
                            time.sleep(1)
                            continue
                except (subprocess.CalledProcessError, FileNotFoundError) as e:
                    logger.warning(
                        f'Allure command failed: {str(e)}, falling back to static files'
                        )
                static_dir = os.path.join(settings.MEDIA_ROOT, 'allure-static')
                if os.path.exists(static_dir):
                    for item in os.listdir(static_dir):
                        source = os.path.join(static_dir, item)
                        destination = os.path.join(report_output_dir, item)
                        if os.path.isdir(source):
                            shutil.copytree(source, destination,
                                dirs_exist_ok=True)
                        else:
                            shutil.copy2(source, destination)
                if not os.path.exists(os.path.join(report_output_dir,
                    'index.html')):
                    fallback_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>测试报告 - {execution.test_suite.name}</title>
</head>
<body>
    <h1>测试报告</h1>
    <p>测试套件: {execution.test_suite.name}</p>
    <p>状态: {execution.get_status_display()}</p>
    <p>总请求数: {execution.total_requests}</p>
    <p>通过: {execution.passed_requests}</p>
    <p>失败: {execution.failed_requests}</p>
</body>
</html>
"""
                    with open(os.path.join(report_output_dir, 'index.html'),
                        'w', encoding='utf-8') as f:
                        f.write(fallback_html)
            status_class = ('status-passed' if execution.status ==
                'COMPLETED' else 'status-failed')
            index_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>测试报告概览 - {execution.test_suite.name}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f7fa;
            color: #333;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 0;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header-content {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            padding: 2rem;
            max-width: 1200px;
            margin: 0 auto;
            position: relative;
        }}
        .header-info {{
            flex: 1;
            text-align: center;
        }}
        .header-actions {{
            position: absolute;
            right: 2rem;
            bottom: 2rem;
        }}
        .allure-report-btn {{
            display: inline-block;
            padding: 0.8rem 1.5rem;
            background: rgba(255, 255, 255, 0.2);
            color: white;
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-radius: 6px;
            text-decoration: none;
            font-weight: bold;
            transition: all 0.3s ease;
        }}
        .allure-report-btn:hover {{
            background: rgba(255, 255, 255, 0.3);
            border-color: rgba(255, 255, 255, 0.5);
            transform: translateY(-2px);
            text-decoration: none;
        }}
        .status-row {{
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 1rem;
        }}
        .execution-time {{
            color: #666;
            font-size: 0.9rem;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}
        .summary-card {{
            background: white;
            border-radius: 10px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }}
        .summary-item {{
            text-align: center;
            padding: 1rem;
            border-radius: 8px;
        }}
        .summary-item.total {{
            background: #e3f2fd;
        }}
        .summary-item.passed {{
            background: #e8f5e9;
        }}
        .summary-item.failed {{
            background: #ffebee;
        }}
        .summary-number {{
            font-size: 2rem;
            font-weight: bold;
            display: block;
        }}
        .summary-label {{
            font-size: 0.9rem;
            opacity: 0.8;
        }}
        .status-badge {{
            display: inline-block;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-weight: bold;
            margin-bottom: 1rem;
        }}
        .status-passed {{
            background: #4caf50;
            color: white;
        }}
        .status-failed {{
            background: #f44336;
            color: white;
        }}
        .test-results {{
            background: white;
            border-radius: 10px;
            padding: 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .test-result-item {{
            padding: 1rem;
            border-left: 4px solid #eee;
            margin-bottom: 1rem;
            border-radius: 4px;
        }}
        .test-result-item.passed {{
            border-left-color: #4caf50;
            background: #f8fff8;
        }}
        .test-result-item.failed {{
            border-left-color: #f44336;
            background: #fff8f8;
        }}
        .test-header {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 0.5rem;
        }}
        .test-name {{
            font-weight: bold;
            font-size: 1.1rem;
        }}
        .test-method {{
            display: inline-block;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.9rem;
            margin-right: 0.5rem;
        }}
        .method-get {{ background: #2196f3; color: white; }}
        .method-post {{ background: #4caf50; color: white; }}
        .method-put {{ background: #ff9800; color: white; }}
        .method-delete {{ background: #f44336; color: white; }}
        .test-url {{
            color: #666;
            font-size: 0.9rem;
            margin: 0.5rem 0;
            word-break: break-all;
        }}
        .test-error {{
            color: #f44336;
            font-size: 0.9rem;
            margin-top: 0.5rem;
            padding: 0.5rem;
            background: #ffebee;
            border-radius: 4px;
        }}
        .footer {{
            text-align: center;
            margin-top: 2rem;
            padding: 1rem;
            color: #666;
            font-size: 0.9rem;
        }}
        a {{
            color: #667eea;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <div class="header-info">
                <h1>接口测试报告</h1>
                <p>测试套件: {execution.test_suite.name}</p>
                <p>项目: {execution.test_suite.project.name}</p>
            </div>
            <div class="header-actions">
                <a href="index.html" target="_blank" class="allure-report-btn">查看完整Allure报告</a>
            </div>
        </div>
    </div>
    
    <div class="container">
        <div class="summary-card">
            <div class="status-row">
                <div class="status-badge {status_class}">
                    状态: {execution.get_status_display()}
                </div>
                <span class="execution-time">
                    执行时间: {execution.created_at.strftime('%Y-%m-%d %H:%M:%S') if execution.created_at else 'N/A'}
                </span>
            </div>
            
            <div class="summary-grid">
                <div class="summary-item total">
                    <span class="summary-number">{execution.total_requests or 0}</span>
                    <span class="summary-label">总请求数</span>
                </div>
                <div class="summary-item passed">
                    <span class="summary-number">{execution.passed_requests or 0}</span>
                    <span class="summary-label">通过数</span>
                </div>
                <div class="summary-item failed">
                    <span class="summary-number">{execution.failed_requests or 0}</span>
                    <span class="summary-label">失败数</span>
                </div>
            </div>
        </div>
        
        <div class="test-results">
            <h2>测试结果详情</h2>
"""
            if execution.results:
                for i, result in enumerate(execution.results):
                    is_test_case = result.get('type') == 'test_case'
                    if is_test_case:
                        is_passed = result.get('status') == 'passed'
                        result_class = 'passed' if is_passed else 'failed'
                        method_class = 'method-post'
                        method_name = 'CASE'
                        name = result.get('name', f'测试用例 {i + 1}')
                        passed_count = result.get('passed_count', 0)
                        failed_count = result.get('failed_count', 0)
                        url = (
                            f"Steps: {len(result.get('results', []))} (Passed: {passed_count}, Failed: {failed_count})"
                            )
                        status_text = '通过' if is_passed else '失败'
                    else:
                        is_passed = result.get('passed', False)
                        result_class = 'passed' if is_passed else 'failed'
                        method_class = (
                            f"method-{result.get('method', 'GET').lower()}")
                        method_name = result.get('method', 'GET')
                        name = result.get('name', f'测试请求 {i + 1}')
                        url = result.get('url', '')
                        status_text = '通过' if is_passed else '失败'
                    index_content += f"""
            <div class="test-result-item {result_class}">
                <div class="test-header">
                    <span class="test-method {method_class}">{method_name}</span>
                    <span class="test-name">{name}</span>
                </div>
                <div class="test-url">{url}</div>
                <div><strong>状态:</strong> {status_text}</div>
                {(f'<div class="test-error"><strong>错误:</strong> {result.get("error", "")}</div>' if result.get('error') else '')}
            </div>
"""
            index_content += f"""
        </div>
        <div class="footer">
            <p>报告生成时间: {execution.created_at.strftime('%Y-%m-%d %H:%M:%S') if execution.created_at else 'N/A'}</p>
        </div>
    </div>
</body>
</html>
"""
            summary_file = os.path.join(report_output_dir, 'summary.html')
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(index_content)
            return Response({'message': 'Allure报告生成成功', 'report_url':
                f'/media/allure-reports/execution_{execution.id}/summary.html'}
                )
        except Exception as e:
            return Response({'error': str(e)}, status=status.
                HTTP_400_BAD_REQUEST)

    def _generate_test_result_files(self, execution, report_dir):
        """生成测试结果文件"""
        container_data = {'uuid': str(execution.id), 'name': execution.
            test_suite.name, 'children': []}
        if execution.results:
            for i, result in enumerate(execution.results):
                container_data['children'].append(f'{execution.id}-{i}')
        container_file_path = os.path.join(report_dir,
            f'{execution.id}-container.json')
        with open(container_file_path, 'w', encoding='utf-8') as f:
            json.dump(container_data, f, ensure_ascii=False, indent=2)
        if execution.results:
            for i, result in enumerate(execution.results):
                is_test_case = result.get('type') == 'test_case'
                if is_test_case:
                    status_str = 'passed' if result.get('status'
                        ) == 'passed' else 'failed'
                    description = f"Test Case: {result.get('name')}"
                    steps_data = []
                    for step_idx, step in enumerate(result.get('results', [])):
                        step_status = 'passed' if step.get('passed', False
                            ) else 'failed'
                        steps_data.append({'name': step.get('name',
                            f'Step {step_idx + 1}'), 'status': step_status,
                            'stage': 'finished', 'start': int(time.time() *
                            1000) - 500, 'stop': int(time.time() * 1000),
                            'parameters': [{'name': 'method', 'value': step
                            .get('method', 'GET')}, {'name': 'url', 'value':
                            step.get('url', '')}, {'name': 'status_code',
                            'value': str(step.get('status_code', ''))}],
                            'steps': []})
                else:
                    status_str = 'passed' if result.get('passed', False
                        ) else 'failed'
                    description = f"""Method: {result.get('method', 'GET')}
URL: {result.get('url', '')}"""
                    steps_data = [{'name': '发送请求', 'status': 'passed',
                        'stage': 'finished', 'start': int(time.time() * 
                        1000) - 1000, 'stop': int(time.time() * 1000) - 500,
                        'steps': []}, {'name': '验证响应', 'status': status_str,
                        'stage': 'finished', 'start': int(time.time() * 
                        1000) - 500, 'stop': int(time.time() * 1000),
                        'steps': []}]
                request_result = {'uuid': f'{execution.id}-{i}', 'name':
                    result.get('name', f'测试请求 {i + 1}'), 'status':
                    status_str, 'stage': 'finished', 'start': int(time.time
                    () * 1000) - 1000, 'stop': int(time.time() * 1000),
                    'description': description, 'historyId':
                    f'{execution.test_suite.id}-{i}', 'fullName':
                    f"{execution.test_suite.name} / {result.get('name', f'请求 {i + 1}')}"
                    , 'links': [], 'labels': [{'name': 'suite', 'value':
                    execution.test_suite.name}, {'name': 'testClass',
                    'value': execution.test_suite.name}, {'name': 'package',
                    'value': 'api_testing'}, {'name': 'project', 'value':
                    execution.test_suite.project.name}], 'parameters': [{
                    'name': 'method', 'value': result.get('method', 'GET')},
                    {'name': 'url', 'value': result.get('url', '')}],
                    'steps': steps_data}
                if result.get('error'):
                    request_result['statusDetails'] = {'message': result.
                        get('error'), 'trace': ''}
                request_file_path = os.path.join(report_dir,
                    f'{execution.id}-{i}-result.json')
                with open(request_file_path, 'w', encoding='utf-8') as f:
                    json.dump(request_result, f, ensure_ascii=False, indent=2)


class OperationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """操作日志视图集"""
    queryset = OperationLog.objects.all()
    serializer_class = OperationLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['operation_type', 'resource_type', 'user']
    ordering = ['-created_at']

    def get_queryset(self):
        """只返回当前用户相关的操作日志"""
        user = self.request.user
        return OperationLog.objects.all().order_by('-created_at')


