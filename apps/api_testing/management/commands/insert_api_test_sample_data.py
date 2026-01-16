from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.users.models import User
from apps.api_testing.models import (
    ApiProject, TestSuite, TestSuiteRequest, ApiCollection, ApiRequest,
    TestExecution, Environment
)
import random


class Command(BaseCommand):
    help = 'Create sample API test execution data for ALLURE reports'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=5,
            help='Number of test executions to create',
        )

    def handle(self, *args, **options):
        count = options.get('count')

        # 获取用户
        user = User.objects.order_by('-date_joined').first()
        if not user:
            self.stdout.write(self.style.ERROR('No users found. Please create a user first.'))
            return

        self.stdout.write(f'Creating {count} sample API test executions for user: {user.username}')

        try:
            # 创建或获取示例项目
            project, created = ApiProject.objects.get_or_create(
                name='示例API项目',
                defaults={
                    'description': '用于生成示例ALLURE报告的API项目',
                    'project_type': 'HTTP',
                    'status': 'IN_PROGRESS',
                    'owner': user,
                    'start_date': timezone.now().date()
                }
            )

            if created:
                self.stdout.write(f'Created new API project: {project.name}')
            else:
                self.stdout.write(f'Using existing API project: {project.name}')

            # 创建或获取示例环境
            environment, _ = Environment.objects.get_or_create(
                name='示例环境',
                project=project,
                scope='LOCAL',
                defaults={
                    'variables': {
                        'base_url': 'https://jsonplaceholder.typicode.com'
                    },
                    'is_active': True,
                    'created_by': user
                }
            )

            # 创建或获取示例集合
            collection, _ = ApiCollection.objects.get_or_create(
                project=project,
                name='示例API集合',
                defaults={
                    'description': '示例API请求集合',
                    'order': 1
                }
            )

            # 创建示例API请求
            api_requests = []
            request_data_list = [
                {
                    'name': '获取用户列表',
                    'method': 'GET',
                    'url': '{{base_url}}/users',
                    'headers': [{'key': 'Content-Type', 'value': 'application/json', 'enabled': True}]
                },
                {
                    'name': '获取单个用户',
                    'method': 'GET',
                    'url': '{{base_url}}/users/1',
                    'headers': [{'key': 'Content-Type', 'value': 'application/json', 'enabled': True}]
                },
                {
                    'name': '创建新用户',
                    'method': 'POST',
                    'url': '{{base_url}}/users',
                    'headers': [{'key': 'Content-Type', 'value': 'application/json', 'enabled': True}],
                    'body': {
                        'type': 'json',
                        'data': {
                            'name': 'John Doe',
                            'username': 'johndoe',
                            'email': 'john@example.com'
                        }
                    }
                },
                {
                    'name': '更新用户信息',
                    'method': 'PUT',
                    'url': '{{base_url}}/users/1',
                    'headers': [{'key': 'Content-Type', 'value': 'application/json', 'enabled': True}],
                    'body': {
                        'type': 'json',
                        'data': {
                            'name': 'Jane Doe',
                            'email': 'jane@example.com'
                        }
                    }
                },
                {
                    'name': '删除用户',
                    'method': 'DELETE',
                    'url': '{{base_url}}/users/1',
                    'headers': [{'key': 'Content-Type', 'value': 'application/json', 'enabled': True}]
                }
            ]

            for request_data in request_data_list:
                api_request, _ = ApiRequest.objects.get_or_create(
                    collection=collection,
                    name=request_data['name'],
                    defaults={
                        'description': f'示例API请求: {request_data["name"]}',
                        'method': request_data['method'],
                        'url': request_data['url'],
                        'headers': request_data.get('headers', {}),
                        'body': request_data.get('body', {}),
                        'created_by': user,
                        'order': len(api_requests) + 1
                    }
                )
                api_requests.append(api_request)

            # 创建或获取测试套件
            test_suite, _ = TestSuite.objects.get_or_create(
                project=project,
                name='示例测试套件',
                defaults={
                    'description': '示例测试套件，用于生成ALLURE报告',
                    'environment': environment,
                    'created_by': user
                }
            )

            # 确保测试套件包含所有API请求
            TestSuiteRequest.objects.filter(test_suite=test_suite).delete()
            for i, api_request in enumerate(api_requests):
                TestSuiteRequest.objects.create(
                    test_suite=test_suite,
                    request=api_request,
                    order=i,
                    enabled=True,
                    assertions=[]
                )

            # 创建示例测试执行记录
            for i in range(count):
                execution = TestExecution.objects.create(
                    test_suite=test_suite,
                    status='COMPLETED' if random.random() > 0.3 else 'FAILED',
                    start_time=timezone.now() - timezone.timedelta(minutes=i*10),
                    end_time=timezone.now() - timezone.timedelta(minutes=i*10 - random.randint(1, 5)),
                    executed_by=user,
                    total_requests=len(api_requests),
                    passed_requests=random.randint(0, len(api_requests)),
                    failed_requests=len(api_requests) - random.randint(0, len(api_requests)),
                )

                # 生成测试结果
                results = []
                for api_request in api_requests:
                    passed = random.random() > 0.2
                    results.append({
                        'name': api_request.name,
                        'method': api_request.method,
                        'url': 'https://jsonplaceholder.typicode.com/users',
                        'status_code': random.choice([200, 201, 400, 404, 500]) if not passed else 200,
                        'response_time': random.uniform(50, 500),
                        'passed': passed,
                        'error': '请求失败' if not passed else '',
                        'assertions_results': []
                    })

                execution.results = results
                execution.save()

                self.stdout.write(f'Created sample test execution: {i+1}/{count}')

            self.stdout.write(
                self.style.SUCCESS(f'Successfully created {count} sample API test executions')
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating sample data: {e}'))
            import traceback
            traceback.print_exc()