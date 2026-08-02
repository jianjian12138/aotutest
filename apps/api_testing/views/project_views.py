from apps.core_platform.views.base import BaseProjectViewSet
from apps.core_platform.permissions import TenantAwareViewSetMixin
from apps.notifications.models import NotificationConfig, NotificationLog
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db import models, transaction
from django.utils import timezone
from django.http import HttpResponse, FileResponse, Http404, HttpResponseNotFound
from django.views.static import serve
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import time
import os
import json
import logging
import uuid
import subprocess
from datetime import datetime, timedelta
from ..models import ApiProject, ApiCollection, ApiRequest, Environment, RequestHistory, TestSuite, TestExecution, TestSuiteRequest, ScheduledTask, TaskExecutionLog, TaskNotificationSetting, OperationLog, ApiImportTask, ApiTestCaseModule, ApiTestCase, ApiTestCaseStep, ApiTestCaseExecution, TestSuiteTestCase
from apps.core_platform.models import GlobalParameter
from ..import_utils import parse_openapi_spec
from ..serializers import ApiProjectSerializer, ApiCollectionSerializer, ApiRequestSerializer, ApiTestCaseModuleSerializer, ApiTestCaseSerializer, ApiTestCaseStepSerializer, ApiTestCaseExecutionSerializer, TestSuiteTestCaseSerializer, EnvironmentSerializer, RequestHistorySerializer, TestSuiteSerializer, TestSuiteRequestSerializer, TestExecutionSerializer, UserSerializer, ScheduledTaskSerializer, TaskExecutionLogSerializer, NotificationConfigSerializer, NotificationLogSerializer, TaskNotificationSettingSerializer, NotificationConfigDetailSerializer, NotificationLogDetailSerializer, TaskNotificationSettingDetailSerializer, OperationLogSerializer
logger = logging.getLogger(__name__)
from ..utils import execute_assertions, execute_test_case
from ..operation_logger import log_operation
User = get_user_model()
from rest_framework.pagination import PageNumberPagination
class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 1000


