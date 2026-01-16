import json
import time
from django.utils import timezone
from .models import RequestHistory


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
                passed = actual == expected
                
            elif assertion_type == 'response_time':
                # 响应时间断言在调用方处理
                actual = assertion.get('actual_time')
                passed = actual <= expected if actual else False
                
            elif assertion_type == 'contains':
                text = response.text or ''
                pattern = str(expected)
                actual = text[:200] + '...' if len(text) > 200 else text
                passed = pattern in str(text)
                
            elif assertion_type == 'json_path':
                json_path = assertion.get('json_path', '')
                expected_value = assertion.get('expected')
                actual = None
                passed = False
                
                try:
                    # 检查响应是否为JSON格式
                    content_type = response.headers.get('content-type', '').lower()
                    if 'application/json' not in content_type:
                        raise ValueError(f"响应不是JSON格式，Content-Type: {content_type}")
                    
                    response_json = json.loads(response.text)
                    
                    # 检查JSONPath表达式是否为空
                    if not json_path:
                        raise ValueError("JSON路径表达式不能为空")
                    
                    from jsonpath_ng import parse
                    matches = parse(json_path).find(response_json)
                    actual = matches[0].value if matches else None
                    passed = str(actual) == str(expected_value)
                    
                    # 确保actual值被正确设置到result中
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
    
    result = text
    for key, value in (variables or {}).items():
        if isinstance(value, dict):
            replacement = str(value.get('currentValue', '') or value.get('initialValue', ''))
        else:
            replacement = str(value) if value is not None else ''
        result = result.replace(f'{{{{{key}}}}}', replacement)
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
