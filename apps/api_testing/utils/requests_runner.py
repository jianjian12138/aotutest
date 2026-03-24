from apps.notifications.models import NotificationConfig, NotificationLog
import json
import time
import os
import shutil
import subprocess
import logging
from pathlib import Path
from django.utils import timezone
from django.conf import settings
from ..models import RequestHistory, ApiTestCaseExecution
from apps.core_platform.models import GlobalParameter
from .variables import _replace_variables, extract_variables
from .assertions import execute_assertions

def execute_test_case(test_case, environment, executed_by, create_report=True, context_variables=None):
    """执行测试用例并返回结果"""
    import requests
    import time
    from ..models import RequestHistory, ApiTestCaseExecution
    
    start_execution_time = time.time()
    try:
        # 获取用例步骤
        steps = test_case.steps.filter(enable=True).order_by('step_number')
        
        results = []
        passed_count = 0
        failed_count = 0
        total_count = steps.count()
        
        # 初始化变量字典
        variables = {}
        if environment:
            variables.update(environment.variables)
        
        # 获取全局参数作为兜底
        global_params = GlobalParameter.objects.all()
        for param in global_params:
            if param.key not in variables:
                variables[param.key] = param.value
                
        # 注入跨用例上下文变量 (来自 TestSuite 或外部循环)
        if context_variables:
            variables.update(context_variables)
        
        # 执行每个步骤
        for step in steps:
            try:
                # 确定请求参数 source of truth
                # 默认使用步骤自身的配置（因为前端编辑时是在步骤层面修改的）
                method = step.method
                url = step.url
                headers = step.headers
                params = step.params
                body = step.body
                
                # 如果引用的接口有数据，但步骤自身某项未空，理论上可以合并或回退
                # 不过现在前端每次保存步骤都会包含全量参数，所以直接取步骤自身的即可。
                if step.api_request:
                    if not method: method = step.api_request.method
                    if not url: url = step.api_request.url
                    if not headers: headers = step.api_request.headers
                    if not params: params = step.api_request.params
                    if not body: body = step.api_request.body
                
                # 替换URL中的变量
                url = _replace_variables(url, variables)
                
                # 准备请求头
                req_headers = {}
                if isinstance(headers, list):
                    for header_item in headers:
                        if header_item.get('enabled', True) and header_item.get('key'):
                            key = header_item['key']
                            value = _replace_variables(str(header_item.get('value', '')), variables)
                            req_headers[key] = value
                else:
                    req_headers = headers.copy()
                    for key, value in req_headers.items():
                        req_headers[key] = _replace_variables(str(value), variables)
                
                # 准备请求参数
                req_params = {}
                if params:
                    if isinstance(params, list):
                        # 处理列表格式的参数 [{key: 'name', value: 'val', enabled: true}, ...]
                        for param_item in params:
                            if isinstance(param_item, dict) and param_item.get('enabled', True) and param_item.get('key'):
                                req_params[param_item['key']] = _replace_variables(str(param_item.get('value', '')), variables)
                    elif isinstance(params, dict):
                        req_params = params.copy()
                        for key, value in req_params.items():
                            req_params[key] = _replace_variables(str(value), variables)
                
                # 准备请求体
                req_body_data = None
                if body and method in ['POST', 'PUT', 'PATCH']:
                    if body.get('type') == 'json':
                        req_body_data = body.get('data', {})
                        if isinstance(req_body_data, str):
                            # 如果data是字符串，先替换变量再解析JSON
                            req_body_data = _replace_variables(req_body_data, variables)
                            try:
                                req_body_data = json.loads(req_body_data)
                            except (json.JSONDecodeError, TypeError):
                                pass
                        else:
                            req_body_data = _replace_variables_in_dict(req_body_data, variables)
                    else:
                        # 处理其他类型的body，如raw
                        raw_data = body.get('data')
                        if isinstance(raw_data, str):
                            req_body_data = _replace_variables(raw_data, variables)
                        else:
                            req_body_data = _replace_variables_in_dict(raw_data, variables)
                
                # 等待时间
                if step.wait_time > 0:
                    time.sleep(step.wait_time / 1000.0)
                
                # 执行请求
                start_time = time.time()
                response = requests.request(
                    method=method,
                    url=url,
                    headers=req_headers,
                    params=req_params,
                    json=req_body_data if body and body.get('type') == 'json' else None,
                    data=req_body_data if body and body.get('type') != 'json' else None,
                    timeout=30
                )
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                
                # 执行断言验证
                assertions = step.assertions or []
                # 如果引用了API请求，也包含API请求的断言? 通常步骤定义的断言会覆盖或补充
                # 这里我们假设步骤定义的断言是最终的
                
                for assertion in assertions:
                    if assertion.get('type') == 'response_time':
                        assertion['actual_time'] = response_time
                
                assertions_results = execute_assertions(response, assertions)
                
                # 提取变量
                extracted_vars = {}
                if step.extract_rules:
                    extracted_vars = extract_variables(response, step.extract_rules)
                    variables.update(extracted_vars)
                
                # 检查所有断言是否通过
                passed = True
                error_message = ''
                
                if assertions_results:
                    for assertion_result in assertions_results:
                        if not assertion_result.get('passed', True):
                            passed = False
                            error_message = f"断言失败: {assertion_result.get('name', '未命名断言')} - {assertion_result.get('error', '断言不通过')}"
                            break
                
                if passed:
                    passed_count += 1
                else:
                    failed_count += 1
                
                step_result = {
                    'step_number': step.step_number,
                    'name': step.name,
                    'method': method,
                    'url': url,
                    'request_headers': req_headers,
                    'request_body': req_body_data,
                    'status_code': response.status_code,
                    'response_headers': dict(response.headers),
                    'response_body': response.text,
                    'response_json': response.json() if response.headers.get('content-type', '').startswith('application/json') else None,
                    'response_time': response_time,
                    'passed': passed,
                    'error': error_message,
                    'assertions': assertions_results,
                    'extracted_variables': extracted_vars
                }
                results.append(step_result)
                
                # 回写到跨用例上下文变量池中供后续用例使用
                if context_variables is not None:
                    context_variables.update(extracted_vars)
                
                # 保存请求历史
                if step.api_request:
                    RequestHistory.objects.create(
                        request=step.api_request,
                        environment=environment,
                        request_data={
                            'url': url,
                            'method': method,
                            'headers': req_headers,
                            'params': req_params,
                            'body': req_body_data
                        },
                        response_data={
                            'headers': dict(response.headers),
                            'body': response.text,
                            'json': response.json() if response.headers.get('content-type', '').startswith('application/json') else None
                        },
                        status_code=response.status_code,
                        response_time=response_time,
                        assertions_results=assertions_results,
                        executed_by=executed_by
                    )
                
            except Exception as e:
                failed_count += 1
                results.append({
                    'step_number': step.step_number,
                    'name': step.name,
                    'passed': False,
                    'error': str(e)
                })
        
        # 计算总耗时
        execution_time = (time.time() - start_execution_time) * 1000
        
        # 确定整体状态
        status = 'passed' if failed_count == 0 else 'failed'
        
        # 保存执行记录
        execution_record = ApiTestCaseExecution.objects.create(
            test_case=test_case,
            status=status,
            total_steps=total_count,
            passed_steps=passed_count,
            failed_steps=failed_count,
            results=results,
            execution_time=execution_time,
            executed_by=executed_by
        )
        
        # 自动生成统一测试报告
        if create_report:
            try:
                from apps.reports.models import TestReport
                # 获取用例所属的项目（通过步骤的 api_request 关联）
                project = None
                first_step = test_case.steps.first()
                if first_step and first_step.api_request and first_step.api_request.collection:
                    project = first_step.api_request.collection.project
                
                if project:
                    # 查找对应的统一管理项目
                    from apps.core_platform.models import Project
                    unified_project = Project.objects.filter(name=project.name).first()
                    if unified_project:
                        # 生成Allure报告
                        allure_url = generate_allure_report(execution_record, is_test_case=True)
                        
                        TestReport.objects.create(
                            project=unified_project,
                            name=f'API测试 - {test_case.name} ({timezone.now().strftime("%Y-%m-%d %H:%M")})',
                            report_type='api_execution',
                            api_test_execution=execution_record,
                            allure_url=allure_url,
                            summary={
                                'status': status,
                                'total_steps': total_count,
                                'passed_steps': passed_count,
                                'failed_steps': failed_count,
                                'execution_time': round(execution_time, 2),
                                'test_case_name': test_case.name,
                            },
                            content={
                                'results': results,
                                'test_case_id': test_case.id,
                                'test_case_name': test_case.name,
                            },
                            generated_by=executed_by
                        )
            except Exception as e:
                # 报告生成失败不影响执行结果
                logger.warning(f"Auto-generate test report failed: {e}", exc_info=True)
        
        return {
            'success': True,
            'status': status,
            'passed_steps': passed_count,
            'failed_steps': failed_count,
            'total_steps': total_count,
            'execution_time': execution_time,
            'results': results
        }
        
    except Exception as e:
        # 如果发生异常，也尝试保存一条错误记录
        try:
            ApiTestCaseExecution.objects.create(
                test_case=test_case,
                status='error',
                results=[{'error': str(e)}],
                executed_by=executed_by
            )
        except:
            pass
            
        return {
            'success': False,
            'error': str(e)
        }


