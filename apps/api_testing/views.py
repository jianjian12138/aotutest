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

from .models import (
    ApiProject, ApiCollection, ApiRequest, Environment,
    RequestHistory, TestSuite, TestExecution, TestSuiteRequest,
    ScheduledTask, TaskExecutionLog, NotificationConfig, NotificationLog,
    TaskNotificationSetting, OperationLog, ApiImportTask,
    ApiTestCase, ApiTestCaseStep, ApiTestCaseExecution, TestSuiteTestCase
)
from apps.configuration.models import GlobalParameter

from .serializers import (
    ApiProjectSerializer, ApiCollectionSerializer, ApiRequestSerializer,
    ApiTestCaseSerializer, ApiTestCaseStepSerializer, ApiTestCaseExecutionSerializer,
    TestSuiteTestCaseSerializer,
    EnvironmentSerializer, RequestHistorySerializer, TestSuiteSerializer,
    TestSuiteRequestSerializer, TestExecutionSerializer, UserSerializer,
    ScheduledTaskSerializer, TaskExecutionLogSerializer,
    NotificationConfigSerializer, NotificationLogSerializer, TaskNotificationSettingSerializer,
    NotificationConfigDetailSerializer, NotificationLogDetailSerializer,
    TaskNotificationSettingDetailSerializer, OperationLogSerializer
)

logger = logging.getLogger(__name__)

from .utils import execute_assertions, execute_test_case
from .operation_logger import log_operation

User = get_user_model()


from rest_framework.pagination import PageNumberPagination

class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 1000


