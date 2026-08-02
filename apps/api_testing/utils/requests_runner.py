from apps.notifications.models import NotificationConfig, NotificationLog
import ast
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
from .variables import _replace_variables, extract_variables, _replace_variables_in_dict
from .assertions import execute_assertions
from .reports import generate_allure_report

import re

logger = logging.getLogger(__name__)

# 请求超时与响应体体积上限（WS4 门禁：防止无限等待与内存膨胀）
HTTP_REQUEST_TIMEOUT = 30                # 秒
MAX_RESPONSE_BYTES = 5 * 1024 * 1024    # 5 MB


class SandboxSecurityError(Exception):
    """前置/后置脚本沙箱校验失败：脚本尝试执行被禁止的操作（如 RCE 逃逸、import、危险调用）。"""
    pass


# 沙箱可直接调用的内建/对象名白名单（脚本只能调用这些）。
_ALLOWED_CALL_NAMES = {
    'print', 'len', 'str', 'int', 'float', 'bool', 'list', 'dict', 'tuple', 'set',
    'range', 'enumerate', 'zip', 'min', 'max', 'sum', 'abs', 'sorted',
    'isinstance', 'type', 'round', 'format', 'hex', 'bin', 'ord', 'chr',
    # 注入对象（作占位以避免 NameError；实际多为属性/方法调用）
    'log', 're', 'json', 'variables',
}

# 危险名：即便作为普通 Name 出现也禁止（防止 eval/exec/open/__import__ 等入口）。
_DANGEROUS_NAMES = {
    'eval', 'exec', 'compile', 'open', '__import__', 'input', 'exit', 'quit',
    'globals', 'locals', 'vars', 'getattr', 'setattr', 'delattr',
    'breakpoint', 'memoryview',
}

# 白名单对象的允许方法（用于属性/方法调用校验）。
_WHITELIST_ATTR_METHODS = {
    're': {'search', 'match', 'findall', 'sub', 'split', 'compile'},
    'json': {'loads', 'dumps'},
    'variables': {'get', 'setdefault', 'update'},
}


def _validate_fixture_script(tree_or_text):
    """AST 白名单校验：拒绝 import / dunder 属性链 / 危险名 / 越权调用等。

    通过抛 ``SandboxSecurityError`` 阻断任何可能逃逸沙箱（RCE）或访问文件/网络的脚本。
    双重防御：即便 exec 的 ``__builtins__`` 已清空，仍在此处静态拦截危险结构。
    """
    if isinstance(tree_or_text, str):
        tree = ast.parse(tree_or_text)
    else:
        tree = tree_or_text

    for node in ast.walk(tree):
        # 1) 禁止任何 import
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise SandboxSecurityError("禁止 import 语句")

        # 2) 禁止 dunder 属性链（覆盖 __class__/__base__/__subclasses__/__globals__ 等 RCE 向量）
        if isinstance(node, ast.Attribute):
            if node.attr.startswith('__') and node.attr.endswith('__'):
                raise SandboxSecurityError(f"禁止访问 dunder 属性: {node.attr}")
            # 仅允许白名单对象(re/json/variables)的授权属性/方法；
            # 非 Name 值（如方法链结果 Match.group）放行——dunder 已拦且运行期无可达危险对象。
            if isinstance(node.value, ast.Name):
                obj = node.value.id
                if obj in _WHITELIST_ATTR_METHODS:
                    if node.attr not in _WHITELIST_ATTR_METHODS[obj]:
                        raise SandboxSecurityError(f"禁止访问 {obj} 的未授权方法: {node.attr}")
                else:
                    # 非白名单对象的属性访问（obj.foo）一律拒绝
                    raise SandboxSecurityError(f"禁止访问非白名单对象属性: {obj}.{node.attr}")
            # node.value 为 Call/Constant 等非 Name 形式时放行

        # 3) 危险 Name
        if isinstance(node, ast.Name) and node.id in _DANGEROUS_NAMES:
            raise SandboxSecurityError(f"禁止使用的名称: {node.id}")

        # 4) 调用校验
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                if func.id not in _ALLOWED_CALL_NAMES:
                    raise SandboxSecurityError(f"禁止调用未授权函数: {func.id}")
            elif isinstance(func, ast.Attribute):
                if func.attr.startswith('__') and func.attr.endswith('__'):
                    raise SandboxSecurityError(f"禁止调用 dunder 方法: {func.attr}")
                if isinstance(func.value, ast.Name) and func.value.id in _WHITELIST_ATTR_METHODS:
                    if func.attr not in _WHITELIST_ATTR_METHODS[func.value.id]:
                        raise SandboxSecurityError(
                            f"禁止调用 {func.value.id} 的未授权方法: {func.attr}")
                # func.value 非 Name（方法链结果）放行
            else:
                # 其他调用形式（如函数调用结果再调用）一律禁止
                raise SandboxSecurityError("禁止的函数调用形式")

        # 5) 作用域/并发危险结构
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            raise SandboxSecurityError("禁止 global/nonlocal 语句")
        if isinstance(node, (ast.Yield, ast.YieldFrom, ast.Await,
                              ast.AsyncFunctionDef, ast.AsyncWith, ast.AsyncFor)):
            raise SandboxSecurityError("禁止 yield/await/异步结构")
        if isinstance(node, ast.ClassDef):
            raise SandboxSecurityError("禁止类定义")

        # 6) 裸 except（必须指定异常类型，避免静默吞掉一切）
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            raise SandboxSecurityError("禁止裸 except:（必须指定异常类型）")

    return True