def execute_test_suite(test_suite, environment, executed_by):
    """
    执行测试套件并返回结果（支持跨用例变量传递）
    迭代执行套件内的测试用例（TestCase），不再执行零散的API请求。
    """
    from ..models import TestExecution
    import time
    
    try:
        # 创建执行记录
        execution = TestExecution.objects.create(
            test_suite=test_suite,
            status='RUNNING',
            start_time=timezone.now(),
            executed_by=executed_by
        )
        
        # 获取套件中的测试用例关联记录
        suite_test_cases = test_suite.testsuitetestcase_set.filter(enabled=True).order_by('order')
        
        execution.total_requests = suite_test_cases.count()  # 兼容旧字段名，实际上是总用例数
        execution.save()
        
        results = []
        passed_count = 0
        failed_count = 0
        
        # 初始化跨用例共享上下文变量池
        context_variables = {}
        
        # 依次执行每个测试用例
        for suite_test_case in suite_test_cases:
            test_case = suite_test_case.test_case
            
            try:
                # 调用 execute_test_case 并传入 context_variables，不单独生成报告
                # 这样会把 test_case 的执行结果汇总进来，并在内部提取变量到 context_variables 中
                case_result = execute_test_case(
                    test_case=test_case,
                    environment=environment,
                    executed_by=executed_by,
                    create_report=False,
                    context_variables=context_variables
                )
                
                # 统计通过/失败数 (以用例级别划分)
                if case_result.get('status') == 'passed':
                    passed_count += 1
                else:
                    failed_count += 1
                    
                results.append({
                    'name': test_case.name,
                    'is_test_case': True,
                    'status': case_result.get('status', 'failed'),
                    'passed_steps': case_result.get('passed_steps', 0),
                    'failed_steps': case_result.get('failed_steps', 0),
                    'total_steps': case_result.get('total_steps', 0),
                    'execution_time': case_result.get('execution_time', 0),
                    'error': case_result.get('error', ''),
                    'steps_results': case_result.get('results', [])
                })
                
            except Exception as e:
                failed_count += 1
                results.append({
                    'name': test_case.name,
                    'is_test_case': True,
                    'status': 'error',
                    'error': str(e)
                })
        
        # 更新执行结果
        execution.end_time = timezone.now()
        execution.passed_requests = passed_count
        execution.failed_requests = failed_count
        execution.status = 'COMPLETED' if failed_count == 0 else 'FAILED'
        execution.results = results
        execution.save()
        
        return {
            'success': True,
            'execution_id': execution.id,
            'passed_count': passed_count,
            'failed_count': failed_count,
            'total_count': execution.total_requests,
            'results': results
        }
        
    except Exception as e:
        logger.error(f"执行测试套件失败: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }


def execute_api_request(api_request, environment, executed_by):
    """执行单个API请求并返回结果"""
    import requests
    import time
    
    try:
        # 解析环境变量
        variables = {}
        if environment:
            variables.update(environment.variables)
        
        # 替换URL中的变量
        url = _replace_variables(api_request.url, variables)
        
        # 准备请求头
        headers = {}
        if isinstance(api_request.headers, list):
            for header_item in api_request.headers:
                if header_item.get('enabled', True) and header_item.get('key'):
                    key = header_item['key']
                    value = _replace_variables(str(header_item.get('value', '')), variables)
                    headers[key] = value
        else:
            headers = api_request.headers.copy()
            for key, value in headers.items():
                headers[key] = _replace_variables(str(value), variables)
        
        # 准备请求参数
        params = api_request.params.copy() if api_request.params else {}
        for key, value in params.items():
            params[key] = _replace_variables(str(value), variables)
        
        # 准备请求体
        body_data = None
        if api_request.body and api_request.method in ['POST', 'PUT', 'PATCH']:
            if api_request.body.get('type') == 'json':
                body_data = api_request.body.get('data', {})
                body_data = _replace_variables_in_dict(body_data, variables)
        
        # 执行请求
        start_time = time.time()
        response = requests.request(
            method=api_request.method,
            url=url,
            headers=headers,
            params=params,
            json=body_data,
            timeout=30
        )
        end_time = time.time()
        response_time = (end_time - start_time) * 1000
        
        # 执行断言验证
        assertions = api_request.assertions or []
        for assertion in assertions:
            if assertion.get('type') == 'response_time':
                assertion['actual_time'] = response_time
        
        assertions_results = execute_assertions(response, assertions)
        
        # 保存请求历史
        history = RequestHistory.objects.create(
            request=api_request,
            environment=environment,
            request_data={
                'url': url,
                'method': api_request.method,
                'headers': headers,
                'params': params,
                'body': body_data
            },
            response_data={
                'headers': dict(response.headers),
                'body': response.text,
                'json': response.json() if response.headers.get('content-type', '').startswith('application/json') else None
            },
            status_code=response.status_code,
            response_time=response_time,
            assertions_results=assertions_results,
            executed_by=executed_by
        )
        
        return {
            'success': True,
            'history_id': history.id,
            'status_code': response.status_code,
            'response_time': response_time,
            'assertions_results': assertions_results,
            'response_data': {
                'headers': dict(response.headers),
                'body': response.text,
                'json': response.json() if response.headers.get('content-type', '').startswith('application/json') else None
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


