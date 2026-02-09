import json
import time
from django.utils import timezone
from .models import RequestHistory, ApiTestCaseExecution
from apps.configuration.models import GlobalParameter


def execute_assertions(response, assertions):
    """执行断言验证"""
    results = []
    
    for assertion in assertions:
        result = {
            'name': assertion.get('name', '未命名断言'),
            'type': assertion.get('type'),
            'passed': False,
            'expected': assertion.get('expected'),
            'actual': None,
            'error': None
        }
        
        try:
            assertion_type = assertion.get('type')
            expected = assertion.get('expected')
            actual = None
            passed = False
            
            if assertion_type == 'status_code':
                actual = response.status_code
                operator = assertion.get('operator', 'equals')
                if operator == 'equals':
                    passed = str(actual) == str(expected)
                elif operator == 'not_equals':
                    passed = str(actual) != str(expected)
                else:
                    passed = str(actual) == str(expected)
                
            elif assertion_type == 'response_time':
                actual = assertion.get('actual_time')
                operator = assertion.get('operator', 'lt')
                if operator == 'lt':
                    passed = actual <= expected if actual else False
                elif operator == 'gt':
                    passed = actual >= expected if actual else False
                else:
                    passed = actual <= expected if actual else False
                
            elif assertion_type == 'contains':
                text = response.text or ''
                pattern = str(expected)
                actual = text[:200] + '...' if len(text) > 200 else text
                operator = assertion.get('operator', 'contains')
                if operator == 'contains':
                    passed = pattern in str(text)
                elif operator == 'not_contains':
                    passed = pattern not in str(text)
                else:
                    passed = pattern in str(text)
                
            elif assertion_type == 'json_path':
                json_path = assertion.get('json_path', '')
                expected_value = assertion.get('expected')
                operator = assertion.get('operator', 'equals')
                actual = None
                passed = False
                
                try:
                    # 检查响应是否为JSON格式
                    content_type = response.headers.get('content-type', '').lower()
                    if 'application/json' not in content_type:
                        raise ValueError(f"响应不是JSON格式，Content-Type: {content_type}")
                    
                    response_json = json.loads(response.text)
                    
                    if not json_path:
                        raise ValueError("JSON路径表达式不能为空")
                    
                    from jsonpath_ng import parse
                    matches = parse(json_path).find(response_json)
                    actual = matches[0].value if matches else None
                    
                    # 根据操作符比较
                    if operator == 'equals':
                        passed = str(actual) == str(expected_value)
                    elif operator == 'not_equals':
                        passed = str(actual) != str(expected_value)
                    elif operator == 'contains':
                        passed = str(expected_value) in str(actual)
                    elif operator == 'gt':
                        passed = float(actual) > float(expected_value)
                    elif operator == 'lt':
                        passed = float(actual) < float(expected_value)
                    else:
                        passed = str(actual) == str(expected_value)
                    
                    result['actual'] = actual
                except json.JSONDecodeError as e:
                    actual = None
                    passed = False
                    result['error'] = f"JSON解析失败: {str(e)}"
                    result['actual'] = actual
                except ImportError as e:
                    actual = None
                    passed = False
                    result['error'] = f"缺少依赖库: {str(e)}，请安装jsonpath-ng"
                    result['actual'] = actual
                except Exception as e:
                    actual = None
                    passed = False
                    result['error'] = f"执行错误: {str(e)}"
                    result['actual'] = actual
                    
            elif assertion_type == 'header':
                header_name = assertion.get('header_name', '')
                expected_value = assertion.get('expected_value')
                actual = response.headers.get(header_name)
                passed = actual == expected_value
                
            elif assertion_type == 'equals':
                actual = response.text.strip()
                passed = actual == str(expected).strip()
            
            elif assertion_type == 'database':
                # 数据库校验断言
                config_id = assertion.get('config_id')
                generated_sql = assertion.get('generated_sql')
                expected = assertion.get('expected')
                
                if not config_id or not generated_sql:
                    passed = False
                    result['error'] = "缺少数据库配置ID或SQL语句"
                    actual = None
                else:
                    try:
                        # 动态导入避免循环依赖
                        from apps.data_factory.models import VannaConfig
                        import pymysql
                        from pymysql.cursors import DictCursor
                        
                        config = VannaConfig.objects.get(id=config_id)
                        db_config = config.db_connection
                        
                        # 连接并执行
                        connection = pymysql.connect(
                            host=db_config.get('host', 'localhost'),
                            port=int(db_config.get('port', 3306)),
                            user=db_config.get('username', ''),
                            password=db_config.get('password', ''),
                            database=db_config.get('database', ''),
                            cursorclass=DictCursor,
                            connect_timeout=5
                        )
                        
                        try:
                            with connection.cursor() as cursor:
                                cursor.execute(generated_sql)
                                rows = cursor.fetchall()
                                actual = rows
                                
                                # 比较逻辑
                                if str(expected).lower() == 'true':
                                    passed = len(rows) > 0
                                elif str(expected).lower() == 'false':
                                    passed = len(rows) == 0
                                elif str(expected).startswith('>') and str(expected)[1:].isdigit():
                                    passed = len(rows) > int(str(expected)[1:])
                                else:
                                    # 尝试作为JSON解析比较，或者字符串包含
                                    try:
                                        if isinstance(expected, str) and (expected.startswith('{') or expected.startswith('[')):
                                            expected_json = json.loads(expected)
                                            passed = actual == expected_json
                                        else:
                                            passed = str(expected) == str(actual) or str(expected) in str(actual)
                                    except:
                                        passed = str(expected) == str(actual) or str(expected) in str(actual)
                                    
                        finally:
                            connection.close()
                            
                    except Exception as db_err:
                        passed = False
                        result['error'] = f"数据库执行错误: {str(db_err)}"
                        actual = None
            
            # 确保在所有情况下都设置actual值
            if 'actual' not in result or result['actual'] is None:
                result['actual'] = actual
            result['passed'] = passed
            
        except Exception as e:
            result['error'] = str(e)
            result['passed'] = False
        
        results.append(result)
    
    return results