def _run_fixture_script(script_text, variables, label="fixture-script"):
    """在受限沙箱中执行用例 fixture 的前后置脚本（pre/post_request_script）。

    脚本以 Python 运行，但仅暴露一组受控内建（无文件/网络/ subprocess 等危险能力），
    可读写 ``variables`` 变量池以便向前置/后置逻辑注入数据。
    返回 ``(success, updated_variables, error)``：
    - success=False 表示脚本抛错（setup 失败，调用方应中止该用例）。
    """
    if not script_text or not script_text.strip():
        return True, variables, None

    # 第一层防御：先编译（捕获语法错误），再 AST 静态白名单校验（拦截 RCE 逃逸等）。
    try:
        compiled = compile(script_text, f"<{label}>", "exec")
    except SyntaxError as e:
        logger.error("fixture 脚本语法错误 [%s]: %s", label, e)
        return False, None, f"语法错误: {e}"

    try:
        tree = ast.parse(script_text)
        _validate_fixture_script(tree)
    except SandboxSecurityError as e:
        logger.error("fixture 脚本安全校验未通过 [%s]: %s", label, e)
        return False, None, f"安全校验未通过: {e}"

    # 第二层防御：执行环境彻底清空 __builtins__，仅注入白名单内建与 helper；
    # 文件/网络/subprocess 等入口一律不存在（连 __import__/open/eval 都不可用）。
    _safe = {
        'print': print, 'len': len, 'str': str, 'int': int, 'float': float,
        'bool': bool, 'list': list, 'dict': dict, 'tuple': tuple, 'set': set,
        'range': range, 'enumerate': enumerate, 'zip': zip, 'min': min,
        'max': max, 'sum': sum, 'abs': abs, 'sorted': sorted,
        'isinstance': isinstance, 'type': type, 'round': round, 'format': format,
        'hex': hex, 'bin': bin, 'ord': ord, 'chr': chr,
        're': re, 'json': json,
        'variables': dict(variables or {}),
        'log': lambda msg: logger.info("[fixture %s] %s", label, msg),
        # 常用异常，便于 except 捕获（不含 os/subprocess 等危险入口）
        'Exception': Exception, 'ValueError': ValueError, 'KeyError': KeyError,
        'TypeError': TypeError, 'IndexError': IndexError,
        'AttributeError': AttributeError, 'RuntimeError': RuntimeError,
    }
    sandbox = {'__builtins__': {}, **_safe}
    try:
        exec(compiled, sandbox)  # noqa: S102 - AST 白名单 + 空 builtins 双重防御沙箱
        return True, sandbox.get('variables', {}), None
    except Exception as e:  # 脚本异常 = setup 失败
        logger.error("fixture 脚本执行失败 [%s]: %s", label, e)
        return False, None, str(e)


