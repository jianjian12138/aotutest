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


def _replace_variables(text, variables):
    """替换文本中的变量，支持环境变量和动态Mock数据(如 {{$faker.name}}, {{$timestamp}})"""
    if not isinstance(text, str):
        return text
    
    import re
    from faker import Faker
    import time
    import uuid
    
    # Initialize Faker instance
    fake = Faker('zh_CN')
    
    result = text
    
    # 1. 替换环境变量 ({{var_name}})
    for key, value in (variables or {}).items():
        if isinstance(value, dict):
            replacement = str(value.get('currentValue', '') or value.get('initialValue', ''))
        else:
            replacement = str(value) if value is not None else ''
        
        # 使用正则替换，支持 {{key}} 和 {{ key }} 格式
        pattern = r'\{\{\s*' + re.escape(key) + r'\s*\}\}'
        result = re.sub(pattern, replacement, result)
        
    # 2. 替换动态数据 ({{$faker.xxx}}, {{$timestamp}}, {{$uuid}})
    def dynamic_replacer(match):
        var_name = match.group(1).strip()
        
        if var_name == '$timestamp':
            return str(int(time.time() * 1000))
        elif var_name == '$uuid':
            return str(uuid.uuid4())
            
        elif var_name.startswith('$faker.'):
            # Extract faker method name
            faker_method = var_name[7:]
            if hasattr(fake, faker_method):
                try:
                    # Execute the faker method
                    method = getattr(fake, faker_method)
                    return str(method())
                except Exception as e:
                    logger.warning(f"Error generating faker data for {faker_method}: {str(e)}")
                    return match.group(0) # Return original tag on error
            else:
                return match.group(0)
                
        elif var_name.startswith('$pool.'):
            # {{$pool.pool_name.field_name}}
            parts = var_name.split('.')
            if len(parts) >= 3:
                pool_name = parts[1]
                field_name = parts[2]
                try:
                    from apps.data_factory.models import DataPool
                    pool = DataPool.objects.filter(name=pool_name).first()
                    if pool and pool.data and len(pool.data) > 0:
                        import random
                        row = random.choice(pool.data)
                        return str(row.get(field_name, match.group(0)))
                    else:
                        return match.group(0)
                except Exception as e:
                    logger.warning(f"Error extracting data from DataPool {var_name}: {str(e)}")
                    return match.group(0)
                
        return match.group(0) # Non-matching dynamic tag
        
    # Match any variable starting with $ inside {{ }}
    dynamic_pattern = r'\{\{\s*(\$[a-zA-Z0-9_\.]+)\s*\}\}'
    result = re.sub(dynamic_pattern, dynamic_replacer, result)

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


