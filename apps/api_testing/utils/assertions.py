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
                        # 安全防线：数据库断言仅允许只读查询，禁止写操作/多语句
                        from backend.utils.sql_guard import (
                            SQLGuardError, validate_readonly, enforce_limit,
                        )
                        try:
                            validate_readonly(generated_sql)
                            generated_sql = enforce_limit(generated_sql, max_rows=500)
                        except SQLGuardError as guard_err:
                            raise ValueError(f"数据库断言 SQL 校验未通过: {guard_err}")

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
                            password=config.get_db_password() or '',
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
                                    except Exception:
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