class ApiProjectViewSet(BaseProjectViewSet):
    queryset = ApiProject.objects.all()
    serializer_class = ApiProjectSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.
        OrderingFilter]
    filterset_fields = ['project_type', 'status', 'owner']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name', 'start_date']
    ordering = ['-created_at']

    def create(self, request, *args, **kwargs):
        """创建项目，添加详细日志和错误处理"""
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f'ApiProjectViewSet.create: request.data={request.data}')
        try:
            serializer = self.get_serializer(data=request.data)
            logger.debug(f'ApiProjectViewSet.create: serializer={serializer}')
            if not serializer.is_valid():
                logger.error(
                    f'ApiProjectViewSet.create: serializer validation failed: {serializer.errors}'
                    )
                return Response(serializer.errors, status=status.
                    HTTP_400_BAD_REQUEST)
            logger.debug(
                f'ApiProjectViewSet.create: serializer valid, validated_data={serializer.validated_data}'
                )
            instance = serializer.save()
            logger.debug(
                f'ApiProjectViewSet.create: instance created={instance}')
            response_data = serializer.data
            logger.debug(
                f'ApiProjectViewSet.create: response_data={response_data}')
            return Response(response_data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(
                f'ApiProjectViewSet.create: exception occurred: {str(e)}',
                exc_info=True)
            return Response({'error': str(e)}, status=status.
                HTTP_400_BAD_REQUEST)

    def perform_destroy(self, instance):
        """删除项目时记录日志"""
        log_operation(operation_type='delete', resource_type='project',
            resource_id=instance.id, resource_name=instance.name, user=self
            .request.user)
        instance.delete()

    @action(detail=False, methods=['post'], url_path='create-sample')
    def create_sample_project(self, request):
        """创建示例项目（宠物店）"""
        if ApiProject.objects.filter(name='宠物店API示例项目').exists():
            return Response({'message': '示例项目已存在'}, status=status.
                HTTP_400_BAD_REQUEST)
        project = ApiProject.objects.create(name='宠物店API示例项目', description=
            '参考Apifox宠物店示例，包含用户管理、宠物管理、订单管理等接口', project_type='HTTP',
            status='IN_PROGRESS', owner=request.user, start_date=datetime.
            now().date())
        self._create_sample_data(project, request.user)
        serializer = self.get_serializer(project)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='import')
    def import_api_data(self, request, pk=None):
        """导入API数据，支持Postman、Apifox、JMeter等格式（同步）"""
        None
        if pk:
            try:
                self.get_object()
            except Exception:
                None
        file = request.FILES.get('file')
        file_format = request.data.get('format', 'postman')
        import_mode = request.data.get('mode', 'overwrite')
        if not file:
            return Response({'error': '未提供文件'}, status=status.
                HTTP_400_BAD_REQUEST)
        try:
            file_bytes = file.read()
            project = None
            if pk:
                try:
                    project = ApiProject.objects.get(pk=pk)
                except ApiProject.DoesNotExist:
                    pass
            project_name = '已导入项目'
            spec_data = None
            if file_format.lower() in ['swagger', 'openapi']:
                spec_data = parse_openapi_spec(file_bytes)
                if spec_data:
                    project_name = spec_data.get('project_name', project_name)
            elif file_format.lower() in ['postman', 'apifox']:
                try:
                    file_content = file_bytes.decode('utf-8')
                    data = json.loads(file_content)
                    if 'info' in data and 'name' in data['info']:
                        project_name = data['info']['name']
                except Exception as e:
                    logger.warning(f'无法从文件中提取项目信息: {str(e)}')
            if not project:
                existing_projects = ApiProject.objects.filter(name=project_name
                    )
                if existing_projects.exists():
                    project = existing_projects.first()
                    logger.info(f'使用现有项目: {project_name} (ID: {project.id})')
                else:
                    project = ApiProject.objects.create(name=project_name,
                        description=f'从{file_format}文件导入的项目', project_type=
                        'HTTP', status='IN_PROGRESS', owner=request.user,
                        start_date=timezone.now().date())
                    logger.info(f'创建新项目: {project_name} (ID: {project.id})')
            import_task = ApiImportTask.objects.create(project=project,
                user=request.user, file_name=file.name, file_size=file.size,
                file_format=file_format.lower(), status='running')
            from django_q.tasks import async_task
            from .tasks import import_api_data_task
            async_task(import_api_data_task, project.id, file_content,
                file_format.lower(), import_mode, request.user.id,
                import_task.id, task_name=
                f'import_api_{project.id}_{import_task.id}')
            return Response({'message': '导入任务已提交到后台执行', 'project_id':
                project.id, 'task_id': import_task.id}, status=status.
                HTTP_202_ACCEPTED)
        except Exception as e:
            logger.error(f'API导入失败: {str(e)}', exc_info=True)
            return Response({'error': f'导入失败: {str(e)}'}, status=status.
                HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], url_path='import-tasks')
    def get_import_tasks(self, request, pk=None):
        """获取项目的导入任务列表"""
        project = self.get_object()
        tasks = ApiImportTask.objects.filter(project=project).order_by(
            '-created_at')
        task_list = []
        for task in tasks:
            task_list.append({'id': task.id, 'file_name': task.file_name,
                'file_format': task.file_format, 'status': task.status,
                'status_display': task.get_status_display(),
                'error_message': task.error_message, 'imported_count': task
                .imported_count, 'total_count': task.total_count,
                'created_at': task.created_at, 'updated_at': task.
                updated_at, 'completed_at': task.completed_at})
        return Response(task_list)

    @action(detail=False, methods=['get'], url_path=
        'import-tasks/(?P<task_id>\\d+)')
    def get_import_task_status(self, request, task_id=None):
        """获取导入任务的状态"""
        try:
            task = ApiImportTask.objects.get(id=task_id)
            if (task.user != request.user and task.project.owner != request
                .user and request.user not in task.project.members.all()):
                return Response({'error': '无权限查看该任务'}, status=status.
                    HTTP_403_FORBIDDEN)
            return Response({'id': task.id, 'file_name': task.file_name,
                'file_format': task.file_format, 'status': task.status,
                'status_display': task.get_status_display(),
                'error_message': task.error_message, 'imported_count': task
                .imported_count, 'total_count': task.total_count,
                'created_at': task.created_at, 'updated_at': task.
                updated_at, 'completed_at': task.completed_at})
        except ApiImportTask.DoesNotExist:
            return Response({'error': '任务不存在'}, status=status.
                HTTP_404_NOT_FOUND)

    def _import_postman_data(self, file_content, project, import_mode):
        """导入Postman集合数据"""
        import json
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f'开始处理Postman文件，项目ID: {project.id}，导入模式: {import_mode}')
        try:
            data = json.loads(file_content)
            logger.info(f"解析Postman文件成功，包含'item'属性: {'item' in data}")
        except json.JSONDecodeError as e:
            logger.error(f'解析Postman文件失败: {str(e)}')
            raise
        if import_mode == 'overwrite':
            logger.info(f'覆盖模式：删除项目 {project.id} 下的所有现有集合和请求')
            ApiRequest.objects.filter(collection__project=project).delete()
            ApiCollection.objects.filter(project=project).delete()
        collections = []
        requests = []

        def process_item(item, parent_collection=None):
            nonlocal collections, requests
            logger.info(
                f"处理项目: {item.get('name')}, 父集合: {parent_collection.name if parent_collection else 'None'}"
                )
            if isinstance(item, dict):
                has_request = 'request' in item
                has_item = 'item' in item and isinstance(item['item'], list)
                if has_item:
                    collection_name = item.get('name', '未命名集合')
                    logger.info(f'创建集合: {collection_name}')
                    existing_collection = None
                    if parent_collection:
                        existing_collection = ApiCollection.objects.filter(
                            project=project, name=collection_name, parent=
                            parent_collection).first()
                    else:
                        existing_collection = ApiCollection.objects.filter(
                            project=project, name=collection_name,
                            parent__isnull=True).first()
                    if existing_collection:
                        logger.info(f'集合已存在，使用现有集合: {collection_name}')
                        collection = existing_collection
                    else:
                        collection = ApiCollection.objects.create(project=
                            project, name=collection_name, description=item
                            .get('description', ''), parent=
                            parent_collection, order=ApiCollection.objects.
                            filter(project=project, parent=
                            parent_collection).count())
                    collections.append(collection)
                    sub_items = item.get('item', [])
                    logger.info(f'处理子项，数量: {len(sub_items)}')
                    for sub_item in sub_items:
                        process_item(sub_item, collection)
                elif has_request:
                    if parent_collection:
                        request_data = item.get('request', {})
                        method = request_data.get('method', 'GET')
                        url = self._extract_postman_url(request_data.get(
                            'url', {}))
                        logger.info(
                            f"创建请求: {item.get('name')}, 方法: {method}, URL: {url}"
                            )
                        headers = []
                        for header in request_data.get('header', []):
                            if header.get('key') and header.get('enabled', True
                                ):
                                headers.append({'key': header['key'],
                                    'value': header.get('value', ''),
                                    'description': header.get('description',
                                    ''), 'enabled': True})
                        params = {}
                        for param in request_data.get('url', {}).get('query',
                            []):
                            if param.get('key'):
                                params[param['key']] = param.get('value', '')
                        body = {}
                        if request_data.get('body'):
                            body_type = request_data['body'].get('mode', 'raw')
                            if body_type == 'raw':
                                body = {'type': 'json' if request_data[
                                    'body'].get('raw') else 'raw', 'data': 
                                    request_data['body'].get('raw') or ''}
                            elif body_type == 'formdata':
                                body = {'type': 'raw', 'data': ''}
                        api_request = ApiRequest.objects.create(collection=
                            parent_collection, name=item.get('name',
                            '未命名请求'), description=item.get('description',
                            ''), method=method, url=url, headers=headers,
                            params=params, body=body, created_by=self.
                            request.user, order=ApiRequest.objects.filter(
                            collection=parent_collection).count())
                        requests.append(api_request)
        if 'item' in data:
            root_items = data['item']
            logger.info(f'处理根级别项目，数量: {len(root_items)}')
            for item in root_items:
                process_item(item)
        else:
            logger.info('处理单个请求')
            process_item(data)
        logger.info(
            f'Postman文件处理完成，创建了{len(collections)}个集合，{len(requests)}个请求')
        return {'collections': len(collections), 'requests': len(requests)}

    def _extract_postman_url(self, url_data):
        """提取Postman格式的URL"""
        if isinstance(url_data, str):
            return url_data
        elif isinstance(url_data, dict):
            protocol = url_data.get('protocol', 'http')
            host = '.'.join(url_data.get('host', ['localhost']))
            port = url_data.get('port')
            path_parts = url_data.get('path', [])
            path = '/' + '/'.join(path_parts) if path_parts else ''
            url = f'{protocol}://{host}'
            if port:
                url += f':{port}'
            url += path
            query_params = []
            for param in url_data.get('query', []):
                if param.get('key'):
                    query_params.append(
                        f"{param['key']}={param.get('value', '')}")
            if query_params:
                url += f"?{'&'.join(query_params)}"
            return url
        return ''

    def _import_apifox_data(self, file_content, project, import_mode):
        """导入Apifox数据"""
        return self._import_postman_data(file_content, project, import_mode)

    def _import_jmeter_data(self, file_content, project, import_mode):
        """导入JMeter数据"""
        from xml.etree import ElementTree as ET
        root = ET.fromstring(file_content)
        collections = []
        requests = []
        jmeter_collection = ApiCollection.objects.create(project=project,
            name='JMeter导入集合', description='从JMeter导入的接口集合', order=
            ApiCollection.objects.filter(project=project).count())
        collections.append(jmeter_collection)
        for http_sampler in root.findall('.//HTTPSamplerProxy'):
            name = http_sampler.findtext(
                './/stringProp[@name="HTTPSamplerProxy.name"]', '未命名请求')
            method = http_sampler.findtext(
                './/stringProp[@name="HTTPSamplerProxy.method"]', 'GET')
            protocol = http_sampler.findtext(
                './/stringProp[@name="HTTPSampler.domain"]', '')
            domain = http_sampler.findtext(
                './/stringProp[@name="HTTPSampler.domain"]', '')
            port = http_sampler.findtext(
                './/stringProp[@name="HTTPSampler.port"]', '')
            path = http_sampler.findtext(
                './/stringProp[@name="HTTPSampler.path"]', '')
            url = f'{protocol}://{domain}'
            if port:
                url += f':{port}'
            url += path
            api_request = ApiRequest.objects.create(collection=
                jmeter_collection, name=name, description='从JMeter导入',
                method=method, url=url, headers=[], params={}, body={},
                created_by=self.request.user, order=ApiRequest.objects.
                filter(collection=jmeter_collection).count())
            requests.append(api_request)
        return {'collections': len(collections), 'requests': len(requests)}

    def _import_data(self, file_bytes, file_format, import_mode, project):
        """根据文件格式调用相应的导入逻辑"""
        if file_format in ['postman', 'apifox']:
            file_content = file_bytes.decode('utf-8')
            return self._import_postman_data(file_content, project, import_mode
                )
        elif file_format == 'jmeter':
            file_content = file_bytes.decode('utf-8')
            return self._import_jmeter_data(file_content, project, import_mode)
        elif file_format == 'swagger':
            file_content = file_bytes.decode('utf-8')
            return self._import_swagger_data(file_content, project, import_mode
                )
        elif file_format == 'custom':
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
            file_content = file_bytes.decode('utf-8')
            data = json.loads(file_content)
            logger.info('成功解析为JSON格式')
        except json.JSONDecodeError:
            try:
                data = yaml.safe_load(file_bytes)
                logger.info('成功解析为YAML格式')
            except yaml.YAMLError as yaml_error:
                logger.error(f'YAML解析失败: {str(yaml_error)}')
                raise ValueError(f'YAML格式解析失败: {str(yaml_error)}')
            except Exception as e:
                logger.error(f'解析文件失败: {str(e)}')
                raise ValueError(f'无法解析文件格式: {str(e)}')
        if isinstance(data, dict) and 'case_code' in data:
            logger.info('检测到测试用例格式，开始解析')
            if import_mode == 'overwrite':
                logger.info(f'覆盖模式：删除项目 {project.id} 下的所有现有集合和请求')
                ApiRequest.objects.filter(collection__project=project).delete()
                ApiCollection.objects.filter(project=project).delete()
            test_case_name = data.get('case_name', data.get('case_code',
                '未命名测试用例'))
            test_collection = ApiCollection.objects.create(project=project,
                name=test_case_name, description=
                f"测试用例: {data.get('case_code')}, 优先级: {data.get('priority', 2)}"
                , order=ApiCollection.objects.filter(project=project).count())
            collections.append(test_collection)
            steps = data.get('steps', [])
            logger.info(f'发现测试步骤数量: {len(steps)}')
            for i, step in enumerate(steps):
                if isinstance(step, dict):
                    step_name = step.get('step_name', f'步骤{i + 1}')
                    logger.info(f'处理步骤 {i + 1}: {step_name}')
                    host = step.get('host', '')
                    path = step.get('path', '')
                    method = step.get('method', 'GET').upper()
                    if step.get('skip_when') is True:
                        logger.info(
                            f'跳过步骤 {i + 1} ({step_name})：skip_when为true')
                        continue
                    url = f'{host}{path}' if host and not path.startswith(
                        'http') else path if path else host
                    req_data = step.get('data', {})
                    headers = step.get('headers', [])
                    assertions = []
                    if step.get('response_assert'):
                        response_assert = step['response_assert']
                        if response_assert.get('status_code_assert'):
                            assertions.append({'name': '状态码断言', 'type':
                                'status_code', 'expected': response_assert[
                                'status_code_assert']})
                        if response_assert.get('jsonpath_assert'):
                            for i, jsonpath in enumerate(response_assert[
                                'jsonpath_assert']):
                                assertions.append({'name':
                                    f'JSONPath断言{i + 1}', 'type':
                                    'contains', 'expected': jsonpath})
                    extract_rules = []
                    if step.get('extract'):
                        for i, extract in enumerate(step['extract']):
                            if isinstance(extract, dict
                                ) and 'extract' in extract:
                                extract_value = extract['extract']
                                if '$set_variable' in extract_value:
                                    parts = extract_value.split(',')
                                    if len(parts) >= 2:
                                        variable_name = parts[0].replace(
                                            '$set_variable(', '')
                                        jsonpath = parts[1].replace(
                                            '$get_response_data(', '').replace(')',
                                            '')
                                        extract_rules.append({'variable_name':
                                            variable_name, 'type': 'json_path',
                                            'json_path': jsonpath})
                    api_request = ApiRequest.objects.create(collection=
                        test_collection, name=step_name, description=
                        f'测试用例步骤: {step_name}', method=method, url=url,
                        headers=headers, params={}, body={'type': 'json',
                        'data': req_data} if req_data else {}, assertions=
                        assertions, extract_rules=extract_rules, created_by
                        =self.request.user, order=ApiRequest.objects.filter
                        (collection=test_collection).count())
                    requests.append(api_request)
            logger.info(
                f'测试用例处理完成，创建了 {len(collections)} 个集合，{len(requests)} 个请求')
            return {'collections': len(collections), 'requests': len(requests)}
        if isinstance(data, dict) and 'collections' in data:
            collections_data = data.get('collections', [])
            requests_data = data.get('requests', [])
            collection_map = {}
            for coll_data in collections_data:
                parent = collection_map.get(coll_data.get('parent')
                    ) if coll_data.get('parent') else None
                collection = ApiCollection.objects.create(project=project,
                    name=coll_data.get('name', '未命名集合'), description=
                    coll_data.get('description', ''), parent=parent, order=
                    ApiCollection.objects.filter(project=project, parent=
                    parent).count())
                collections.append(collection)
                collection_map[coll_data.get('id', collection.id)] = collection
            for req_data in requests_data:
                collection_id = req_data.get('collection')
                collection = collection_map.get(collection_id)
                if collection:
                    api_request = ApiRequest.objects.create(collection=
                        collection, name=req_data.get('name', '未命名请求'),
                        description=req_data.get('description', ''), method
                        =req_data.get('method', 'GET').upper(), url=
                        req_data.get('url', ''), headers=req_data.get(
                        'headers', []), params=req_data.get('params', {}),
                        body=req_data.get('body', {}), created_by=self.
                        request.user, order=ApiRequest.objects.filter(
                        collection=collection).count())
                    requests.append(api_request)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    if 'item' in item or 'children' in item:

                        def process_collection(item_data, parent_collection
                            =None):
                            coll = ApiCollection.objects.create(project=
                                project, name=item_data.get('name', '未命名集合'
                                ), description=item_data.get('description',
                                ''), parent=parent_collection, order=
                                ApiCollection.objects.filter(project=
                                project, parent=parent_collection).count())
                            collections.append(coll)
                            children = item_data.get('item', []
                                ) + item_data.get('children', [])
                            for child in children:
                                if isinstance(child, dict):
                                    if 'request' in child:
                                        req = child.get('request', {})
                                        api_request = (ApiRequest.objects.
                                            create(collection=coll, name=child.
                                            get('name', '未命名请求'), description=
                                            child.get('description', ''),
                                            method=req.get('method', 'GET').
                                            upper(), url=req.get('url', ''),
                                            headers=req.get('headers', []),
                                            params=req.get('params', {}), body=
                                            req.get('body', {}), created_by=
                                            self.request.user, order=ApiRequest
                                            .objects.filter(collection=coll).
                                            count()))
                                        requests.append(api_request)
                                    else:
                                        process_collection(child, coll)
                        process_collection(item)
        return {'collections': len(collections), 'requests': len(requests)}

    def _import_swagger_data(self, file_content, project, import_mode):
        """导入Swagger/OpenAPI数据"""
        spec_data = parse_openapi_spec(file_content)
        if not spec_data:
            raise ValueError('无法解析 OpenAPI 规范文件')
        collections_count = 0
        requests_count = 0
        tag_collections = {}
        with transaction.atomic():
            for req_data in spec_data['requests']:
                tag_name = req_data['tag']
                if tag_name not in tag_collections:
                    collection, created = ApiCollection.objects.get_or_create(
                        project=project, name=tag_name, defaults={
                        'description': f'{tag_name}相关接口', 'order':
                        ApiCollection.objects.filter(project=project).count()})
                    tag_collections[tag_name] = collection
                    if created:
                        collections_count += 1
                collection = tag_collections[tag_name]
                ApiRequest.objects.create(collection=collection, name=
                    req_data['name'], description=req_data['description'],
                    method=req_data['method'], url=req_data['url'], headers
                    =req_data['headers'], params=req_data['params'], body=
                    req_data['body'], created_by=self.request.user, order=
                    ApiRequest.objects.filter(collection=collection).count())
                requests_count += 1
        return {'collections': collections_count, 'requests': requests_count}

    def _create_sample_data(self, project, user):
        """创建示例数据"""
        user_collection = ApiCollection.objects.create(project=project,
            name='用户管理', description='用户注册、登录、信息管理相关接口', order=1)
        ApiRequest.objects.create(collection=user_collection, name='用户注册',
            description='新用户注册接口', method='POST', url=
            '{{base_url}}/api/users/register', headers={'Content-Type':
            'application/json'}, body={'type': 'json', 'data': {'username':
            'testuser', 'email': 'test@example.com', 'password':
            'password123'}}, created_by=user, order=1)
        ApiRequest.objects.create(collection=user_collection, name='用户登录',
            description='用户登录获取token', method='POST', url=
            '{{base_url}}/api/users/login', headers={'Content-Type':
            'application/json'}, body={'type': 'json', 'data': {'username':
            'testuser', 'password': 'password123'}}, created_by=user, order=2)
        pet_collection = ApiCollection.objects.create(project=project, name
            ='宠物管理', description='宠物信息增删改查接口', order=2)
        ApiRequest.objects.create(collection=pet_collection, name='获取宠物列表',
            description='分页获取宠物列表', method='GET', url=
            '{{base_url}}/api/pets', headers={'Authorization':
            'Bearer {{token}}'}, params={'page': '1', 'limit': '10'},
            created_by=user, order=1)
        ApiRequest.objects.create(collection=pet_collection, name='创建宠物',
            description='添加新宠物信息', method='POST', url=
            '{{base_url}}/api/pets', headers={'Content-Type':
            'application/json', 'Authorization': 'Bearer {{token}}'}, body=
            {'type': 'json', 'data': {'name': '小白', 'category': 'dog',
            'age': 2, 'price': 1000}}, created_by=user, order=2)


