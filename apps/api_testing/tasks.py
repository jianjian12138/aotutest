"""
API导入的Celery异步任务
"""
import logging
import json
import yaml
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from apps.api_testing.models import ApiProject, ApiCollection, ApiRequest, ApiImportTask
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()

@shared_task(bind=True)
def import_api_data_task(self, project_id, file_content, file_format, import_mode, user_id, task_id=None):
    """
    异步导入API数据任务
    
    :param self: Celery任务实例
    :param project_id: 项目ID
    :param file_content: 文件内容
    :param file_format: 文件格式 (postman/apifox/jmeter/swagger)
    :param import_mode: 导入模式 (overwrite/append)
    :param user_id: 用户ID
    :param task_id: 导入任务ID
    """
    try:
        logger.info(f"开始导入API数据: 项目ID={project_id}, 格式={file_format}, 模式={import_mode}")
        
        # 获取用户和项目
        user = User.objects.get(id=user_id)
        project = ApiProject.objects.get(id=project_id)
        
        # 更新任务状态为运行中
        if task_id:
            import_task = ApiImportTask.objects.get(id=task_id)
            import_task.status = 'running'
            import_task.save()
        
        # 根据格式选择导入方法
        if file_format in ['postman', 'postman-collection']:
            imported_data = _import_postman_data(file_content, project, user)
        elif file_format == 'apifox':
            imported_data = _import_apifox_data(file_content, project, user)
        elif file_format in ['jmeter', 'jmx']:
            imported_data = _import_jmeter_data(file_content, project, user)
        elif file_format in ['swagger', 'openapi']:
            imported_data = _import_swagger_data(file_content, project, user)
        else:
            raise ValueError(f"不支持的导入格式: {file_format}")
        
        # 更新任务状态为成功
        if task_id:
            import_task = ApiImportTask.objects.get(id=task_id)
            import_task.status = 'success'
            import_task.imported_count = imported_data['requests']
            import_task.total_count = imported_data['requests']
            import_task.completed_at = timezone.now()
            import_task.save()
        
        logger.info(f"API数据导入成功: 项目ID={project_id}, 导入集合数={imported_data['collections']}, 导入请求数={imported_data['requests']}")
        return {
            'status': 'success',
            'message': f'API数据导入成功，共导入 {imported_data["collections"]} 个集合，{imported_data["requests"]} 个请求',
            'project_id': project_id
        }
        
    except Exception as e:
        logger.error(f"API数据导入失败: 项目ID={project_id}, 错误={str(e)}", exc_info=True)
        
        # 更新任务状态为失败
        if task_id:
            import_task = ApiImportTask.objects.get(id=task_id)
            import_task.status = 'failed'
            import_task.error_message = str(e)
            import_task.completed_at = timezone.now()
            import_task.save()
        
        return {
            'status': 'failed',
            'message': f'API数据导入失败: {str(e)}',
            'project_id': project_id
        }

