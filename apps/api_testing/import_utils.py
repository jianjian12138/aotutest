import json
import yaml
import logging

logger = logging.getLogger(__name__)

def parse_openapi_spec(file_content):
    """
    解析 OpenAPI/Swagger 规范
    返回包含项目名称、描述和 API 请求列表的字典
    """
    try:
        if isinstance(file_content, bytes):
            file_content = file_content.decode('utf-8')
            
        try:
            data = json.loads(file_content)
        except json.JSONDecodeError:
            data = yaml.safe_load(file_content)
            
        if not data:
            return None
            
        info = data.get('info', {})
        project_name = info.get('title', '已导入项目')
        description = info.get('description', f"从 OpenAPI 导入: {project_name}")
        
        paths = data.get('paths', {})
        components = data.get('components', {})
        schemas = components.get('schemas', {})
        
        api_requests = []
        
        for path, path_item in paths.items():
            # 某些规范中可能有参数在路径级别
            path_params = path_item.get('parameters', [])
            
            for method, operation in path_item.items():
                if method.lower() not in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']:
                    continue
                
                name = operation.get('summary') or operation.get('operationId') or f"{method.upper()} {path}"
                tags = operation.get('tags', ['默认集合'])
                tag = tags[0] if tags else '默认集合'
                
                # 合并路径级别和操作级别的参数
                all_params = path_params + operation.get('parameters', [])
                
                headers = []
                query_params = {}
                
                for param in all_params:
                    # 某些参数可能是引用
                    if '$ref' in param:
                        # 简单处理，暂不深入解析引用，除非必要
                        continue
                        
                    p_in = param.get('in')
                    p_name = param.get('name')
                    p_desc = param.get('description', '')
                    
                    if p_in == 'header':
                        headers.append({
                            'key': p_name,
                            'value': _get_example_value(param),
                            'description': p_desc,
                            'enabled': True
                        })
                    elif p_in == 'query':
                        query_params[p_name] = _get_example_value(param)
                
                # 处理 Request Body
                body = {'type': 'none', 'data': ''}
                request_body = operation.get('requestBody', {})
                if request_body:
                    content = request_body.get('content', {})
                    if 'application/json' in content:
                        body['type'] = 'json'
                        schema = content['application/json'].get('schema', {})
                        # 尝试从 schema 生成示例
                        body['data'] = _generate_example_from_schema(schema, schemas)
                    elif 'application/x-www-form-urlencoded' in content:
                        body['type'] = 'form-data'
                        # 简化处理
                        body['data'] = ""
                
                api_requests.append({
                    'name': name,
                    'tag': tag,
                    'url': f"{{{{url}}}}{path}",
                    'method': method.upper(),
                    'description': operation.get('description', ''),
                    'headers': headers,
                    'params': query_params,
                    'body': body
                })
                
        return {
            'project_name': project_name,
            'description': description,
            'requests': api_requests
        }
    except Exception as e:
        logger.error(f"OpenAPI 解析失败: {str(e)}", exc_info=True)
        return None

def _get_example_value(param):
    """从参数中提取示例值"""
    if 'example' in param:
        return str(param['example'])
    if 'default' in param:
        return str(param['default'])
    
    schema = param.get('schema', {})
    if 'example' in schema:
        return str(schema['example'])
    if 'default' in schema:
        return str(schema['default'])
        
    # 根据类型返回占位符
    p_type = schema.get('type', 'string')
    if p_type == 'integer' or p_type == 'number':
        return "0"
    if p_type == 'boolean':
        return "true"
    return "string"

def _generate_example_from_schema(schema, all_schemas):
    """根据 Schema 生成 JSON 示例"""
    if not schema:
        return ""
        
    try:
        # 简单处理常见模式
        if '$ref' in schema:
            ref_name = schema['$ref'].split('/')[-1]
            if ref_name in all_schemas:
                return _generate_example_from_schema(all_schemas[ref_name], all_schemas)
            return {}
            
        s_type = schema.get('type')
        if s_type == 'object':
            example = {}
            properties = schema.get('properties', {})
            for p_name, p_schema in properties.items():
                example[p_name] = _generate_example_from_schema(p_schema, all_schemas)
            return example
        elif s_type == 'array':
            items = schema.get('items', {})
            return [_generate_example_from_schema(items, all_schemas)]
        else:
            if 'example' in schema:
                return schema['example']
            if 'default' in schema:
                return schema['default']
            
            if s_type == 'integer' or s_type == 'number':
                return 0
            if s_type == 'boolean':
                return True
            return "string"
    except:
        return ""