class EnvironmentViewSet(BaseProjectViewSet):
    # 第六轮批次2：修复形式挂靠，并堵住 GLOBAL 分支的真实跨租户读取 ——
    # 原实现 Q(scope='GLOBAL') 只按状态字段过滤、无任何归属校验，
    # 任一登录用户都能读到全平台所有 GLOBAL 环境的 variables（常含 token/密码）。
    tenant_scope_self_managed = True
    tenant_scope_self_managed_reason = (
        'get_queryset 自管归属边界：LOCAL 环境限 Q(owner=user)|Q(members=user) 的 ApiProject（协作成员可见性不变）；'
        'GLOBAL 环境本轮由“全平台任意登录用户可读”收敛为“本人或与本人共享 ApiProject 的协作者所创建”，只收紧不放宽。'
        'Environment 无 organization 字段且 ApiProject 亦无 organization，自动解析会命中 project__organization 直接 FieldError；'
        '退而按 created_by 叠加又会把项目成员可见的 LOCAL 环境收成 owner-only、破坏协作，故声明自管'
    )
    queryset = Environment.objects.all()
    serializer_class = EnvironmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['scope', 'is_active']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        my_projects = ApiProject.objects.filter(
            models.Q(owner=user) | models.Q(members=user))
        # LOCAL：沿用原有项目归属过滤，成员共享语义不变
        scope_q = models.Q(scope='LOCAL', project__in=my_projects)
        if user.is_staff or user.is_superuser:
            scope_q |= models.Q(scope='GLOBAL')
        else:
            # GLOBAL：补上原本缺失的归属校验，限本人及共享项目的协作者所建
            mate_ids = User.objects.filter(
                models.Q(owned_api_projects__in=my_projects)
                | models.Q(api_projects__in=my_projects)).values_list('id', flat=True)
            scope_q |= models.Q(scope='GLOBAL') & (
                models.Q(created_by=user) | models.Q(created_by__in=mate_ids))
        queryset = Environment.objects.filter(scope_q)
        project_id = self.request.query_params.get('project')
        if project_id:
            queryset = queryset.filter(models.Q(scope='GLOBAL') | models.Q(
                scope='LOCAL', project_id=project_id))
        return self._apply_tenant_scope(queryset.distinct().order_by('-created_at'))

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """激活环境"""
        environment = self.get_object()
        if environment.scope == 'LOCAL' and environment.project:
            Environment.objects.filter(project=environment.project, scope=
                'LOCAL').update(is_active=False)
        elif environment.scope == 'GLOBAL':
            Environment.objects.filter(scope='GLOBAL').update(is_active=False)
        environment.is_active = True
        environment.save()
        return Response({'message': '环境已激活'})

    def perform_destroy(self, instance):
        """删除环境时记录日志"""
        log_operation(operation_type='delete', resource_type='environment',
            resource_id=instance.id, resource_name=instance.name, user=self
            .request.user)
        instance.delete()