def extract_variables(response, extract_rules):
    """从响应中提取变量"""
    extracted_variables = {}
    
    for rule in extract_rules:
        try:
            extract_type = rule.get('type')
            variable_name = rule.get('variable_name')
            
            if not variable_name:
                continue
            
            if extract_type == 'status_code':
                # 从状态码提取
                extracted_variables[variable_name] = response.status_code
            
            elif extract_type == 'json_path':
                # 从JSON响应中提取
                json_path = rule.get('json_path')
                if json_path:
                    try:
                        response_json = response.json()
                        from jsonpath_ng import parse
                        matches = parse(json_path).find(response_json)
                        if matches:
                            extracted_variables[variable_name] = matches[0].value
                    except Exception as e:
                        # JSON解析失败或JSONPath提取失败，跳过此规则
                        continue
            
            elif extract_type == 'header':
                # 从响应头提取
                header_name = rule.get('header_name')
                if header_name:
                    extracted_variables[variable_name] = response.headers.get(header_name)
            
            elif extract_type == 'regex':
                # 从响应文本中使用正则表达式提取
                pattern = rule.get('pattern')
                if pattern:
                    import re
                    match = re.search(pattern, response.text)
                    if match:
                        extracted_variables[variable_name] = match.group(1) if match.groups() else match.group()
        
        except Exception as e:
            # 提取失败，跳过此规则
            continue
    
    return extracted_variables