class _CappedResponse:
    """对 requests.Response 的薄包装：对 .text 施加 5MB 体积上限并打日志，避免超大响应撑爆内存。

    注意：本包装仅用于"已下载到内存"的响应做上限截断展示/断言。真正的下载应使用
    ``stream=True`` + 逐块累加，并在累计超过 ``MAX_RESPONSE_BYTES`` 时主动中断连接，
    从源头避免大响应进入内存（见 requests_runner 内 requests 调用处的 stream 改造范围）。
    """

    def __init__(self, response, max_bytes=MAX_RESPONSE_BYTES):
        self._resp = response
        self.status_code = response.status_code
        self.headers = response.headers
        self._max = max_bytes
        self._text = None

    @property
    def text(self):
        if self._text is None:
            raw = self._resp.text
            size = len(self._resp.content)
            if size > self._max:
                logger.warning(
                    "响应体 %d 字节超过上限 %d，已截断（仅影响断言/存储，不影响状态码）",
                    size, self._max,
                )
                self._text = raw[:self._max] + f"...[truncated, total {size} bytes]"
            else:
                self._text = raw
        return self._text

    def json(self):
        """解析 JSON：改用已做 5MB 上限截断的 ``self.text``，使上限对 JSON 同样生效。

        若响应被截断导致非法 JSON，``json.loads`` 抛 ``json.JSONDecodeError``，由调用方处理（不静默）。
        """
        return json.loads(self.text)


def _run_regex_assertion(response, assertion):
    """regex 断言类型：判断响应文本是否匹配给定正则表达式。"""
    name = assertion.get('name', 'regex')
    pattern = assertion.get('expected') or assertion.get('pattern') or ''
    operator = assertion.get('operator', 'matches')  # matches | not_matches
    flags = re.IGNORECASE if assertion.get('ignorecase') else 0
    result = {
        'name': name, 'type': 'regex',
        'expected': pattern, 'actual': None, 'passed': False, 'error': None,
    }
    try:
        compiled = re.compile(pattern, flags)
        text = response.text or ''
        result['actual'] = text[:200] + ('...' if len(text) > 200 else '')
        matched = bool(compiled.search(text))
        result['passed'] = matched if operator != 'not_matches' else not matched
        if not result['passed']:
            result['error'] = '正则未匹配' if operator != 'not_matches' else '正则意外匹配'
    except re.error as e:
        result['error'] = f"正则编译错误: {e}"
    return result


def _execute_assertions_with_regex(response, assertions):
    """执行断言：内置类型委托给 execute_assertions，regex 类型就近处理。"""
    regex_assertions = [a for a in (assertions or []) if a.get('type') == 'regex']
    other_assertions = [a for a in (assertions or []) if a.get('type') != 'regex']
    results = execute_assertions(response, other_assertions)
    for a in regex_assertions:
        results.append(_run_regex_assertion(response, a))
    return results

