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
from .variables import _replace_variables
def execute_test_case_httprunner(test_case, environment, executed_by):
    """使用HttpRunner v4执行测试用例"""
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
                        except Exception:
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
                    except Exception:
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
        step_result.success
        
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
                    except Exception:
                        response_body = str(response_body)
                
                try:
                    response_json = json.loads(response_body)
                except Exception:
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


