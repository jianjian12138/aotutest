from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.api_testing.models import (
    ApiProject, ApiCollection, ApiRequest, Environment,
    TestSuite, TestSuiteRequest, ScheduledTask
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Insert sample data for API testing module'

    def handle(self, *args, **kwargs):
        # Get the first user as the owner/creator
        try:
            user = User.objects.first()
            if not user:
                self.stdout.write(self.style.ERROR('No users found. Please create a user first.'))
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error getting user: {e}'))
            return

        self.stdout.write(self.style.SUCCESS('Starting to insert sample data...'))

        # 1. Create API Project
        project = ApiProject.objects.create(
            name='示例API项目',
            description='这是一个用于演示的API测试项目',
            project_type='HTTP',
            status='IN_PROGRESS',
            start_date=timezone.now().date(),
            owner=user
        )
        self.stdout.write(self.style.SUCCESS(f'Created API Project: {project.name}'))

        # 2. Create API Collections
        collections = []
        for i in range(3):
            collection = ApiCollection.objects.create(
                name=f'集合{i+1}',
                description=f'这是第{i+1}个API集合',
                order=i+1,
                project=project
            )
            collections.append(collection)
            self.stdout.write(self.style.SUCCESS(f'Created API Collection: {collection.name}'))

        # 3. Create Environment
        environment = Environment.objects.create(
            name='测试环境',
            scope='LOCAL',
            variables={
                'base_url': 'https://jsonplaceholder.typicode.com',
                'token': 'sample_token_123'
            },
            is_active=True,
            project=project,
            created_by=user
        )
        self.stdout.write(self.style.SUCCESS(f'Created Environment: {environment.name}'))

        # 4. Create API Requests
        requests = []
        sample_requests = [
            {
                'name': '获取用户列表',
                'method': 'GET',
                'url': '{{base_url}}/users',
                'headers': {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer {{token}}'
                },
                'params': {'page': 1, 'limit': 10},
                'body': {},
                'assertions': [
                    {
                        'type': 'status_code',
                        'expected': 200,
                        'operator': 'equals'
                    }
                ],
                'extract_rules': [
                    {
                        'name': 'first_user_id',
                        'path': '$[0].id',
                        'type': 'jsonpath'
                    }
                ]
            },
            {
                'name': '创建用户',
                'method': 'POST',
                'url': '{{base_url}}/users',
                'headers': {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer {{token}}'
                },
                'params': {},
                'body': {
                    'name': 'Test User',
                    'username': 'testuser',
                    'email': 'test@example.com'
                },
                'assertions': [
                    {
                        'type': 'status_code',
                        'expected': 201,
                        'operator': 'equals'
                    }
                ]
            },
            {
                'name': '获取单个用户',
                'method': 'GET',
                'url': '{{base_url}}/users/{{first_user_id}}',
                'headers': {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer {{token}}'
                },
                'params': {},
                'body': {},
                'assertions': [
                    {
                        'type': 'status_code',
                        'expected': 200,
                        'operator': 'equals'
                    },
                    {
                        'type': 'jsonpath',
                        'path': '$.id',
                        'expected': '{{first_user_id}}',
                        'operator': 'equals'
                    }
                ]
            },
            {
                'name': '更新用户',
                'method': 'PUT',
                'url': '{{base_url}}/users/{{first_user_id}}',
                'headers': {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer {{token}}'
                },
                'params': {},
                'body': {
                    'name': 'Updated Test User',
                    'username': 'updatedtestuser'
                },
                'assertions': [
                    {
                        'type': 'status_code',
                        'expected': 200,
                        'operator': 'equals'
                    }
                ]
            },
            {
                'name': '删除用户',
                'method': 'DELETE',
                'url': '{{base_url}}/users/{{first_user_id}}',
                'headers': {
                    'Authorization': 'Bearer {{token}}'
                },
                'params': {},
                'body': {},
                'assertions': [
                    {
                        'type': 'status_code',
                        'expected': 200,
                        'operator': 'equals'
                    }
                ]
            }
        ]

        for i, req_data in enumerate(sample_requests):
            collection = collections[i % len(collections)]
            api_request = ApiRequest.objects.create(
                collection=collection,
                name=req_data['name'],
                description=f'这是{req_data["name"]}的描述',
                request_type='HTTP',
                method=req_data['method'],
                url=req_data['url'],
                headers=req_data['headers'],
                params=req_data['params'],
                body=req_data['body'],
                auth={},
                assertions=req_data['assertions'],
                extract_rules=req_data.get('extract_rules', []),
                order=i+1,
                created_by=user
            )
            requests.append(api_request)
            self.stdout.write(self.style.SUCCESS(f'Created API Request: {api_request.name}'))

        # 5. Create Test Suite
        test_suite = TestSuite.objects.create(
            project=project,
            name='示例测试套件',
            description='这是一个用于演示的测试套件',
            environment=environment,
            created_by=user
        )

        # Add requests to test suite
        for i, api_request in enumerate(requests[:3]):  # Add first 3 requests to test suite
            TestSuiteRequest.objects.create(
                test_suite=test_suite,
                request=api_request,
                order=i+1,
                assertions=[],
                enabled=True
            )
        self.stdout.write(self.style.SUCCESS(f'Created Test Suite: {test_suite.name}'))

        # 6. Create Scheduled Task
        scheduled_task = ScheduledTask.objects.create(
            name='示例定时任务',
            description='这是一个用于演示的定时任务',
            task_type='TEST_SUITE',
            trigger_type='INTERVAL',
            interval_seconds=3600,  # Run every hour
            test_suite=test_suite,
            environment=environment,
            status='ACTIVE',
            created_by=user
        )
        self.stdout.write(self.style.SUCCESS(f'Created Scheduled Task: {scheduled_task.name}'))

        self.stdout.write(self.style.SUCCESS('\nSample data insertion completed successfully!'))
        self.stdout.write(self.style.SUCCESS(f'Created: {ApiProject.objects.count()} API Projects'))
        self.stdout.write(self.style.SUCCESS(f'Created: {ApiCollection.objects.count()} API Collections'))
        self.stdout.write(self.style.SUCCESS(f'Created: {ApiRequest.objects.count()} API Requests'))
        self.stdout.write(self.style.SUCCESS(f'Created: {Environment.objects.count()} Environments'))
        self.stdout.write(self.style.SUCCESS(f'Created: {TestSuite.objects.count()} Test Suites'))
        self.stdout.write(self.style.SUCCESS(f'Created: {ScheduledTask.objects.count()} Scheduled Tasks'))