def execute_test_case(test_case, environment, executed_by):
    """执行测试用例并返回结果"""
    import requests
    import time
    from .models import RequestHistory, ApiTestCaseExecution
    
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
        
        # 执行每个步骤
        for step in steps:
            try:
                # 确定请求参数 source of truth
                if step.api_request:
                    method = step.api_request.method
                    url = step.api_request.url
                    headers = step.api_request.headers
                    params = step.api_request.params
                    body = step.api_request.body
                else:
                    method = step.method
                    url = step.url
                    headers = step.headers
                    params = step.params
                    body = step.body
                
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
                req_params = params.copy() if params else {}
                for key, value in req_params.items():
                    req_params[key] = _replace_variables(str(value), variables)
                
                # 准备请求体
                req_body_data = None
                if body and method in ['POST', 'PUT', 'PATCH']:
                    if body.get('type') == 'json':
                        req_body_data = body.get('data', {})
                        req_body_data = _replace_variables_in_dict(req_body_data, variables)
                    else:
                        # 处理其他类型的body，如raw
                        req_body_data = _replace_variables_in_dict(body.get('data'), variables)
                
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
                    'extracted_variables': extracted_vars if 'extracted_vars' in locals() else {}
                }
                results.append(step_result)
                
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
        ApiTestCaseExecution.objects.create(
            test_case=test_case,
            status=status,
            total_steps=total_count,
            passed_steps=passed_count,
            failed_steps=failed_count,
            results=results,
            execution_time=execution_time,
            executed_by=executed_by
        )
        
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
    """执行测试套件并返回结果"""
    from .models import TestExecution, RequestHistory
    import requests
    import time
    
    try:
        # 创建执行记录
        execution = TestExecution.objects.create(
            test_suite=test_suite,
            status='RUNNING',
            start_time=timezone.now(),
            executed_by=executed_by
        )
        
        # 获取套件中的请求
        suite_requests = test_suite.testsuiterequest_set.filter(enabled=True).order_by('order')
        
        execution.total_requests = suite_requests.count()
        execution.save()
        
        results = []
        passed_count = 0
        failed_count = 0
        
        # 初始化变量字典，用于存储环境变量和从响应中提取的变量
        variables = {}
        if environment:
            variables.update(environment.variables)
        
        # 执行每个请求
        for suite_request in suite_requests:
            api_request = suite_request.request
            
            try:
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
                
                # 提取变量
                if api_request.extract_rules:
                    extracted_vars = extract_variables(response, api_request.extract_rules)
                    variables.update(extracted_vars)
                
                # 检查所有断言是否通过
                passed = True
                error_message = ''
                
                # 检查套件请求的断言
                for assertion in suite_request.assertions:
                    if assertion.get('type') == 'status_code':
                        expected = assertion.get('value')
                        if response.status_code != expected:
                            passed = False
                            error_message = f'状态码断言失败: 期望 {expected}, 实际 {response.status_code}'
                            break
                
                # 检查接口自身的断言
                if passed and assertions_results:
                    for assertion_result in assertions_results:
                        if not assertion_result.get('passed', True):
                            passed = False
                            error_message = f"断言失败: {assertion_result.get('name', '未命名断言')} - {assertion_result.get('error', '断言不通过')}"
                            break
                
                if passed:
                    passed_count += 1
                else:
                    failed_count += 1
                
                results.append({
                    'name': api_request.name,
                    'method': api_request.method,
                    'url': url,
                    'status_code': response.status_code,
                    'response_time': response_time,
                    'passed': passed,
                    'error': error_message,
                    'assertions_results': assertions_results,
                    'extracted_variables': extracted_vars if 'extracted_vars' in locals() else {}
                })
                
                # 保存请求历史
                RequestHistory.objects.create(
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
                
            except Exception as e:
                failed_count += 1
                results.append({
                    'name': api_request.name,
                    'method': api_request.method,
                    'url': api_request.url,
                    'passed': False,
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


def _replace_variables(text, variables):
    """替换文本中的变量"""
    if not isinstance(text, str):
        return text
    
    import re
    
    # DEBUG log
    print(f"DEBUG: _replace_variables input: {text}")
    print(f"DEBUG: variables: {variables}")
    
    result = text
    for key, value in (variables or {}).items():
        if isinstance(value, dict):
            replacement = str(value.get('currentValue', '') or value.get('initialValue', ''))
        else:
            replacement = str(value) if value is not None else ''
        
        # 使用正则替换，支持 {{key}} 和 {{ key }} 格式
        pattern = r'\{\{\s*' + re.escape(key) + r'\s*\}\}'
        result = re.sub(pattern, replacement, result)
        
    print(f"DEBUG: _replace_variables output: {result}")
    return result


def _replace_variables_in_dict(data, variables):
    """递归替换字典中的变量"""
    if isinstance(data, dict):
        return {k: _replace_variables_in_dict(v, variables) for k, v in data.items()}
    elif isinstance(data, list):
        return [_replace_variables_in_dict(item, variables) for item in data]
    elif isinstance(data, str):
        return _replace_variables(data, variables)
    else:
        return data


def execute_test_case_httprunner(test_case, environment, executed_by):
    """使用HttpRunner v4执行测试用例"""
    import os
    import json
    import time
    from django.conf import settings
    from .models import RequestHistory
    
    try:
        from httprunner import HttpRunner, Config, RunRequest, RunTestCase, Step
    except ImportError:
        return {
            'success': False,
            'error': 'HttpRunner未安装，请联系管理员安装httprunner库'
        }

    try:
        # 1. 准备配置
        config = Config(test_case.name).base_url("")
        
        # 处理环境变量
        variables = {}
        if environment:
            for k, v in environment.variables.items():
                if isinstance(v, dict):
                    variables[k] = v.get('currentValue', '') or v.get('initialValue', '')
                else:
                    variables[k] = v
            config.variables(**variables)
        
        test_steps = []
        # 获取所有启用的步骤
        steps = test_case.steps.filter(enable=True).order_by('step_number')
        
        if not steps.exists():
            return {
                'success': True,
                'passed_count': 0,
                'failed_count': 0,
                'total_count': 0,
                'results': [],
                'message': '没有可执行的步骤'
            }
        
        for step in steps:
            # 获取请求数据
            if step.api_request:
                method = step.api_request.method
                url = step.api_request.url
                headers = step.api_request.headers
                params = step.api_request.params
                body = step.api_request.body
                assertions = step.api_request.assertions
                extract_rules = step.api_request.extract_rules
            else:
                method = step.method
                url = step.url
                headers = step.headers
                params = step.params
                body = step.body
                assertions = step.assertions
                extract_rules = step.extract_rules
            
            # 预处理URL中的变量，避免HttpRunner v4因URL非绝对路径而报错
            url = _replace_variables(url, variables)
            
            # 检查URL是否包含未替换的变量或非绝对路径
            url_stripped = url.strip()
            if url_stripped.startswith("{{"):
                import re
                var_match = re.match(r'\{\{\s*(.*?)\s*\}\}', url_stripped)
                var_name = var_match.group(1) if var_match else "unknown"
                return {
                    'success': False,
                    'error': f"步骤 '{step.name}' URL配置错误: 变量 '{var_name}' 未在环境中定义或未被替换。当前URL: {url}"
                }
            
            if not (url_stripped.lower().startswith("http://") or url_stripped.lower().startswith("https://")):
                return {
                    'success': False,
                    'error': f"步骤 '{step.name}' URL无效: '{url}'。URL必须以 http:// 或 https:// 开头。如果使用了变量，请确保变量已在环境中定义。"
                }

            # 构建步骤
            # RunRequest(name) -> .get(url) -> .with_headers() ...
            req = RunRequest(step.name)
            
            # 设置请求方法和URL
            method_lower = method.lower()
            if hasattr(req, method_lower):
                step_req = getattr(req, method_lower)(url)
            else:
                # 默认 fallback，虽然应该不会发生
                step_req = req.post(url)
            
            # 处理Headers
            if isinstance(headers, list):
                req_headers = {}
                for h in headers:
                    if h.get('enabled', True) and h.get('key'):
                        req_headers[h['key']] = h.get('value', '')
                if req_headers:
                    step_req.with_headers(**req_headers)
            elif isinstance(headers, dict) and headers:
                step_req.with_headers(**headers)
                
            # 处理Params
            if params:
                step_req.with_params(**params)
                
            # 处理Body
            if body and method.upper() in ['POST', 'PUT', 'PATCH']:
                if body.get('type') == 'json':
                    step_req.with_json(body.get('data', {}))
                else:
                    # 对于非JSON body，HttpRunner通常使用data字段
                    step_req.with_data(body.get('data', ''))
            
            # 处理断言
            if assertions:
                validator = step_req.validate()
                for assertion in assertions:
                    a_type = assertion.get('type')
                    expected = assertion.get('expected') or assertion.get('value') or assertion.get('expected_value')
                    
                    if a_type == 'status_code':
                        # 状态码断言
                        try:
                            expected_int = int(expected)
                            validator.assert_equal("status_code", expected_int)
                        except:
                            validator.assert_equal("status_code", expected)
                    elif a_type == 'contains':
                        # 包含断言 - body string contains
                        validator.assert_contains("body", str(expected))
                    elif a_type == 'equals':
                        # 相等断言 - body equals
                        validator.assert_equal("body", expected)
                    elif a_type == 'json_path':
                        path = assertion.get('json_path', '')
                        # 去除可能的 $. 前缀，适配JMESPath
                        if path.startswith('$.'):
                            path = path[2:]
                        elif path.startswith('$'):
                            path = path[1:]
                        
                        if path:
                            validator.assert_equal(path, expected)
                    elif a_type == 'header':
                        h_name = assertion.get('header_name')
                        if h_name:
                            validator.assert_equal(f"headers.{h_name}", expected)
            
            # 处理变量提取
            if extract_rules:
                extractor = step_req.extract()
                for rule in extract_rules:
                    var_name = rule.get('variable_name')
                    json_path = rule.get('json_path', '')
                    
                    # 适配JMESPath
                    if json_path.startswith('$.'):
                        json_path = json_path[2:]
                    elif json_path.startswith('$'):
                        json_path = json_path[1:]
                        
                    if var_name and json_path:
                        extractor.with_jmespath(json_path, var_name)
            
            test_steps.append(Step(step_req))
            
        # 3. 动态创建测试类并执行
        class DynamicTestCase(HttpRunner):
            config = None
            teststeps = []
            
        DynamicTestCase.config = config
        DynamicTestCase.teststeps = test_steps
            
        runner = DynamicTestCase()
        runner.test_start()
        summary = runner.get_summary()
        
        # 4. 转换结果
        passed_count = 0
        failed_count = 0
        results = []
        
        # summary.step_results 是一个列表
        step_results = summary.step_results
        
        for i, step_result in enumerate(step_results):
            # StepResult 对象
            passed = step_result.success
            name = step_result.name
            
            if passed:
                passed_count += 1
            else:
                failed_count += 1
            
            # 提取响应信息
            status_code = 0
            response_time = 0
            error_msg = ""
            
            # data 是 SessionData 对象
            session_data = step_result.data
            if session_data:
                # req_resps 是 List[ReqRespData]
                if session_data.req_resps:
                    last_req_resp = session_data.req_resps[-1]
                    status_code = last_req_resp.response.status_code
                    # elapsed_ms in RequestStat
                    response_time = session_data.stat.elapsed_ms
                
                if not passed:
                    # 尝试获取验证错误信息
                    # validators 是 Dict
                    error_msg = "Validation failed"
                    if session_data.validators:
                        # 简单的将验证结果作为错误信息
                         error_msg = str(session_data.validators)
            
            results.append({
                'step_number': i + 1,
                'name': name,
                'passed': passed,
                'status_code': status_code,
                'response_time': response_time,
                'error': error_msg,
                'assertions_results': [] 
            })
            
        return {
            'success': True,
            'passed_count': passed_count,
            'failed_count': failed_count,
            'total_count': len(test_steps),
            'results': results
        }

    except Exception as e:
        import traceback
        return {
            'success': False,
            'error': f"HttpRunner执行异常: {str(e)}\n{traceback.format_exc()}"
        }


def execute_api_request_httprunner(api_request, environment, executed_by):
    """使用HttpRunner v4执行单个API请求"""
    import os
    import json
    import time
    from django.conf import settings
    from .models import RequestHistory
    
    try:
        from httprunner import HttpRunner, Config, RunRequest, RunTestCase, Step
    except ImportError:
        return {
            'success': False,
            'error': 'HttpRunner未安装，请联系管理员安装httprunner库'
        }

    try:
        # 1. 准备配置
        config = Config("Single Request").base_url("")
        
        # 处理环境变量
        variables = {}
        if environment:
            for k, v in environment.variables.items():
                if isinstance(v, dict):
                    variables[k] = v.get('currentValue', '') or v.get('initialValue', '')
                else:
                    variables[k] = v
            config.variables(**variables)
        
        # 2. 构建步骤
        # RunRequest(name) -> .get(url) -> .with_headers() ...
        req = RunRequest(api_request.name)
        
        # 设置请求方法和URL
        method = api_request.method
        url = api_request.url
        headers = api_request.headers
        params = api_request.params
        body = api_request.body
        assertions = api_request.assertions
        
        # 预处理URL中的变量
        url = _replace_variables(url, variables)
        
        # 检查URL是否包含未替换的变量或非绝对路径
        url_stripped = url.strip()
        if url_stripped.startswith("{{"):
            import re
            var_match = re.match(r'\{\{\s*(.*?)\s*\}\}', url_stripped)
            var_name = var_match.group(1) if var_match else "unknown"
            return {
                'success': False,
                'error': f"API请求 URL配置错误: 变量 '{var_name}' 未在环境中定义或未被替换。当前URL: {url}"
            }
        
        if not (url_stripped.lower().startswith("http://") or url_stripped.lower().startswith("https://")):
             return {
                'success': False,
                'error': f"API请求 URL无效: '{url}'。URL必须以 http:// 或 https:// 开头。如果使用了变量，请确保变量已在环境中定义。"
             }
        
        method_lower = method.lower()
        if hasattr(req, method_lower):
            step_req = getattr(req, method_lower)(url)
        else:
            step_req = req.post(url)
        
        # 处理Headers
        if isinstance(headers, list):
            req_headers = {}
            for h in headers:
                if h.get('enabled', True) and h.get('key'):
                    req_headers[h['key']] = h.get('value', '')
            if req_headers:
                step_req.with_headers(**req_headers)
        elif isinstance(headers, dict) and headers:
            step_req.with_headers(**headers)
            
        # 处理Params
        if params:
            step_req.with_params(**params)
            
        # 处理Body
        if body and method.upper() in ['POST', 'PUT', 'PATCH']:
            if body.get('type') == 'json':
                step_req.with_json(body.get('data', {}))
            else:
                step_req.with_data(body.get('data', ''))
        
        # 处理断言
        if assertions:
            validator = step_req.validate()
            for assertion in assertions:
                a_type = assertion.get('type')
                expected = assertion.get('expected') or assertion.get('value') or assertion.get('expected_value')
                
                if a_type == 'status_code':
                    try:
                        expected_int = int(expected)
                        validator.assert_equal("status_code", expected_int)
                    except:
                        validator.assert_equal("status_code", expected)
                elif a_type == 'contains':
                    validator.assert_contains("body", str(expected))
                elif a_type == 'equals':
                    validator.assert_equal("body", expected)
                elif a_type == 'json_path':
                    path = assertion.get('json_path', '')
                    if path.startswith('$.'):
                        path = path[2:]
                    elif path.startswith('$'):
                        path = path[1:]
                    if path:
                        validator.assert_equal(path, expected)
                elif a_type == 'header':
                    h_name = assertion.get('header_name')
                    if h_name:
                        validator.assert_equal(f"headers.{h_name}", expected)
        
        test_steps = [Step(step_req)]
        
        # 3. 动态创建测试类并执行
        class DynamicTestCase(HttpRunner):
            config = None
            teststeps = []
            
        DynamicTestCase.config = config
        DynamicTestCase.teststeps = test_steps
            
        runner = DynamicTestCase()
        runner.test_start()
        summary = runner.get_summary()
        
        # 4. 转换结果
        step_result = summary.step_results[0]
        passed = step_result.success
        
        status_code = 0
        response_time = 0
        response_headers = {}
        response_body = ""
        response_json = None
        
        session_data = step_result.data
        if session_data:
            if session_data.req_resps:
                last_req_resp = session_data.req_resps[-1]
                status_code = last_req_resp.response.status_code
                response_headers = dict(last_req_resp.response.headers)
                response_body = last_req_resp.response.body
                if isinstance(response_body, bytes):
                    try:
                        response_body = response_body.decode('utf-8')
                    except:
                        response_body = str(response_body)
                
                try:
                    response_json = json.loads(response_body)
                except:
                    pass
                    
                response_time = session_data.stat.elapsed_ms

        # 保存请求历史
        history = RequestHistory.objects.create(
            request=api_request,
            environment=environment,
            request_data={
                'url': url,
                'method': method,
                'headers': headers,
                'params': params,
                'body': body
            },
            response_data={
                'headers': response_headers,
                'body': response_body,
                'json': response_json
            },
            status_code=status_code,
            response_time=response_time,
            assertions_results=[], # HttpRunner断言结果结构不同，暂时留空
            executed_by=executed_by
        )
        
        return {
            'success': True,
            'history_id': history.id,
            'status_code': status_code,
            'response_time': response_time,
            'assertions_results': [],
            'response_data': {
                'headers': response_headers,
                'body': response_body,
                'json': response_json
            }
        }

    except Exception as e:
        import traceback
        return {
            'success': False,
            'error': f"HttpRunner执行异常: {str(e)}\n{traceback.format_exc()}"
        }