def _import_postman_data(file_content, project, user):
    """
    导入Postman数据 - 优化版本，提高处理大型文件的效率
    """
    try:
        data = json.loads(file_content)
        collections_created = 0
        requests_created = 0
        
        # 先获取现有集合的数量，用于设置order值
        def get_initial_order(parent_collection):
            """获取初始order值，避免频繁查询数据库"""
            return ApiCollection.objects.filter(
                project=project, 
                parent=parent_collection
            ).count()
        
        # 使用非递归方式处理，避免栈溢出，提高处理效率
        def process_items(items, parent_collection=None):
            """非递归处理Postman文件项"""
            nonlocal collections_created, requests_created
            
            # 获取当前父集合下的初始order值
            initial_order = get_initial_order(parent_collection)
            
            # 存储当前层级需要创建的集合和请求
            current_collections = []
            
            # 第一次遍历：创建所有集合
            for i, item in enumerate(items):
                if isinstance(item, dict):
                    if 'item' in item:  # 这是一个文件夹/集合
                        # 创建集合，order值为初始值+索引
                        collection = ApiCollection.objects.create(
                            project=project,
                            name=item.get('name', '未命名集合'),
                            description=item.get('description', ''),
                            parent=parent_collection,
                            order=initial_order + i
                        )
                        collections_created += 1
                        current_collections.append((collection, item))
            
            # 第二次遍历：处理请求和递归处理子集合
            for collection, item in current_collections:
                # 处理当前集合下的请求
                for sub_item in item['item']:
                    if isinstance(sub_item, dict):
                        if 'request' in sub_item:  # 这是一个请求
                            # 解析请求
                            request_data = sub_item['request']
                            method = request_data.get('method', 'GET')
                            url = ''
                            
                            # 处理URL
                            url_obj = request_data.get('url', {})
                            if isinstance(url_obj, dict):
                                # 构建URL
                                protocol = url_obj.get('protocol', 'http')
                                host = url_obj.get('host', [])
                                if isinstance(host, list):
                                    host = '.'.join(host)
                                path = url_obj.get('path', [])
                                if isinstance(path, list):
                                    path = '/'.join(path)
                                
                                url = f"{protocol}://{host}/{path.lstrip('/')}"
                                
                                # 处理查询参数
                                params = {}
                                for param in url_obj.get('query', []):
                                    if param.get('key'):
                                        params[param['key']] = param.get('value', '')
                            else:
                                url = url_obj
                                params = {}
                            
                            # 解析请求头
                            headers = []
                            for header in request_data.get('header', []):
                                if header.get('key') and not header.get('disabled', False):
                                    headers.append({
                                        'key': header['key'],
                                        'value': header.get('value', ''),
                                        'description': header.get('description', ''),
                                        'enabled': True
                                    })
                            
                            # 解析请求体
                            body = {}
                            if request_data.get('body'):
                                body_type = request_data['body'].get('mode', 'raw')
                                if body_type == 'raw':
                                    body = {
                                        'type': 'json' if request_data['body'].get('raw') else 'raw',
                                        'data': request_data['body'].get('raw') or ''
                                    }
                                else:
                                    body = {'type': 'raw', 'data': ''}
                            
                            # 创建请求
                            ApiRequest.objects.create(
                                collection=collection,
                                name=sub_item.get('name', '未命名请求'),
                                description=sub_item.get('description', ''),
                                method=method,
                                url=url,
                                headers=headers,
                                params=params,
                                body=body,
                                created_by=user,
                                order=requests_created
                            )
                            requests_created += 1
                        elif 'item' in sub_item:  # 子集合
                            # 递归处理子集合
                            process_items([sub_item], collection)
        
        # 开始处理数据
        if 'item' in data:  # 标准的Postman集合结构
            # 使用事务确保原子性
            with transaction.atomic():
                process_items(data['item'])
        elif 'request' in data:  # 单个请求情况
            # 创建默认集合
            default_collection = ApiCollection.objects.create(
                project=project,
                name='默认集合',
                description='导入生成的默认集合',
                parent=None,
                order=get_initial_order(None)
            )
            collections_created += 1
            
            # 处理单个请求
            with transaction.atomic():
                process_items([data], default_collection)
        else:
            # 未知结构，返回错误
            raise ValueError(f"未知的Postman数据结构: {list(data.keys())}")
        
        return {
            'collections': collections_created,
            'requests': requests_created
        }
    except Exception as e:
        logger.error(f"解析Postman数据失败: {str(e)}", exc_info=True)
        raise

def _import_apifox_data(file_content, project, user):
    """
    导入Apifox数据
    Apifox数据格式与Postman类似，可以复用Postman的导入逻辑
    """
    return _import_postman_data(file_content, project, user)