class UserViewSet(TenantAwareViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """用户列表接口，用于项目成员选择。
    第六轮批次2：接入统一租户隔离 —— 管理员(is_staff/is_superuser)全量；其余仅看自己，禁止同组织 PII 互见。"""
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    org_field = None  # 自定义 get_queryset 已实现隔离，不依赖 mixin 自动解析
    # 第六轮批次2：显式声明自管租户过滤，并在每个 return 分支收口 _apply_tenant_scope。
    tenant_scope_self_managed = True
    tenant_scope_self_managed_reason = (
        'get_queryset 已实现严于组织级隔离的边界：管理员全量，其余用户仅能看到自己一行（fail-closed）。'
        'User 模型自带 organization 字段，若改用自动解析会放宽为“同组织用户互相可见”，'
        '直接暴露 email 等 PII，属可见性倒退，故声明自管'
    )

    def get_queryset(self):
        user = self.request.user
        # 第六轮批次2：接入统一租户隔离
        # 管理员全量；普通用户仅看自己（fail-closed，绝不暴露同组织他人 PII）
        if user.is_authenticated and (user.is_staff or user.is_superuser):
            return self._apply_tenant_scope(User.objects.all().order_by('username'))
        uid = getattr(user, 'id', None)
        return self._apply_tenant_scope(User.objects.filter(id=uid).order_by('username'))