class ApiProjectViewSet(viewsets.ModelViewSet):
    queryset = ApiProject.objects.all()
    serializer_class = ApiProjectSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project_type', 'status', 'owner']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name', 'start_date']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        return ApiProject.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
    
    def create(self, request, *args, **kwargs):
        """创建项目，添加详细日志和错误处理"""
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"ApiProjectViewSet.create: request.data={request.data}")
        
        try:
            # 创建序列化器实例
            serializer = self.get_serializer(data=request.data)
            logger.debug(f"ApiProjectViewSet.create: serializer={serializer}")
            
            # 验证数据
            if not serializer.is_valid():
                logger.error(f"ApiProjectViewSet.create: serializer validation failed: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            logger.debug(f"ApiProjectViewSet.create: serializer valid, validated_data={serializer.validated_data}")
            
            # 保存数据
            instance = serializer.save()
            logger.debug(f"ApiProjectViewSet.create: instance created={instance}")
            
            # 格式化响应
            response_data = serializer.data
            logger.debug(f"ApiProjectViewSet.create: response_data={response_data}")
            
            return Response(response_data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"ApiProjectViewSet.create: exception occurred: {str(e)}", exc_info=True)
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def perform_create(self, serializer):
        """创建项目时记录日志"""
        instance = serializer.save()
        log_operation(
            operation_type='create',
            resource_type='project',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )
    
    def perform_update(self, serializer):
        """更新项目时记录日志"""
        instance = serializer.save()
        log_operation(
            operation_type='edit',
            resource_type='project',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )
    
    def perform_destroy(self, instance):
        """删除项目时记录日志"""
        log_operation(
            operation_type='delete',
            resource_type='project',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )
        instance.delete()
    
    @action(detail=False, methods=['post'], url_path='create-sample')
    def create_sample_project(self, request):
        """创建示例项目（宠物店）"""
        if ApiProject.objects.filter(name='宠物店API示例项目').exists():
            return Response({'message': '示例项目已存在'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 创建示例项目
        project = ApiProject.objects.create(
            name='宠物店API示例项目',
            description='参考Apifox宠物店示例，包含用户管理、宠物管理、订单管理等接口',
            project_type='HTTP',
            status='IN_PROGRESS',
            owner=request.user,
            start_date=datetime.now().date()
        )
        
        # 创建示例数据
        self._create_sample_data(project, request.user)
        
        serializer = self.get_serializer(project)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'], url_path='import')
    def import_api_data(self, request, pk=None):
        """导入API数据，支持Postman、Apifox、JMeter等格式（同步）"""
        # 获取传入的项目（可能为空，因为我们可能需要根据文件创建新项目）
        original_project = None
        if pk:
            try:
                original_project = self.get_object()
            except:
                original_project = None
                
        file = request.FILES.get('file')
        file_format = request.data.get('format', 'postman')
        import_mode = request.data.get('mode', 'overwrite')
        
        if not file:
            return Response({'error': '未提供文件'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 读取文件原始内容（字节流）
            file_bytes = file.read()
            
            # 确定要使用的项目
            project = None
            project_name = "测试"  # 默认项目名称
            
            # 对于Postman和Apifox格式，尝试从文件中提取项目信息
            if file_format.lower() in ['postman', 'apifox']:
                try:
                    file_content = file_bytes.decode('utf-8')
                    import json
                    data = json.loads(file_content)
                    if 'info' in data and 'name' in data['info']:
                        project_name = data['info']['name']
                except Exception as e:
                    logger.warning(f'无法从文件中提取项目信息: {str(e)}，使用默认项目名称')
            
            # 检查系统中是否已有同名项目
            existing_projects = ApiProject.objects.filter(name=project_name)
            if existing_projects.exists():
                project = existing_projects.first()
                logger.info(f'使用现有项目: {project_name} (ID: {project.id})')
            else:
                # 创建新项目
                project = ApiProject.objects.create(
                    name=project_name,
                    description=f'从{file_format}文件导入的项目',
                    project_type='HTTP',
                    status='IN_PROGRESS',
                    owner=request.user,
                    start_date=datetime.now().date()
                )
                logger.info(f'创建新项目: {project_name} (ID: {project.id})')
            
            # 创建导入任务记录
            import_task = ApiImportTask.objects.create(
                project=project,
                user=request.user,
                file_name=file.name,
                file_size=file.size,
                file_format=file_format.lower(),
                status='running'
            )
            
            # 直接调用导入逻辑（同步处理）
            result = self._import_data(file_bytes, file_format.lower(), import_mode, project)
            
            # 更新任务状态
            import_task.status = 'completed'
            import_task.imported_count = result.get('requests', 0) + result.get('collections', 0)
            import_task.total_count = result.get('requests', 0) + result.get('collections', 0)
            import_task.save()
            
            return Response({
                'message': '导入成功',
                'project_id': project.id,
                'task_id': import_task.id,
                'results': result
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f'API导入失败: {str(e)}', exc_info=True)
            return Response({'error': f'导入失败: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'], url_path='import-tasks')
    def get_import_tasks(self, request, pk=None):
        """获取项目的导入任务列表"""
        project = self.get_object()
        tasks = ApiImportTask.objects.filter(project=project).order_by('-created_at')
        
        task_list = []
        for task in tasks:
            task_list.append({
                'id': task.id,
                'file_name': task.file_name,
                'file_format': task.file_format,
                'status': task.status,
                'status_display': task.get_status_display(),
                'error_message': task.error_message,
                'imported_count': task.imported_count,
                'total_count': task.total_count,
                'created_at': task.created_at,
                'updated_at': task.updated_at,
                'completed_at': task.completed_at
            })
        
        return Response(task_list)
    
    @action(detail=False, methods=['get'], url_path='import-tasks/(?P<task_id>\d+)')
    def get_import_task_status(self, request, task_id=None):
        """获取导入任务的状态"""
        try:
            task = ApiImportTask.objects.get(id=task_id)
            # 验证用户是否有权限查看该任务
            if task.user != request.user and task.project.owner != request.user and request.user not in task.project.members.all():
                return Response({'error': '无权限查看该任务'}, status=status.HTTP_403_FORBIDDEN)
            
            return Response({
                'id': task.id,
                'file_name': task.file_name,
                'file_format': task.file_format,
                'status': task.status,
                'status_display': task.get_status_display(),
                'error_message': task.error_message,
                'imported_count': task.imported_count,
                'total_count': task.total_count,
                'created_at': task.created_at,
                'updated_at': task.updated_at,
                'completed_at': task.completed_at
            })
        except ApiImportTask.DoesNotExist:
            return Response({'error': '任务不存在'}, status=status.HTTP_404_NOT_FOUND)
    
    def _import_postman_data(self, file_content, project, import_mode):
        """导入Postman集合数据"""
        import json
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"开始处理Postman文件，项目ID: {project.id}，导入模式: {import_mode}")
        
        try:
            data = json.loads(file_content)
            logger.info(f"解析Postman文件成功，包含'item'属性: {'item' in data}")
        except json.JSONDecodeError as e:
            logger.error(f"解析Postman文件失败: {str(e)}")
            raise
        
        # 如果是覆盖模式，删除现有数据
        if import_mode == 'overwrite':
            logger.info(f"覆盖模式：删除项目 {project.id} 下的所有现有集合和请求")
            # 删除所有请求
            ApiRequest.objects.filter(collection__project=project).delete()
            # 删除所有集合
            ApiCollection.objects.filter(project=project).delete()
        
        collections = []
        requests = []
        
        # 处理Postman集合数据
        def process_item(item, parent_collection=None):
            nonlocal collections, requests
            logger.info(f"处理项目: {item.get('name')}, 父集合: {parent_collection.name if parent_collection else 'None'}")
            
            if isinstance(item, dict):
                # 检查是否有request属性来判断是否为请求
                has_request = 'request' in item
                has_item = 'item' in item and isinstance(item['item'], list)
                
                if has_item:
                    collection_name = item.get('name', '未命名集合')
                    logger.info(f"创建集合: {collection_name}")
                    
                    # 检查是否已存在同名集合
                    existing_collection = None
                    if parent_collection:
                        existing_collection = ApiCollection.objects.filter(
                            project=project, 
                            name=collection_name, 
                            parent=parent_collection
                        ).first()
                    else:
                        existing_collection = ApiCollection.objects.filter(
                            project=project, 
                            name=collection_name, 
                            parent__isnull=True
                        ).first()
                    
                    if existing_collection:
                        logger.info(f"集合已存在，使用现有集合: {collection_name}")
                        collection = existing_collection
                    else:
                        collection = ApiCollection.objects.create(
                            project=project,
                            name=collection_name,
                            description=item.get('description', ''),
                            parent=parent_collection,
                            order=ApiCollection.objects.filter(project=project, parent=parent_collection).count()
                        )
                    collections.append(collection)
                    
                    # 处理子项
                    sub_items = item.get('item', [])
                    logger.info(f"处理子项，数量: {len(sub_items)}")
                    
                    for sub_item in sub_items:
                        process_item(sub_item, collection)
                elif has_request:
                    # 这是一个请求
                    if parent_collection:
                        # 解析请求数据
                        request_data = item.get('request', {})
                        method = request_data.get('method', 'GET')
                        url = self._extract_postman_url(request_data.get('url', {}))
                        
                        logger.info(f"创建请求: {item.get('name')}, 方法: {method}, URL: {url}")
                        
                        # 解析请求头
                        headers = []
                        for header in request_data.get('header', []):
                            if header.get('key') and header.get('enabled', True):
                                headers.append({
                                    'key': header['key'],
                                    'value': header.get('value', ''),
                                    'description': header.get('description', ''),
                                    'enabled': True
                                })
                        
                        # 解析请求参数
                        params = {}
                        for param in request_data.get('url', {}).get('query', []):
                            if param.get('key'):
                                params[param['key']] = param.get('value', '')
                        
                        # 解析请求体
                        body = {}
                        if request_data.get('body'):
                            body_type = request_data['body'].get('mode', 'raw')
                            if body_type == 'raw':
                                body = {
                                    'type': 'json' if request_data['body'].get('raw') else 'raw',
                                    'data': request_data['body'].get('raw') or ''
                                }
                            elif body_type == 'formdata':
                                # 暂时不支持formdata类型
                                body = {'type': 'raw', 'data': ''}
                        
                        # 创建API请求
                        api_request = ApiRequest.objects.create(
                            collection=parent_collection,
                            name=item.get('name', '未命名请求'),
                            description=item.get('description', ''),
                            method=method,
                            url=url,
                            headers=headers,
                            params=params,
                            body=body,
                            created_by=self.request.user,
                            order=ApiRequest.objects.filter(collection=parent_collection).count()
                        )
                        requests.append(api_request)
        
        # 处理根级别项目
        if 'item' in data:
            root_items = data['item']
            logger.info(f"处理根级别项目，数量: {len(root_items)}")
            
            for item in root_items:
                process_item(item)
        else:
            # 单个请求情况
            logger.info("处理单个请求")
            process_item(data)
        
        logger.info(f"Postman文件处理完成，创建了{len(collections)}个集合，{len(requests)}个请求")
        
        return {
            'collections': len(collections),
            'requests': len(requests)
        }
    
    def _extract_postman_url(self, url_data):
        """提取Postman格式的URL"""
        if isinstance(url_data, str):
            return url_data
        elif isinstance(url_data, dict):
            # 处理完整的URL对象
            protocol = url_data.get('protocol', 'http')
            host = '.'.join(url_data.get('host', ['localhost']))
            port = url_data.get('port')
            # 用斜杠连接路径数组，确保以斜杠开头
            path_parts = url_data.get('path', [])
            path = '/' + '/'.join(path_parts) if path_parts else ''
            
            url = f'{protocol}://{host}'
            if port:
                url += f':{port}'
            url += path
            
            # 处理查询参数
            query_params = []
            for param in url_data.get('query', []):
                if param.get('key'):
                    query_params.append(f"{param['key']}={param.get('value', '')}")
            if query_params:
                url += f'?{"&".join(query_params)}'
            
            return url
        return ''
    
    def _import_apifox_data(self, file_content, project, import_mode):
        """导入Apifox数据"""
        # Apifox数据格式与Postman类似，可以复用Postman的导入逻辑
        return self._import_postman_data(file_content, project, import_mode)
    
    def _import_jmeter_data(self, file_content, project, import_mode):
        """导入JMeter数据"""
        # 简单的JMeter JMX文件解析
        from xml.etree import ElementTree as ET
        
        root = ET.fromstring(file_content)
        collections = []
        requests = []
        
        # 创建一个JMeter集合
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
            protocol = http_sampler.findtext('.//stringProp[@name="HTTPSampler.domain"]', '')
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
                created_by=self.request.user,
                order=ApiRequest.objects.filter(collection=jmeter_collection).count()
            )
            requests.append(api_request)
        
        return {
            'collections': len(collections),
            'requests': len(requests)
        }
    
    def _import_data(self, file_bytes, file_format, import_mode, project):
        """根据文件格式调用相应的导入逻辑"""
        if file_format in ['postman', 'apifox']:
            # 解码为字符串处理
            file_content = file_bytes.decode('utf-8')
            return self._import_postman_data(file_content, project, import_mode)
        elif file_format == 'jmeter':
            # 解码为字符串处理
            file_content = file_bytes.decode('utf-8')
            return self._import_jmeter_data(file_content, project, import_mode)
        elif file_format == 'swagger':
            # 解码为字符串处理
            file_content = file_bytes.decode('utf-8')
            return self._import_swagger_data(file_content, project, import_mode)
        elif file_format == 'custom':
            # 直接传递字节流，让_custom_import处理
            return self._import_custom_data(file_bytes, project, import_mode)
        else:
            raise ValueError(f'不支持的文件格式: {file_format}')
            
    def _import_custom_data(self, file_bytes, project, import_mode):
        """导入自定义格式数据，支持JSON、YAML和Excel文件"""
        import json
        import yaml
        import pandas as pd
        import io
        import logging
        logger = logging.getLogger(__name__)
        
        collections = []
        requests = []
        
        try:
            # 尝试解析JSON格式
            file_content = file_bytes.decode('utf-8')
            data = json.loads(file_content)
            logger.info("成功解析为JSON格式")
        except json.JSONDecodeError:
            try:
                # 尝试解析YAML格式
                data = yaml.safe_load(file_bytes)
                logger.info("成功解析为YAML格式")
            except yaml.YAMLError as yaml_error:
                logger.error(f"YAML解析失败: {str(yaml_error)}")
                # 对于YAML文件，我们直接抛出YAML解析错误，而不是尝试解析为Excel格式
                raise ValueError(f'YAML格式解析失败: {str(yaml_error)}')
            except Exception as e:
                logger.error(f"解析文件失败: {str(e)}")
                raise ValueError(f'无法解析文件格式: {str(e)}')
        
        # 处理JSON/YAML格式数据
        # 1. 检查是否为测试用例格式：包含case_code, case_name, steps等字段
        if isinstance(data, dict) and 'case_code' in data:
            logger.info("检测到测试用例格式，开始解析")
            
            # 如果是覆盖模式，删除现有数据
            if import_mode == 'overwrite':
                logger.info(f"覆盖模式：删除项目 {project.id} 下的所有现有集合和请求")
                # 删除所有请求
                ApiRequest.objects.filter(collection__project=project).delete()
                # 删除所有集合
                ApiCollection.objects.filter(project=project).delete()
            
            # 创建测试用例集合
            test_case_name = data.get('case_name', data.get('case_code', '未命名测试用例'))
            test_collection = ApiCollection.objects.create(
                project=project,
                name=test_case_name,
                description=f'测试用例: {data.get("case_code")}, 优先级: {data.get("priority", 2)}',
                order=ApiCollection.objects.filter(project=project).count()
            )
            collections.append(test_collection)
            
            # 处理测试步骤
            steps = data.get('steps', [])
            logger.info(f"发现测试步骤数量: {len(steps)}")
            for i, step in enumerate(steps):
                if isinstance(step, dict):
                    step_name = step.get('step_name', f'步骤{i+1}')
                    logger.info(f"处理步骤 {i+1}: {step_name}")
                    host = step.get('host', '')
                    path = step.get('path', '')
                    method = step.get('method', 'GET').upper()
                    
                    # 只跳过skip_when明确为布尔值true的步骤，其他步骤即使有skip_when条件也导入
                    if step.get('skip_when') is True:
                        logger.info(f"跳过步骤 {i+1} ({step_name})：skip_when为true")
                        continue
                    
                    # 构建URL
                    url = f"{host}{path}" if host and not path.startswith('http') else path if path else host
                    
                    # 获取请求数据
                    req_data = step.get('data', {})
                    headers = step.get('headers', [])
                    
                    # 处理断言
                    assertions = []
                    if step.get('response_assert'):
                        response_assert = step['response_assert']
                        
                        # 状态码断言
                        if response_assert.get('status_code_assert'):
                            assertions.append({
                                'name': '状态码断言',
                                'type': 'status_code',
                                'expected': response_assert['status_code_assert']
                            })
                        
                        # JSONPath断言
                        if response_assert.get('jsonpath_assert'):
                            for i, jsonpath in enumerate(response_assert['jsonpath_assert']):
                                assertions.append({
                                    'name': f'JSONPath断言{i+1}',
                                    'type': 'contains',
                                    'expected': jsonpath
                                })
                    
                    # 处理提取规则
                    extract_rules = []
                    if step.get('extract'):
                        for i, extract in enumerate(step['extract']):
                            if isinstance(extract, dict) and 'extract' in extract:
                                extract_value = extract['extract']
                                # 简单处理，提取变量名和JSONPath
                                if '$set_variable' in extract_value:
                                    # 提取变量名和JSONPath
                                    parts = extract_value.split(',')
                                    if len(parts) >= 2:
                                        variable_name = parts[0].replace('$set_variable(', '')
                                        jsonpath = parts[1].replace('$get_response_data(', '').replace(')', '')
                                        extract_rules.append({
                                            'variable_name': variable_name,
                                            'type': 'json_path',
                                            'json_path': jsonpath
                                        })
                    
                    # 创建请求
                    api_request = ApiRequest.objects.create(
                        collection=test_collection,
                        name=step_name,
                        description=f'测试用例步骤: {step_name}',
                        method=method,
                        url=url,
                        headers=headers,
                        params={},
                        body={'type': 'json', 'data': req_data} if req_data else {},
                        assertions=assertions,
                        extract_rules=extract_rules,
                        created_by=self.request.user,
                        order=ApiRequest.objects.filter(collection=test_collection).count()
                    )
                    requests.append(api_request)
            
            logger.info(f"测试用例处理完成，创建了 {len(collections)} 个集合，{len(requests)} 个请求")
            return {
                'collections': len(collections),
                'requests': len(requests)
            }
        
        # 2. 检查是否为包含collections和requests字段的格式
        if isinstance(data, dict) and 'collections' in data:
            # 包含collections和requests字段的格式
            collections_data = data.get('collections', [])
            requests_data = data.get('requests', [])
            
            # 创建集合
            collection_map = {}
            for coll_data in collections_data:
                parent = collection_map.get(coll_data.get('parent')) if coll_data.get('parent') else None
                collection = ApiCollection.objects.create(
                    project=project,
                    name=coll_data.get('name', '未命名集合'),
                    description=coll_data.get('description', ''),
                    parent=parent,
                    order=ApiCollection.objects.filter(project=project, parent=parent).count()
                )
                collections.append(collection)
                collection_map[coll_data.get('id', collection.id)] = collection
            
            # 创建请求
            for req_data in requests_data:
                collection_id = req_data.get('collection')
                collection = collection_map.get(collection_id)
                if collection:
                    api_request = ApiRequest.objects.create(
                        collection=collection,
                        name=req_data.get('name', '未命名请求'),
                        description=req_data.get('description', ''),
                        method=req_data.get('method', 'GET').upper(),
                        url=req_data.get('url', ''),
                        headers=req_data.get('headers', []),
                        params=req_data.get('params', {}),
                        body=req_data.get('body', {}),
                        created_by=self.request.user,
                        order=ApiRequest.objects.filter(collection=collection).count()
                    )
                    requests.append(api_request)
        elif isinstance(data, list):
            # 直接是集合数组
            for item in data:
                if isinstance(item, dict):
                    # 检查是否是集合
                    if 'item' in item or 'children' in item:
                        # 递归处理集合
                        def process_collection(item_data, parent_collection=None):
                            coll = ApiCollection.objects.create(
                                project=project,
                                name=item_data.get('name', '未命名集合'),
                                description=item_data.get('description', ''),
                                parent=parent_collection,
                                order=ApiCollection.objects.filter(project=project, parent=parent_collection).count()
                            )
                            collections.append(coll)
                            
                            # 处理子项
                            children = item_data.get('item', []) + item_data.get('children', [])
                            for child in children:
                                if isinstance(child, dict):
                                    if 'request' in child:
                                        # 是请求
                                        req = child.get('request', {})
                                        api_request = ApiRequest.objects.create(
                                            collection=coll,
                                            name=child.get('name', '未命名请求'),
                                            description=child.get('description', ''),
                                            method=req.get('method', 'GET').upper(),
                                            url=req.get('url', ''),
                                            headers=req.get('headers', []),
                                            params=req.get('params', {}),
                                            body=req.get('body', {}),
                                            created_by=self.request.user,
                                            order=ApiRequest.objects.filter(collection=coll).count()
                                        )
                                        requests.append(api_request)
                                    else:
                                        # 是子集合
                                        process_collection(child, coll)
                        
                        process_collection(item)
        
        return {
            'collections': len(collections),
            'requests': len(requests)
        }
    
    def _import_swagger_data(self, file_content, project, import_mode):
        """导入Swagger/OpenAPI数据"""
        data = json.loads(file_content)
        collections = []
        requests = []
        
        # 解析Swagger数据
        paths = data.get('paths', {})
        components = data.get('components', {})
        schemas = components.get('schemas', {})
        
        # 按标签分组创建集合
        tag_collections = {}
        
        # 先创建所有标签对应的集合
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                tags = operation.get('tags', [])
                for tag in tags:
                    if tag not in tag_collections:
                        collection = ApiCollection.objects.create(
                            project=project,
                            name=tag,
                            description=f'{tag}相关接口',
                            order=ApiCollection.objects.filter(project=project).count()
                        )
                        tag_collections[tag] = collection
                        collections.append(collection)
        
        # 默认集合
        default_collection = ApiCollection.objects.create(
            project=project,
            name='默认集合',
            description='未分类接口',
            order=ApiCollection.objects.filter(project=project).count()
        )
        collections.append(default_collection)
        
        # 处理每个路径和请求
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                tags = operation.get('tags', [])
                collection = tag_collections.get(tags[0]) if tags else default_collection
                
                # 创建API请求
                api_request = ApiRequest.objects.create(
                    collection=collection,
                    name=operation.get('summary', '未命名请求'),
                    description=operation.get('description', ''),
                    method=method.upper(),
                    url=f"{{base_url}}{path}",
                    headers=[],
                    params={},
                    body={},
                    created_by=self.request.user,
                    order=ApiRequest.objects.filter(collection=collection).count()
                )
                requests.append(api_request)
        
        return {
            'collections': len(collections),
            'requests': len(requests)
        }
    
    def _create_sample_data(self, project, user):
        """创建示例数据"""
        # 用户管理集合
        user_collection = ApiCollection.objects.create(
            project=project,
            name='用户管理',
            description='用户注册、登录、信息管理相关接口',
            order=1
        )
        
        # 用户注册接口
        ApiRequest.objects.create(
            collection=user_collection,
            name='用户注册',
            description='新用户注册接口',
            method='POST',
            url='{{base_url}}/api/users/register',
            headers={'Content-Type': 'application/json'},
            body={
                'type': 'json',
                'data': {
                    'username': 'testuser',
                    'email': 'test@example.com',
                    'password': 'password123'
                }
            },
            created_by=user,
            order=1
        )
        
        # 用户登录接口
        ApiRequest.objects.create(
            collection=user_collection,
            name='用户登录',
            description='用户登录获取token',
            method='POST',
            url='{{base_url}}/api/users/login',
            headers={'Content-Type': 'application/json'},
            body={
                'type': 'json',
                'data': {
                    'username': 'testuser',
                    'password': 'password123'
                }
            },
            created_by=user,
            order=2
        )
        
        # 宠物管理集合
        pet_collection = ApiCollection.objects.create(
            project=project,
            name='宠物管理',
            description='宠物信息增删改查接口',
            order=2
        )
        
        # 获取宠物列表
        ApiRequest.objects.create(
            collection=pet_collection,
            name='获取宠物列表',
            description='分页获取宠物列表',
            method='GET',
            url='{{base_url}}/api/pets',
            headers={'Authorization': 'Bearer {{token}}'},
            params={'page': '1', 'limit': '10'},
            created_by=user,
            order=1
        )
        
        # 创建宠物
        ApiRequest.objects.create(
            collection=pet_collection,
            name='创建宠物',
            description='添加新宠物信息',
            method='POST',
            url='{{base_url}}/api/pets',
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Bearer {{token}}'
            },
            body={
                'type': 'json',
                'data': {
                    'name': '小白',
                    'category': 'dog',
                    'age': 2,
                    'price': 1000
                }
            },
            created_by=user,
            order=2
        )


class ApiCollectionViewSet(viewsets.ModelViewSet):
    queryset = ApiCollection.objects.all()
    serializer_class = ApiCollectionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['project', 'parent']
    
    def get_queryset(self):
        user = self.request.user
        return ApiCollection.objects.filter(
            project__in=ApiProject.objects.filter(
                models.Q(owner=user) | models.Q(members=user)
            )
        ).distinct()

    def perform_create(self, serializer):
        """创建集合时记录日志"""
        instance = serializer.save()
        log_operation(
            operation_type='create',
            resource_type='collection',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )

    def perform_update(self, serializer):
        """更新集合时记录日志"""
        instance = serializer.save()
        log_operation(
            operation_type='edit',
            resource_type='collection',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )

    def perform_destroy(self, instance):
        """删除集合时记录日志"""
        log_operation(
            operation_type='delete',
            resource_type='collection',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )
        instance.delete()


class ApiRequestViewSet(viewsets.ModelViewSet):
    queryset = ApiRequest.objects.all()
    serializer_class = ApiRequestSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['collection', 'method', 'request_type', 'collection__project']
    search_fields = ['name', 'url']
    ordering_fields = ['name', 'url', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        queryset = ApiRequest.objects.filter(
            collection__project__in=ApiProject.objects.filter(
                models.Q(owner=user) | models.Q(members=user)
            )
        ).distinct()
        
        # 支持通过project参数过滤
        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(collection__project_id=project_id)
        
        return queryset
    
    def perform_create(self, serializer):
        """创建接口时记录日志"""
        instance = serializer.save()
        log_operation(
            operation_type='create',
            resource_type='request',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )

    def perform_update(self, serializer):
        """更新接口时记录日志"""
        instance = serializer.save()
        log_operation(
            operation_type='edit',
            resource_type='request',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )

    def perform_destroy(self, instance):
        """删除接口时记录日志"""
        log_operation(
            operation_type='delete',
            resource_type='request',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )
        instance.delete()
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """执行API请求"""
        api_request = self.get_object()
        environment_id = request.data.get('environment_id')
        engine = request.data.get('engine', 'requests')
        
        if engine == 'httprunner':
            from .utils import execute_api_request_httprunner
            try:
                environment = None
                if environment_id:
                    try:
                        environment = Environment.objects.get(id=environment_id)
                    except Environment.DoesNotExist:
                        pass
                
                result = execute_api_request_httprunner(api_request, environment, request.user)
                
                if result.get('success'):
                    return Response(result)
                else:
                    return Response(result, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        try:
            # 解析环境变量
            variables = {}
            if environment_id:
                try:
                    env = Environment.objects.get(id=environment_id)
                    variables.update(env.variables)
                except Environment.DoesNotExist:
                    pass
            
            # 获取全局参数作为兜底
            global_params = GlobalParameter.objects.all()
            for param in global_params:
                if param.key not in variables:
                    variables[param.key] = param.value
            
            # 替换URL中的变量
            url = self._replace_variables(api_request.url or '', variables)
            
            # 准备请求头
            headers = {}
            if isinstance(api_request.headers, list):
                for header_item in api_request.headers:
                    if header_item.get('enabled', True) and header_item.get('key'):
                        key = header_item['key']
                        value = self._replace_variables(str(header_item.get('value', '')), variables)
                        headers[key] = value
            else:
                headers = api_request.headers.copy()
                for key, value in headers.items():
                    headers[key] = self._replace_variables(str(value), variables)
            
            # 准备请求参数
            params = api_request.params.copy() if api_request.params else {}
            for key, value in params.items():
                params[key] = self._replace_variables(str(value), variables)
            
            # 准备请求体
            body_data = None
            if api_request.body and api_request.method in ['POST', 'PUT', 'PATCH']:
                if api_request.body.get('type') == 'json':
                    body_data = api_request.body.get('data', {})
                    body_data = self._replace_variables_in_dict(body_data, variables)
                else:
                    body_data = self._replace_variables_in_dict(api_request.body.get('data'), variables)
            
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
            
            response_time = (end_time - start_time) * 1000  # 转换为毫秒
            
            # 执行断言验证
            assertions = api_request.assertions or []
            for assertion in assertions:
                if assertion.get('type') == 'response_time':
                    assertion['actual_time'] = response_time
            assertions_results = execute_assertions(response, assertions)
            
            # 保存请求历史
            history = RequestHistory.objects.create(
                request=api_request,
                environment_id=environment_id,
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
                    'json': response.json() if response.headers.get('content-type', '').startswith('application/json') else None,
                    'size': len(response.content)
                },
                status_code=response.status_code,
                response_time=response_time,
                executed_by=request.user
            )
            
            # 记录执行操作
            log_operation(
                operation_type='execute',
                resource_type='request',
                resource_id=api_request.id,
                resource_name=api_request.name,
                user=request.user
            )
            
            # 返回包含断言结果的数据
            history_data = RequestHistorySerializer(history).data
            history_data['assertions_results'] = assertions_results
            
            return Response(history_data)
            
        except Exception as e:
            # 保存错误历史
            history = RequestHistory.objects.create(
                request=api_request,
                environment_id=environment_id,
                request_data={
                    'url': api_request.url,
                    'method': api_request.method,
                    'headers': api_request.headers,
                    'params': api_request.params,
                    'body': api_request.body
                },
                error_message=str(e),
                executed_by=request.user
            )
            
            return Response(RequestHistorySerializer(history).data, status=status.HTTP_400_BAD_REQUEST)
    
    def _replace_variables(self, text, variables):
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
    
    def _replace_variables_in_dict(self, data, variables):
        """递归替换字典中的变量"""
        if isinstance(data, dict):
            return {k: self._replace_variables_in_dict(v, variables) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._replace_variables_in_dict(item, variables) for item in data]
        elif isinstance(data, str):
            return self._replace_variables(data, variables)
        else:
            return data


class EnvironmentViewSet(viewsets.ModelViewSet):
    queryset = Environment.objects.all()
    serializer_class = EnvironmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['scope', 'project', 'is_active']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        return Environment.objects.filter(
            models.Q(scope='GLOBAL') | 
            models.Q(
                scope='LOCAL',
                project__in=ApiProject.objects.filter(
                    models.Q(owner=user) | models.Q(members=user)
                )
            )
        ).distinct().order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """激活环境"""
        environment = self.get_object()
        
        # 如果是局部环境，取消同项目下其他环境的激活状态
        if environment.scope == 'LOCAL' and environment.project:
            Environment.objects.filter(
                project=environment.project,
                scope='LOCAL'
            ).update(is_active=False)
        # 如果是全局环境，取消其他全局环境的激活状态
        elif environment.scope == 'GLOBAL':
            Environment.objects.filter(scope='GLOBAL').update(is_active=False)
        
        environment.is_active = True
        environment.save()
        
        return Response({'message': '环境已激活'})

    def perform_create(self, serializer):
        """创建环境时记录日志"""
        instance = serializer.save()
        log_operation(
            operation_type='create',
            resource_type='environment',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )

    def perform_update(self, serializer):
        """更新环境时记录日志"""
        instance = serializer.save()
        log_operation(
            operation_type='edit',
            resource_type='environment',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )

    def perform_destroy(self, instance):
        """删除环境时记录日志"""
        log_operation(
            operation_type='delete',
            resource_type='environment',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )
        instance.delete()


class ApiTestCaseViewSet(viewsets.ModelViewSet):
    queryset = ApiTestCase.objects.all()
    serializer_class = ApiTestCaseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project', 'status', 'priority']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'priority']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        return ApiTestCase.objects.filter(
            project__in=ApiProject.objects.filter(
                models.Q(owner=user) | models.Q(members=user)
            )
        ).distinct()
        
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
        
    def perform_update(self, serializer):
        serializer.save()

    @action(detail=True, methods=['get'], url_path='latest-execution')
    def get_latest_execution(self, request, pk=None):
        """获取用例最新的执行结果"""
        test_case = self.get_object()
        execution = ApiTestCaseExecution.objects.filter(test_case=test_case).first()
        if execution:
            return Response(ApiTestCaseExecutionSerializer(execution).data)
        return Response(None)

    @action(detail=True, methods=['get'], url_path='executions')
    def get_executions(self, request, pk=None):
        """获取用例的执行历史"""
        test_case = self.get_object()
        executions = ApiTestCaseExecution.objects.filter(test_case=test_case).order_by('-created_at')[:20]
        return Response(ApiTestCaseExecutionSerializer(executions, many=True).data)

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """执行测试用例"""
        test_case = self.get_object()
        environment_id = request.data.get('environment_id')
        engine = request.data.get('engine', 'requests')
        
        if engine == 'httprunner':
            # 使用HttpRunner执行
            from .utils import execute_test_case_httprunner
            try:
                environment = None
                if environment_id:
                    try:
                        environment = Environment.objects.get(id=environment_id)
                    except Environment.DoesNotExist:
                        pass
                
                result = execute_test_case_httprunner(test_case, environment, request.user)
                
                if result.get('success'):
                    return Response(result)
                else:
                    return Response(result, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        try:
            environment = None
            if environment_id:
                try:
                    environment = Environment.objects.get(id=environment_id)
                except Environment.DoesNotExist:
                    pass
            
            result = execute_test_case(test_case, environment, request.user)
            
            if result.get('success'):
                return Response(result)
            else:
                return Response(result, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ApiTestCaseStepViewSet(viewsets.ModelViewSet):
    queryset = ApiTestCaseStep.objects.all()
    serializer_class = ApiTestCaseStepSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['test_case']
    ordering = ['step_number']


class TestSuiteTestCaseViewSet(viewsets.ModelViewSet):
    queryset = TestSuiteTestCase.objects.all()
    serializer_class = TestSuiteTestCaseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['test_suite']
    ordering = ['order']


class RequestHistoryViewSet(viewsets.ModelViewSet):
    queryset = RequestHistory.objects.all()
    serializer_class = RequestHistorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['request__request_type', 'status_code']
    ordering = ['-executed_at']
    pagination_class = StandardPagination
    
    def get_queryset(self):
        user = self.request.user
        return RequestHistory.objects.filter(
            request__collection__project__in=ApiProject.objects.filter(
                models.Q(owner=user) | models.Q(members=user)
            )
        ).select_related(
            'request', 'environment', 'executed_by',
            'request__created_by', 'environment__created_by', 'environment__project'
        ).distinct()

    @action(detail=False, methods=['post'], url_path='batch-delete')
    def batch_delete(self, request):
        """批量删除请求历史"""
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'error': '未提供要删除的记录ID'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 确保只能删除有权限的记录
        # 先获取有权限的ID列表，避免在distinct()后调用delete()
        queryset = self.get_queryset()
        valid_ids = list(queryset.filter(id__in=ids).values_list('id', flat=True))
        
        # 使用有权限的ID列表进行删除
        deleted_count, _ = RequestHistory.objects.filter(id__in=valid_ids).delete()
        
        return Response({'message': f'成功删除 {deleted_count} 条记录'})


class TestSuiteViewSet(viewsets.ModelViewSet):
    queryset = TestSuite.objects.all()
    serializer_class = TestSuiteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['project']
    
    def get_queryset(self):
        user = self.request.user
        return TestSuite.objects.filter(
            project__in=ApiProject.objects.filter(
                models.Q(owner=user) | models.Q(members=user)
            )
        ).distinct()

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """执行测试套件"""
        test_suite = self.get_object()
        
        try:
            # 创建执行记录
            execution = TestExecution.objects.create(
                test_suite=test_suite,
                status='RUNNING',
                start_time=timezone.now(),
                executed_by=request.user
            )
            
            # 获取套件中的测试用例
            suite_test_cases = TestSuiteTestCase.objects.filter(
                test_suite=test_suite,
                enabled=True
            ).order_by('order')
            
            # 如果没有测试用例，尝试执行旧的请求关联（向前兼容）
            if not suite_test_cases.exists():
                return self._execute_deprecated_requests(test_suite, execution, request.user)
            
            execution.total_requests = 0 # 统计总步数
            execution.save()
            
            results = []
            passed_count = 0
            failed_count = 0
            
            from .utils import execute_test_case
            
            # 执行每个测试用例
            for suite_tc in suite_test_cases:
                test_case = suite_tc.test_case
                
                try:
                    # 执行单个测试用例
                    case_result = execute_test_case(test_case, test_suite.environment, request.user)
                    
                    execution.total_requests += case_result.get('total_steps', 0)
                    
                    passed_count += case_result.get('passed_steps', 0)
                    failed_count += case_result.get('failed_steps', 0)
                    
                    results.append({
                        'type': 'test_case',
                        'id': test_case.id,
                        'name': test_case.name,
                        'status': case_result.get('status'),
                        'passed_count': case_result.get('passed_steps', 0),
                        'failed_count': case_result.get('failed_steps', 0),
                        'total_count': case_result.get('total_steps', 0),
                        'execution_time': case_result.get('execution_time', 0),
                        'results': case_result.get('results', [])
                    })
                    
                except Exception as e:
                    failed_count += 1
                    results.append({
                        'type': 'test_case',
                        'id': test_case.id,
                        'name': test_case.name,
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
            
            # 记录执行操作
            log_operation(
                operation_type='execute',
                resource_type='suite',
                resource_id=test_suite.id,
                resource_name=test_suite.name,
                user=request.user
            )
            
            return Response(TestExecutionSerializer(execution).data)
            
        except Exception as e:
            if 'execution' in locals():
                execution.status = 'FAILED'
                execution.end_time = timezone.now()
                execution.save()
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        """创建测试套件时记录日志"""
        instance = serializer.save()
        log_operation(
            operation_type='create',
            resource_type='suite',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )

    def perform_update(self, serializer):
        """更新测试套件时记录日志"""
        instance = serializer.save()
        log_operation(
            operation_type='edit',
            resource_type='suite',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )

    def perform_destroy(self, instance):
        """删除测试套件时记录日志"""
        log_operation(
            operation_type='delete',
            resource_type='suite',
            resource_id=instance.id,
            resource_name=instance.name,
            user=self.request.user
        )
        instance.delete()

    @action(detail=True, methods=['post'], url_path='add-test-cases')
    def add_test_cases(self, request, pk=None):
        """添加测试用例到测试套件"""
        test_suite = self.get_object()
        test_case_ids = request.data.get('test_case_ids', [])
        
        try:
            for tc_id in test_case_ids:
                test_case = ApiTestCase.objects.get(id=tc_id)
                TestSuiteTestCase.objects.get_or_create(
                    test_suite=test_suite,
                    test_case=test_case,
                    defaults={
                        'order': TestSuiteTestCase.objects.filter(test_suite=test_suite).count(),
                        'enabled': True
                    }
                )
            
            return Response({'message': '添加成功'})
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def _replace_variables(self, text, variables):
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
    
    def _replace_variables_in_dict(self, data, variables):
        """递归替换字典中的变量"""
        if isinstance(data, dict):
            return {k: self._replace_variables_in_dict(v, variables) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._replace_variables_in_dict(item, variables) for item in data]
        elif isinstance(data, str):
            return self._replace_variables(data, variables)
        else:
            return data


class TestSuiteRequestViewSet(viewsets.ModelViewSet):
    queryset = TestSuiteRequest.objects.all()
    serializer_class = TestSuiteRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['test_suite', 'enabled']
    
    def get_queryset(self):
        user = self.request.user
        return TestSuiteRequest.objects.filter(
            test_suite__project__in=ApiProject.objects.filter(
                models.Q(owner=user) | models.Q(members=user)
            )
        ).distinct()


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
        return TestExecution.objects.filter(
            test_suite__project__in=ApiProject.objects.filter(
                models.Q(owner=user) | models.Q(members=user)
            )
        ).distinct()
    
    @action(detail=True, methods=['post'], url_path='generate-allure-report')
    def generate_allure_report(self, request, pk=None):
        """生成Allure报告数据"""
        execution = self.get_object()
        
        try:
            # 创建报告目录
            results_dir = os.path.join(settings.MEDIA_ROOT, 'allure-results', f'execution_{execution.id}')
            os.makedirs(results_dir, exist_ok=True)
            
            # 生成测试结果文件
            self._generate_test_result_files(execution, results_dir)
            
            # 生成Allure报告
            report_output_dir = os.path.join(settings.MEDIA_ROOT, 'allure-reports', f'execution_{execution.id}')
            os.makedirs(report_output_dir, exist_ok=True)
            
            # 使用Allure命令行工具生成完整报告
            import subprocess
            import shutil
            import time
            from pathlib import Path
            
            # Allure命令行工具路径 - 使用相对路径
            base_dir = Path(__file__).resolve().parent.parent.parent
            
            # Determine executable name based on OS
            if os.name == 'nt':
                allure_executable = 'allure.bat'
            else:
                allure_executable = 'allure'
                
            allure_cmd = str(base_dir / 'allure' / 'bin' / allure_executable)

            if not os.path.exists(allure_cmd):
                logger.warning(f"Allure command not found at: {allure_cmd}, using fallback")
                # 尝试其他可能的路径
                possible_paths = [
                    base_dir / 'allure' / 'bin' / allure_executable,
                    Path('/usr/local/bin/allure'),  # 系统安装的allure
                    Path('/usr/bin/allure'),  # 系统安装的allure
                ]
                for path in possible_paths:
                    if path.exists():
                        allure_cmd = str(path)
                        break
                else:
                    allure_cmd = None
            
            # 确保所有目录存在
            os.makedirs(results_dir, exist_ok=True)
            if allure_cmd:
                try:
                    for _ in range(3):  # 重试机制
                        try:
                            # 如果目录已存在，先清理
                            if os.path.exists(report_output_dir):
                                shutil.rmtree(report_output_dir)
                            
                            # 生成Allure报告
                            subprocess.run([
                                allure_cmd, 'generate',
                                results_dir,
                                '--clean',
                                '--output', report_output_dir
                            ], check=True, capture_output=True, text=True, timeout=30)
                            break
                        except subprocess.TimeoutExpired:
                            if _ == 2:  # 最后一次尝试
                                raise
                            time.sleep(1)
                            continue
                except (subprocess.CalledProcessError, FileNotFoundError) as e:
                    # 如果Allure命令失败，回退到静态文件复制方式
                    logger.warning(f"Allure command failed: {str(e)}, falling back to static files")
                
                static_dir = os.path.join(settings.MEDIA_ROOT, 'allure-static')
                if os.path.exists(static_dir):
                    for item in os.listdir(static_dir):
                        source = os.path.join(static_dir, item)
                        destination = os.path.join(report_output_dir, item)
                        if os.path.isdir(source):
                            shutil.copytree(source, destination, dirs_exist_ok=True)
                        else:
                            shutil.copy2(source, destination)
                
                # 始终确保有可用的报告
                if not os.path.exists(os.path.join(report_output_dir, 'index.html')):
                    # 创建回退的简单报告
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
                    with open(os.path.join(report_output_dir, 'index.html'), 'w', encoding='utf-8') as f:
                        f.write(fallback_html)
            
            # 创建自定义的summary.html页面作为报告概览
            status_class = "status-passed" if execution.status == "COMPLETED" else "status-failed"
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
            
            # 添加测试结果列表
            if execution.results:
                for i, result in enumerate(execution.results):
                    # Check if this is a test case result (new format) or a simple request result (old format)
                    is_test_case = result.get('type') == 'test_case'
                    
                    if is_test_case:
                        is_passed = result.get('status') == 'passed'
                        result_class = "passed" if is_passed else "failed"
                        method_class = "method-post"  # Use green for test case
                        method_name = "CASE"
                        name = result.get('name', f'测试用例 {i+1}')
                        # Show passed/failed count for test case
                        passed_count = result.get('passed_count', 0)
                        failed_count = result.get('failed_count', 0)
                        url = f"Steps: {len(result.get('results', []))} (Passed: {passed_count}, Failed: {failed_count})"
                        status_text = '通过' if is_passed else '失败'
                    else:
                        is_passed = result.get('passed', False)
                        result_class = "passed" if is_passed else "failed"
                        method_class = f"method-{result.get('method', 'GET').lower()}"
                        method_name = result.get('method', 'GET')
                        name = result.get('name', f'测试请求 {i+1}')
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
                {f'<div class="test-error"><strong>错误:</strong> {result.get("error", "")}</div>' if result.get('error') else ""}
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
            # 保存为summary.html，避免覆盖Allure生成的index.html
            summary_file = os.path.join(report_output_dir, 'summary.html')
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(index_content)
            
            return Response({
                'message': 'Allure报告生成成功',
                'report_url': f'/media/allure-reports/execution_{execution.id}/summary.html'
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def _generate_test_result_files(self, execution, report_dir):
        """生成测试结果文件"""
        # 生成容器文件，定义测试套件
        container_data = {
            "uuid": str(execution.id),
            "name": execution.test_suite.name,
            "children": []
        }
        
        # 为每个测试请求添加到children列表
        if execution.results:
            for i, result in enumerate(execution.results):
                container_data["children"].append(f"{execution.id}-{i}")
        
        # 保存容器文件
        container_file_path = os.path.join(report_dir, f'{execution.id}-container.json')
        with open(container_file_path, 'w', encoding='utf-8') as f:
            json.dump(container_data, f, ensure_ascii=False, indent=2)
        
        # 只生成每个测试请求的结果文件，不生成测试套件的结果文件
        if execution.results:
            for i, result in enumerate(execution.results):
                # Check if this is a test case result (new format) or a simple request result (old format)
                is_test_case = result.get('type') == 'test_case'
                
                if is_test_case:
                    status_str = "passed" if result.get('status') == 'passed' else "failed"
                    description = f"Test Case: {result.get('name')}"
                    steps_data = []
                    
                    # Convert test case steps to Allure steps
                    for step_idx, step in enumerate(result.get('results', [])):
                        step_status = "passed" if step.get('passed', False) else "failed"
                        steps_data.append({
                            "name": step.get('name', f"Step {step_idx + 1}"),
                            "status": step_status,
                            "stage": "finished",
                            "start": int(time.time() * 1000) - 500,  # Approximate time
                            "stop": int(time.time() * 1000),
                            "parameters": [
                                {"name": "method", "value": step.get('method', 'GET')},
                                {"name": "url", "value": step.get('url', '')},
                                {"name": "status_code", "value": str(step.get('status_code', ''))}
                            ],
                            "steps": []
                        })
                else:
                    # Old format (deprecated)
                    status_str = "passed" if result.get('passed', False) else "failed"
                    description = f"Method: {result.get('method', 'GET')}\nURL: {result.get('url', '')}"
                    steps_data = [
                        {
                            "name": "发送请求",
                            "status": "passed",
                            "stage": "finished",
                            "start": int(time.time() * 1000) - 1000,
                            "stop": int(time.time() * 1000) - 500,
                            "steps": []
                        },
                        {
                            "name": "验证响应",
                            "status": status_str,
                            "stage": "finished",
                            "start": int(time.time() * 1000) - 500,
                            "stop": int(time.time() * 1000),
                            "steps": []
                        }
                    ]

                request_result = {
                    "uuid": f"{execution.id}-{i}",
                    "name": result.get('name', f'测试请求 {i+1}'),
                    "status": status_str,
                    "stage": "finished",
                    "start": int(time.time() * 1000) - 1000,  # 模拟开始时间
                    "stop": int(time.time() * 1000),  # 模拟结束时间
                    "description": description,
                    "historyId": f"{execution.test_suite.id}-{i}",
                    "fullName": f"{execution.test_suite.name} / {result.get('name', f'请求 {i+1}')}",
                    "links": [],
                    "labels": [
                        {"name": "suite", "value": execution.test_suite.name},
                        {"name": "testClass", "value": execution.test_suite.name},
                        {"name": "package", "value": "api_testing"},
                        {"name": "project", "value": execution.test_suite.project.name}
                    ],
                    "parameters": [
                        {"name": "method", "value": result.get('method', 'GET')},
                        {"name": "url", "value": result.get('url', '')}
                    ],
                    "steps": steps_data
                }
                
                # 添加错误信息（如果有的话）
                if result.get('error'):
                    request_result["statusDetails"] = {
                        "message": result.get('error'),
                        "trace": ""
                    }
                
                # 保存请求结果
                request_file_path = os.path.join(report_dir, f'{execution.id}-{i}-result.json')
                with open(request_file_path, 'w', encoding='utf-8') as f:
                    json.dump(request_result, f, ensure_ascii=False, indent=2)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """用户列表接口，用于项目成员选择"""
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']


class ScheduledTaskViewSet(viewsets.ModelViewSet):
    """定时任务视图集"""
    queryset = ScheduledTask.objects.all()
    serializer_class = ScheduledTaskSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'last_run_time']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """根据用户权限过滤任务"""
        queryset = super().get_queryset()
        
        # 管理员可以看到所有任务
        if self.request.user.is_staff:
            return queryset
        
        # 普通用户只能看到自己创建的任务
        return queryset.filter(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def run_now(self, request, pk=None):
        """立即执行定时任务"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info("=== run_now 方法被调用 ===")
        
        task = self.get_object()
        logger.info(f"获取任务对象: {task.id} - {task.name}")
        
        # 检查权限
        if not request.user.is_staff and task.created_by != request.user:
            logger.info("权限检查失败")
            return Response(
                {'error': '无权执行此任务'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # 创建执行日志
            execution_log = TaskExecutionLog.objects.create(
                task=task,
                status='PENDING',
                executed_by=request.user
            )
            logger.info(f"创建执行日志: {execution_log.id}")
            
            # 异步执行任务
            logger.info("调用 _execute_task_async 方法")
            self._execute_task_async(task, execution_log)
            
            logger.info("任务开始执行")
            return Response(
                {'message': '任务已开始执行', 'execution_id': execution_log.id},
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {'error': f'执行任务失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """激活定时任务"""
        task = self.get_object()
        
        if task.status == 'ACTIVE':
            return Response(
                {'error': '任务已经是激活状态'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        task.status = 'ACTIVE'
        task.next_run_time = task.calculate_next_run()
        task.save()
        
        return Response(
            {'message': '任务已激活', 'next_run_time': task.next_run_time},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """暂停定时任务"""
        task = self.get_object()
        
        if task.status == 'PAUSED':
            return Response(
                {'error': '任务已经是暂停状态'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        task.status = 'PAUSED'
        task.next_run_time = None
        task.save()
        
        return Response(
            {'message': '任务已暂停'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['get'])
    def execution_logs(self, request, pk=None):
        """获取任务执行日志"""
        task = self.get_object()
        
        # 检查权限
        if not request.user.is_staff and task.created_by != request.user:
            return Response(
                {'error': '无权查看此任务的执行日志'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        logs = TaskExecutionLog.objects.filter(task=task).order_by('-created_at')
        page = self.paginate_queryset(logs)
        
        if page is not None:
            serializer = TaskExecutionLogSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = TaskExecutionLogSerializer(logs, many=True)
        return Response(serializer.data)
    
    def _execute_task_async(self, task, execution_log):
        """异步执行任务"""
        import threading
        from datetime import datetime
        
        # 添加测试日志
        import logging
        logger = logging.getLogger(__name__)
        logger.info("=== _execute_task_async 方法被调用 ===")
        
        def execute():
            try:
                # 更新执行状态
                execution_log.status = 'RUNNING'
                execution_log.start_time = timezone.now()
                execution_log.save()
                
                # 执行任务
                if task.task_type == 'TEST_SUITE':
                    result = self._execute_test_suite(task)
                elif task.task_type == 'API_REQUEST':
                    result = self._execute_api_request(task)
                else:
                    raise ValueError(f"未知的任务类型: {task.task_type}")
                
                # 更新执行结果
                execution_log.status = 'COMPLETED'
                execution_log.end_time = timezone.now()
                execution_log.result = result
                execution_log.save()
                
                # 更新任务统计
                task.update_run_stats(success=True)
                task.last_result = result
                task.save()
                
                logger.info("=== 开始检查发送成功通知 ===")
                # 发送通知（如果配置了）
                # 检查任务是否有通知设置
                notification_setting = None
                if hasattr(task, 'notification_settings'):
                    try:
                        notification_setting = task.notification_settings.first()
                        logger.info(f"获取到通知设置: {notification_setting}")
                        if notification_setting:
                            logger.info(f"通知设置详情 - ID: {notification_setting.id}, 是否启用: {notification_setting.is_enabled}, 成功通知: {notification_setting.notify_on_success}")
                        else:
                            logger.info("没有找到通知设置")
                    except Exception as e:
                        logger.error(f"获取任务通知设置时出错: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    logger.info("任务没有notification_settings属性")
                
                if notification_setting and notification_setting.is_enabled:
                    logger.info("通知设置已启用，准备发送成功通知")
                    if notification_setting.notify_on_success:
                        logger.info("调用 _send_notification 方法发送成功通知")
                        self._send_notification(task, execution_log, success=True)
                    else:
                        logger.info("通知设置中未启用成功通知")
                else:
                    logger.info("通知设置未启用或不存在，跳过成功通知")
                logger.info("=== 结束检查发送成功通知 ===")
                
            except Exception as e:
                # 记录执行失败
                execution_log.status = 'FAILED'
                execution_log.end_time = timezone.now()
                execution_log.error_message = str(e)
                execution_log.save()
                
                # 更新任务统计
                task.update_run_stats(success=False)
                task.error_message = str(e)
                task.save()
                
                logger.info("=== 开始检查发送失败通知 ===")
                # 发送失败通知（如果配置了）
                # 检查任务是否有通知设置
                notification_setting = None
                if hasattr(task, 'notification_settings'):
                    try:
                        notification_setting = task.notification_settings.first()
                        logger.info(f"获取到通知设置（失败情况）: {notification_setting}")
                        if notification_setting:
                            logger.info(f"通知设置详情（失败情况） - ID: {notification_setting.id}, 是否启用: {notification_setting.is_enabled}, 失败通知: {notification_setting.notify_on_failure}")
                        else:
                            logger.info("没有找到通知设置（失败情况）")
                    except Exception as e:
                        logger.error(f"获取任务通知设置时出错（失败情况）: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    logger.info("任务没有notification_settings属性（失败情况）")
                
                if notification_setting and notification_setting.is_enabled:
                    logger.info("通知设置已启用，准备发送失败通知")
                    if notification_setting.notify_on_failure:
                        logger.info("调用 _send_notification 方法发送失败通知")
                        self._send_notification(task, execution_log, success=False)
                    else:
                        logger.info("通知设置中未启用失败通知")
                else:
                    logger.info("通知设置未启用或不存在，跳过失败通知")
                logger.info("=== 结束检查发送失败通知 ===")
        
        # 在新线程中执行
        thread = threading.Thread(target=execute)
        thread.daemon = True
        thread.start()
    
    def _execute_test_suite(self, task):
        """执行测试套件"""
        from .utils import execute_test_suite
        
        result = execute_test_suite(
            task.test_suite, 
            task.environment, 
            task.created_by
        )
        return result
    
    def _execute_api_request(self, task):
        """执行API请求"""
        from .utils import execute_api_request
        
        result = execute_api_request(
            task.api_request, 
            task.environment, 
            task.created_by
        )
        return result
    
    def _send_notification(self, task, execution_log, success=True):
        """发送通知邮件"""
        try:
            import logging
            logger = logging.getLogger(__name__)
            from django.core.mail import send_mail
            from django.conf import settings

            logger.info("=== _send_notification 方法被调用 ===")
            logger.info(f"任务ID: {task.id}, 任务名称: {task.name}, 执行状态: {success}")

            # 检查任务是否有通知设置
            notification_setting = None
            if hasattr(task, 'notification_settings'):
                try:
                    notification_setting = task.notification_settings.first()
                    logger.info(f"获取到通知设置: {notification_setting}")
                except Exception as e:
                    logger.error(f"获取任务通知设置时出错: {e}")
                    import traceback
                    traceback.print_exc()

            if not notification_setting:
                logger.warning(f"任务 {task.id} 没有通知设置")
                return

            logger.info(f"通知设置详情 - ID: {notification_setting.id}, 是否启用: {notification_setting.is_enabled}")

            if not notification_setting.is_enabled:
                logger.info(f"任务 {task.id} 的通知设置未启用")
                return

            # 检查是否应该发送通知
            execution_status = 'success' if success else 'failed'
            should_notify = notification_setting.should_notify(execution_status)
            logger.info(f"执行状态: {execution_status}, should_notify结果: {should_notify}")
            if not should_notify:
                logger.info(f"根据执行状态 {execution_status}，不应该发送通知")
                return

            logger.info("通过了通知条件检查")

            # 获取通知配置
            notification_config = notification_setting.get_notification_config()
            
            # 检查是否有通知配置或自定义配置
            has_config = notification_config is not None
            has_custom_bots = bool(notification_setting.custom_webhook_bots)
            has_custom_recipients = notification_setting.custom_recipients.exists()
            has_task_emails = hasattr(task, 'notify_emails') and bool(task.notify_emails)
            
            if not (has_config or has_custom_bots or has_custom_recipients or has_task_emails):
                logger.warning("没有找到通知配置且无自定义设置（任务邮箱列表也为空）")
                return

            if notification_config:
                logger.info(f"找到了通知配置: {notification_config.name}")
            else:
                logger.info("使用自定义通知设置")

            # 根据通知类型发送不同类型的通知
            logger.info(f"通知类型: {notification_setting.notification_type}")

            if notification_setting.notification_type in ['email', 'both']:
                logger.info("发送邮件通知")
                self._send_email_notification(task, execution_log, notification_setting, notification_config, success)

            if notification_setting.notification_type in ['webhook', 'both']:
                logger.info("发送Webhook通知")
                self._send_webhook_notification(task, execution_log, notification_setting, notification_config, success)

        except Exception as e:
            logger.error(f"发送通知失败: {str(e)}", exc_info=True)

    def _send_email_notification(self, task, execution_log, notification_setting, notification_config, success):
        """发送邮件通知"""
        try:
            import logging
            logger = logging.getLogger(__name__)
            from django.core.mail import send_mail
            from django.conf import settings

            logger.info("=== 开始发送邮件通知 ===")

            # 准备邮件内容
            subject = f"定时任务执行{'成功' if success else '失败'}: {task.name}"

            # 过滤掉详细的测试结果数据，只保留概要信息
            summary_info = '无详细信息'
            if execution_log.result:
                result_data = execution_log.result
                # 只保留高级概要字段,过滤掉详细的'results'数组
                summary_fields = {
                    'success': result_data.get('success'),
                    'execution_id': result_data.get('execution_id'),
                    'passed_count': result_data.get('passed_count'),
                    'failed_count': result_data.get('failed_count'),
                    'total_count': result_data.get('total_count')
                }
                # 只保留有值的字段
                summary_info = '\n'.join([f'{k}: {v}' for k, v in summary_fields.items() if v is not None])

            message = f"""
            任务名称: {task.name}
            执行状态: {'成功' if success else '失败'}
            执行时间: {execution_log.created_at.strftime('%Y-%m-%d %H:%M:%S')}
            任务类型: {'测试套件执行' if task.task_type == 'TEST_SUITE' else 'API请求执行'}

            执行概要:
            {summary_info}

            错误信息:
            {execution_log.error_message if execution_log.error_message else '无错误信息'}
            """

            # 获取收件人列表
            recipients = []
            # 首先检查自定义收件人
            if notification_setting.custom_recipients.exists():
                recipients = [user.email for user in notification_setting.custom_recipients.all() if user.email]
                logger.info(f"使用自定义收件人: {recipients}")

            # 如果定时任务表单中指定了通知邮箱，也添加到收件人列表
            if hasattr(task, 'notify_emails') and task.notify_emails:
                if isinstance(task.notify_emails, list):
                    recipients.extend(task.notify_emails)
                else:
                    recipients.append(task.notify_emails)
                logger.info(f"添加任务表单中的通知邮箱: {task.notify_emails}")

            # 去重收件人
            recipients = list(set(recipients))
            logger.info(f"最终收件人列表: {recipients}")

            if not recipients:
                logger.warning("没有找到任何邮件收件人")
                return

            # 发送邮件
            from_email = settings.DEFAULT_FROM_EMAIL
            logger.info(f"准备发送邮件，发件人: {from_email}, 收件人: {recipients}")
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=recipients,
                fail_silently=False,
            )
            logger.info("邮件发送成功")

            # 记录通知日志
            from .models import NotificationLog
            NotificationLog.objects.create(
                task=task,
                task_name=task.name,
                notification_type='task_execution',
                sender_name='系统邮件通知',
                sender_email=from_email,
                recipient_info=[{'email': email} for email in recipients],
                notification_content=message,
                status='success',
                sent_at=timezone.now()
            )

        except Exception as e:
            logger.error(f"发送邮件通知失败: {str(e)}", exc_info=True)
            # 记录通知发送失败的日志
            try:
                from .models import NotificationLog
                NotificationLog.objects.create(
                    task=task,
                    task_name=task.name,
                    notification_type='task_execution',
                    sender_name='系统邮件通知',
                    sender_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_info=[{'email': email} for email in recipients] if 'recipients' in locals() else [],
                    notification_content=f"发送邮件通知失败: {str(e)}",
                    status='failed',
                    error_message=str(e)
                )
            except:
                pass

    def _send_webhook_notification(self, task, execution_log, notification_setting, notification_config, success):
        """发送Webhook通知"""
        try:
            import logging
            import requests
            import json
            logger = logging.getLogger(__name__)

            logger.info("=== 开始发送Webhook通知 ===")

            all_webhook_bots = []
            
            # 1. 首先获取配置中的机器
            if notification_config:
                bots = notification_config.get_webhook_bots()
                for bot in bots:
                    if bot.get('enabled', True):
                        all_webhook_bots.append(bot)
            
            # 2. 获取自定义机器人配置 (覆盖同名/同类型或者是累加，这里选择累加)
            if notification_setting.custom_webhook_bots:
                logger.info(f"发现自定义Webhook机器人配置: {len(notification_setting.custom_webhook_bots)}个")
                for bot_type, bot_config in notification_setting.custom_webhook_bots.items():
                    # 构造统一的bot结构
                    bot_data = {
                        'type': bot_type,
                        'name': bot_config.get('name', f'自定义{bot_type}机器人'),
                        'webhook_url': bot_config.get('webhook_url'),
                        'enabled': bot_config.get('enabled', True)
                    }
                    if bot_type == 'dingtalk' and bot_config.get('secret'):
                        bot_data['secret'] = bot_config.get('secret')
                        
                    if bot_data.get('enabled', True) and bot_data.get('webhook_url'):
                        all_webhook_bots.append(bot_data)

            if not all_webhook_bots:
                logger.warning("没有找到任何启用的webhook机器人配置")
                return

            logger.info(f"总共找到 {len(all_webhook_bots)} 个待发送的webhook机器人")

            # 准备通知内容
            status_text = '成功' if success else '失败'
            status_color = 'green' if success else 'red'

            # 为不同的机器人平台准备消息格式
            for bot in all_webhook_bots:
                if not bot.get('enabled', True) or not bot.get('webhook_url'):
                    logger.info(f"跳过未启用或无URL的机器人: {bot.get('name', 'Unknown')}")
                    continue

                bot_type = bot.get('type', 'unknown')
                webhook_url = bot['webhook_url']
                logger.info(f"发送通知到 {bot_type} 机器人: {bot.get('name', 'Unknown')}")

                # 根据机器人类型构造消息格式
                if bot_type == 'wechat':  # 企业微信
                    message_data = {
                        "msgtype": "markdown",
                        "markdown": {
                            "content": f"""**定时任务执行{status_text}**

任务名称: {task.name}

执行状态: {status_text}

执行时间: {execution_log.created_at.strftime('%Y-%m-%d %H:%M:%S')}

任务类型: {'测试套件执行' if task.task_type == 'TEST_SUITE' else 'API请求执行'}"""
                        }
                    }
                elif bot_type == 'feishu':  # 飞书
                    message_data = {
                        "msg_type": "interactive",
                        "card": {
                            "elements": [{
                                "tag": "div",
                                "text": {
                                    "content": f"**定时任务执行{status_text}**\n任务名称: {task.name}\n执行状态: {status_text}\n执行时间: {execution_log.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n任务类型: {'测试套件执行' if task.task_type == 'TEST_SUITE' else 'API请求执行'}",
                                    "tag": "lark_md"
                                }
                            }],
                            "header": {
                                "title": {
                                    "content": f"定时任务执行{status_text}",
                                    "tag": "plain_text"
                                },
                                "template": "green" if success else "red"
                            }
                        }
                    }
                elif bot_type == 'dingtalk':  # 钉钉
                    message_data = {
                        "msgtype": "markdown",
                        "markdown": {
                            "title": f"定时任务执行{status_text}",
                            "text": f"""**定时任务执行{status_text}**

任务名称: {task.name}

执行状态: {status_text}

执行时间: {execution_log.created_at.strftime('%Y-%m-%d %H:%M:%S')}

任务类型: {'测试套件执行' if task.task_type == 'TEST_SUITE' else 'API请求执行'}"""
                        }
                    }

                    # 钉钉机器人签名验证
                    secret = bot.get('secret')
                    if secret:
                        import time
                        import hmac
                        import hashlib
                        import base64
                        import urllib.parse

                        timestamp = str(round(time.time() * 1000))
                        string_to_sign = f'{timestamp}\n{secret}'
                        string_to_sign_enc = string_to_sign.encode('utf-8')
                        secret_enc = secret.encode('utf-8')
                        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
                        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))

                        # 在URL中添加签名参数
                        if '?' in webhook_url:
                            webhook_url += f'&timestamp={timestamp}&sign={sign}'
                        else:
                            webhook_url += f'?timestamp={timestamp}&sign={sign}'

                        logger.info(f"钉钉机器人签名验证 - 时间戳: {timestamp}")
                        logger.info(f"签名字符串: {string_to_sign}")
                        logger.info(f"生成的签名: {sign}")
                        logger.info(f"最终URL: {webhook_url}")
                    else:
                        logger.info("钉钉机器人未配置签名密钥，使用无签名模式")
                else:  # 通用格式
                    message_data = {
                        "text": f"定时任务执行{status_text}\n任务名称: {task.name}\n执行状态: {status_text}\n执行时间: {execution_log.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n任务类型: {'测试套件执行' if task.task_type == 'TEST_SUITE' else 'API请求执行'}"
                    }

                # 发送webhook请求
                try:
                    response = requests.post(
                        webhook_url,
                        json=message_data,
                        headers={'Content-Type': 'application/json'},
                        timeout=10
                    )
                    response.raise_for_status()
                    logger.info(f"Webhook通知发送成功 - {bot_type}: {response.status_code}")

                    # 记录成功的通知日志
                    from .models import NotificationLog
                    NotificationLog.objects.create(
                        task=task,
                        task_name=task.name,
                        notification_type='task_execution',
                        sender_name=f'系统Webhook通知-{bot_type}',
                        sender_email='',
                        recipient_info=[],
                        webhook_bot_info={
                            'bot_type': bot_type,
                            'bot_name': bot.get('name', 'Unknown'),
                            'webhook_url': webhook_url[:50] + '...' if len(webhook_url) > 50 else webhook_url
                        },
                        notification_content=json.dumps(message_data, ensure_ascii=False),
                        status='success',
                        sent_at=timezone.now(),
                        response_info={
                            'status_code': response.status_code,
                            'response_text': response.text[:500]
                        }
                    )

                except requests.exceptions.RequestException as e:
                    logger.error(f"Webhook通知发送失败 - {bot_type}: {str(e)}")

                    # 记录失败的通知日志
                    try:
                        from .models import NotificationLog
                        NotificationLog.objects.create(
                            task=task,
                            task_name=task.name,
                            notification_type='task_execution',
                            sender_name=f'系统Webhook通知-{bot_type}',
                            sender_email='',
                            recipient_info=[],
                            webhook_bot_info={
                                'bot_type': bot_type,
                                'bot_name': bot.get('name', 'Unknown'),
                                'webhook_url': webhook_url[:50] + '...' if len(webhook_url) > 50 else webhook_url
                            },
                            notification_content=json.dumps(message_data, ensure_ascii=False),
                            status='failed',
                            error_message=str(e),
                            sent_at=timezone.now()
                        )
                    except:
                        pass

            logger.info("=== 结束发送Webhook通知 ===")

        except Exception as e:
            logger.error(f"发送Webhook通知失败: {str(e)}", exc_info=True)


class TaskExecutionLogViewSet(viewsets.ReadOnlyModelViewSet):
    """任务执行日志视图集"""
    queryset = TaskExecutionLog.objects.all()
    serializer_class = TaskExecutionLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['task', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        return TaskExecutionLog.objects.filter(
            task__created_by=user
        ).select_related('task', 'executed_by')




# ================ 通知管理相关视图集 ================

class NotificationConfigViewSet(viewsets.ModelViewSet):
    """通知配置视图集"""
    queryset = NotificationConfig.objects.all()
    serializer_class = NotificationConfigSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['is_active', 'is_default', 'config_type']
    search_fields = ['name', 'sender_name', 'sender_email']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        queryset = NotificationConfig.objects.filter(
            models.Q(created_by=user) | models.Q(is_default=True)
        )
        
        # 支持按配置类型过滤
        config_type = self.request.query_params.get('config_type', None)
        if config_type:
            queryset = queryset.filter(config_type=config_type)
        
        return queryset.distinct()
    
    @action(detail=True, methods=['post'], url_path='add-bot')
    def add_webhook_bot(self, request, pk=None):
        """添加Webhook机器人配置"""
        config = self.get_object()
        bot_type = request.data.get('bot_type')
        name = request.data.get('name')
        webhook_url = request.data.get('webhook_url')
        
        if not all([bot_type, name, webhook_url]):
            return Response({'error': '请提供完整的机器人信息'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 获取现有配置
        webhook_bots = config.webhook_bots or {}
        webhook_bots[bot_type] = {
            'name': name,
            'webhook_url': webhook_url,
            'enabled': True
        }
        
        config.webhook_bots = webhook_bots
        config.save()
        
        serializer = NotificationConfigDetailSerializer(config)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='remove-bot')
    def remove_webhook_bot(self, request, pk=None):
        """移除Webhook机器人配置"""
        config = self.get_object()
        bot_type = request.data.get('bot_type')

        if not bot_type:
            return Response({'error': '请提供机器人类型'}, status=status.HTTP_400_BAD_REQUEST)

        webhook_bots = config.webhook_bots or {}
        if bot_type in webhook_bots:
            del webhook_bots[bot_type]
            config.webhook_bots = webhook_bots
            config.save()
            return Response({'message': f'{bot_type}机器人已移除'})

        return Response({'error': '未找到该机器人配置'}, status=status.HTTP_404_NOT_FOUND)


class NotificationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """通知日志视图集"""
    queryset = NotificationLog.objects.all()
    serializer_class = NotificationLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'notification_type']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        # 修复查询逻辑：通过任务的创建者或相关项目过滤通知日志
        return NotificationLog.objects.filter(
            models.Q(
                task__test_suite__project__in=ApiProject.objects.filter(
                    models.Q(owner=user) | models.Q(members=user)
                )
            ) | models.Q(
                task__api_request__collection__project__in=ApiProject.objects.filter(
                    models.Q(owner=user) | models.Q(members=user)
                )
            ) | models.Q(
                task__created_by=user
            )
        ).distinct()
    
    @action(detail=True, methods=['get'], url_path='detail')
    def get_notification_detail(self, request, pk=None):
        """获取通知详情"""
        notification = self.get_object()
        serializer = NotificationLogDetailSerializer(notification)
        return Response(serializer.data)


class TaskNotificationSettingViewSet(viewsets.ModelViewSet):
    """定时任务通知设置视图集"""
    queryset = TaskNotificationSetting.objects.all()
    serializer_class = TaskNotificationSettingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['task', 'is_enabled']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        return TaskNotificationSetting.objects.filter(
            models.Q(
                task__test_suite__project__in=ApiProject.objects.filter(
                    models.Q(owner=user) | models.Q(members=user)
                )
            ) | models.Q(
                task__api_request__collection__project__in=ApiProject.objects.filter(
                    models.Q(owner=user) | models.Q(members=user)
                )
            ) | models.Q(
                task__created_by=user
            )
        ).distinct()
    
    @action(detail=True, methods=['post'], url_path='update-settings')
    def update_notification_settings(self, request, pk=None):
        """更新通知设置"""
        setting = self.get_object()
        serializer = TaskNotificationSettingDetailSerializer(setting, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data)


# ================ 通知管理相关模型 ================




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
        # 可以根据需要调整权限逻辑，这里返回所有日志
        return OperationLog.objects.all().order_by('-created_at')


class ApiDashboardViewSet(viewsets.ViewSet):
    """API测试仪表盘视图集"""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """获取仪表盘统计数据"""
        try:
            user = request.user
            
            # 获取用户可访问的项目ID列表
            accessible_projects = ApiProject.objects.filter(
                models.Q(owner=user) | models.Q(members=user)
            ).distinct()
            project_ids = accessible_projects.values_list('id', flat=True)

            # 统计数据
            project_count = accessible_projects.count()
            
            # 接口数量 (通过项目关联)
            interface_count = ApiRequest.objects.filter(
                collection__project_id__in=project_ids
            ).count()
            
            # 测试套件数量
            suite_count = TestSuite.objects.filter(
                project_id__in=project_ids
            ).count()
            
            # 执行记录数量 (包括单次请求历史和测试用例执行记录)
            request_history_count = RequestHistory.objects.filter(
                request__collection__project_id__in=project_ids
            ).count()
            
            case_execution_count = ApiTestCaseExecution.objects.filter(
                test_case__project_id__in=project_ids
            ).count()
            
            history_count = request_history_count + case_execution_count

            return Response({
                'project_count': project_count,
                'interface_count': interface_count,
                'suite_count': suite_count,
                'history_count': history_count
            })
        except Exception as e:
            import traceback
            print(f"Error in ApiDashboardViewSet.stats: {str(e)}")
            traceback.print_exc()
            return Response({
                'project_count': 0,
                'interface_count': 0,
                'suite_count': 0,
                'history_count': 0
            }, status=200)


class ApiTestCaseExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ApiTestCaseExecution.objects.all()
    serializer_class = ApiTestCaseExecutionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['test_case', 'status']
    ordering = ['-created_at']
    pagination_class = StandardPagination

    def get_queryset(self):
        user = self.request.user
        return ApiTestCaseExecution.objects.filter(
            test_case__project__in=ApiProject.objects.filter(
                models.Q(owner=user) | models.Q(members=user)
            )
        ).distinct()