def _import_jmeter_data(file_content, project, user):
    """
    导入JMeter数据
    """
    try:
        from xml.etree import ElementTree as ET
        
        root = ET.fromstring(file_content)
        collections = []
        requests = []
        
        # 创建JMeter集合
        jmeter_collection = ApiCollection.objects.create(
            project=project,
            name='JMeter导入集合',
            description='从JMeter导入的接口集合',
            order=ApiCollection.objects.filter(project=project).count()
        )
        collections.append(jmeter_collection)
        
        # 解析HTTP请求采样器
        for http_sampler in root.findall('.//HTTPSamplerProxy'):
            name = http_sampler.findtext('.//stringProp[@name="HTTPSamplerProxy.name"]', '未命名请求')
            method = http_sampler.findtext('.//stringProp[@name="HTTPSamplerProxy.method"]', 'GET')
            
            # 解析URL相关信息
            protocol = http_sampler.findtext('.//stringProp[@name="HTTPSampler.protocol"]', 'http')
            domain = http_sampler.findtext('.//stringProp[@name="HTTPSampler.domain"]', '')
            port = http_sampler.findtext('.//stringProp[@name="HTTPSampler.port"]', '')
            path = http_sampler.findtext('.//stringProp[@name="HTTPSampler.path"]', '')
            
            url = f"{protocol}://{domain}"
            if port:
                url += f":{port}"
            url += path
            
            # 创建API请求
            api_request = ApiRequest.objects.create(
                collection=jmeter_collection,
                name=name,
                description='从JMeter导入',
                method=method,
                url=url,
                headers=[],
                params={},
                body={},
                created_by=user,
                order=ApiRequest.objects.filter(collection=jmeter_collection).count()
            )
            requests.append(api_request)
        
        return {
            'collections': len(collections),
            'requests': len(requests)
        }
    except Exception as e:
        logger.error(f"解析JMeter数据失败: {str(e)}", exc_info=True)
        raise

def _import_swagger_data(file_content, project, user):
    """
    导入Swagger/OpenAPI数据 - 优化版本，使用批量操作
    """
    try:
        # 处理JSON格式的Swagger数据
        try:
            data = json.loads(file_content)
        except json.JSONDecodeError:
            # 尝试解析YAML格式
            data = yaml.safe_load(file_content)
        
        # 解析Swagger数据
        paths = data.get('paths', {})
        
        # 收集所有需要创建的集合
        tag_set = set()
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                tags = operation.get('tags', [])
                tag_set.update(tags)
        
        # 创建集合映射
        tag_collections = {}
        collections_to_create = []
        
        # 收集需要创建的集合
        for tag in tag_set:
            collections_to_create.append({
                'name': tag,
                'description': f'{tag}相关接口',
                'project': project,
                'parent': None
            })
        
        # 添加默认集合
        collections_to_create.append({
            'name': '默认集合',
            'description': '未分类接口',
            'project': project,
            'parent': None
        })
        
        # 批量创建集合
        created_collections = []
        with transaction.atomic():
            for i, coll_data in enumerate(collections_to_create):
                coll = ApiCollection.objects.create(
                    project=coll_data['project'],
                    name=coll_data['name'],
                    description=coll_data['description'],
                    parent=coll_data['parent'],
                    order=i
                )
                created_collections.append(coll)
                
                # 构建标签到集合的映射
                if coll.name != '默认集合':
                    tag_collections[coll.name] = coll
        
        # 获取默认集合
        default_collection = next(coll for coll in created_collections if coll.name == '默认集合')
        
        # 收集所有需要创建的请求
        requests_to_create = []
        
        # 遍历所有路径和请求
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                tags = operation.get('tags', [])
                collection = tag_collections.get(tags[0]) if tags else default_collection
                
                # 收集请求数据
                requests_to_create.append({
                    'collection': collection,
                    'name': operation.get('summary', operation.get('operationId', path)),
                    'description': operation.get('description', ''),
                    'method': method.upper(),
                    'url': f"{{base_url}}{path}",
                    'headers': [],
                    'params': {},
                    'body': {},
                    'created_by': user,
                    'order': len(requests_to_create)  # 临时order
                })
        
        # 批量创建请求
        with transaction.atomic():
            for req_data in requests_to_create:
                ApiRequest.objects.create(**req_data)
        
        return {
            'collections': len(created_collections),
            'requests': len(requests_to_create)
        }
    except Exception as e:
        logger.error(f"解析Swagger数据失败: {str(e)}", exc_info=True)
        raise