def execute_test_case(test_case, environment, executed_by, create_report=True, context_variables=None):
    """执行测试用例并返回结果"""
    import requests
    from ..models import RequestHistory
    
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

        # === 用例级 setup：运行 TestCase.pre_request_script（失败则中止整个用例）===
        aborted = False
        case_setup = getattr(test_case, 'pre_request_script', '') or ''
        if case_setup.strip():
            ok, new_vars, err = _run_fixture_script(
                case_setup, variables, label=f"case-setup:{getattr(test_case, 'name', '?')}"
            )
            if not ok:
                logger.error("用例 setup 脚本失败，中止执行：%s", err)
                execution_time = (time.time() - start_execution_time) * 1000
                ApiTestCaseExecution.objects.create(
                    test_case=test_case,
                    status='failed',
                    total_steps=total_count,
                    passed_steps=0,
                    failed_steps=total_count,
                    results=[{'step_number': 0, 'name': '(setup)', 'passed': False,
                              'error': f'setup failed: {err}'}],
                    execution_time=execution_time,
                    executed_by=executed_by,
                )
                return {
                    'success': False,
                    'status': 'failed',
                    'error': f'setup failed: {err}',
                    'passed_steps': 0,
                    'failed_steps': total_count,
                    'total_steps': total_count,
                    'execution_time': execution_time,
                    'results': [{'step_number': 0, 'name': '(setup)', 'passed': False,
                                 'error': f'setup failed: {err}'}],
                }
            if new_vars:
                variables.update(new_vars)

        # 执行每个步骤
        for step in steps:
            try:
                # === 步骤级 setup：运行 Step.pre_request_script（失败则中止该用例）===
                step_setup = getattr(step, 'pre_request_script', '') or ''
                if step_setup.strip():
                    ok, new_vars, err = _run_fixture_script(
                        step_setup, variables, label=f"step-setup:{step.name}"
                    )
                    if not ok:
                        failed_count += 1
                        results.append({
                            'step_number': step.step_number,
                            'name': step.name,
                            'passed': False,
                            'error': f'pre_request_script failed: {err}',
                        })
                        aborted = True
                        break
                    if new_vars:
                        variables.update(new_vars)

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
                raw_response = requests.request(
                    method=method,
                    url=url,
                    headers=req_headers,
                    params=req_params,
                    json=req_body_data if body and body.get('type') == 'json' else None,
                    data=req_body_data if body and body.get('type') != 'json' else None,
                    timeout=HTTP_REQUEST_TIMEOUT
                )
                # 施加响应体体积上限（截断 + 日志），避免超大响应撑爆内存
                response = _CappedResponse(raw_response, MAX_RESPONSE_BYTES)
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                
                # 执行断言验证
                assertions = step.assertions or []
                # 如果引用了API请求，也包含API请求的断言? 通常步骤定义的断言会覆盖或补充
                # 这里我们假设步骤定义的断言是最终的
                
                for assertion in assertions:
                    if assertion.get('type') == 'response_time':
                        assertion['actual_time'] = response_time
                
                assertions_results = _execute_assertions_with_regex(response, assertions)
                
                # 提取变量
                extracted_vars = {}
                if step.extract_rules:
                    extracted_vars = extract_variables(response, step.extract_rules)
                    variables.update(extracted_vars)

                # === 步骤级 teardown：运行 Step.post_request_script（失败仅记录，不影响用例结果）===
                step_teardown = getattr(step, 'post_request_script', '') or ''
                if step_teardown.strip():
                    _run_fixture_script(step_teardown, variables, label=f"step-teardown:{step.name}")

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
        
        # === 用例级 teardown：运行 TestCase.post_request_script（setup 失败时跳过）===
        if not aborted:
            case_teardown = getattr(test_case, 'post_request_script', '') or ''
            if case_teardown.strip():
                _run_fixture_script(
                    case_teardown, variables, label=f"case-teardown:{getattr(test_case, 'name', '?')}"
                )

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
        except Exception:
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
        
        # === 请求前脚本（ApiRequest.pre_request_script）===
        api_pre = getattr(api_request, 'pre_request_script', '') or ''
        if api_pre.strip():
            ok, new_vars, err = _run_fixture_script(api_pre, variables, label=f"api-pre:{api_request.name}")
            if ok and new_vars:
                variables.update(new_vars)
            elif not ok:
                logger.warning("ApiRequest 前脚本失败（不中止单次请求）：%s", err)

        # 执行请求
        start_time = time.time()
        raw_response = requests.request(
            method=api_request.method,
            url=url,
            headers=headers,
            params=params,
            json=body_data,
            timeout=HTTP_REQUEST_TIMEOUT
        )
        response = _CappedResponse(raw_response, MAX_RESPONSE_BYTES)
        end_time = time.time()

        # === 请求后脚本（ApiRequest.post_request_script）===
        api_post = getattr(api_request, 'post_request_script', '') or ''
        if api_post.strip():
            _run_fixture_script(api_post, variables, label=f"api-post:{api_request.name}")
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


