from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
import uuid

from apps.wharttest.models import (
    WHartTestConfig,
    WHartTestProject,
    WHartTestExecution,
    WHartTestTask,
    WHartTestIntegrationLog
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Insert sample data for WHartTest module'

    def handle(self, *args, **kwargs):
        # 创建或获取默认用户
        try:
            admin_user = User.objects.get(username='admin')
        except User.DoesNotExist:
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )
        
        # 创建示例配置
        config, created = WHartTestConfig.objects.get_or_create(
            name='示例WHartTest配置',
            defaults={
                'base_url': 'https://wharttest.example.com',
                'api_key': 'sample-api-key-123',
                'description': '这是一个示例WHartTest配置',
                'is_active': True,
                'created_by': admin_user
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'创建示例配置: {config.name}'))
        
        # 创建示例项目
        project, created = WHartTestProject.objects.get_or_create(
            name='示例WHartTest项目',
            defaults={
                'config': config,
                'wharttest_project_id': f'wharttest-proj-{uuid.uuid4().hex[:8]}',
                'description': '这是一个示例WHartTest项目',
                'is_active': True,
                'created_by': admin_user
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'创建示例项目: {project.name}'))
        
        # 创建示例执行记录
        for i in range(3):
            execution, created = WHartTestExecution.objects.get_or_create(
                name=f'示例执行{i+1}',
                defaults={
                    'project': project,
                    'status': 'SUCCESS' if i % 2 == 0 else 'FAILED',
                    'execution_id': f'wharttest-exec-{uuid.uuid4().hex[:8]}',
                    'description': f'这是示例执行记录{i+1}',
                    'start_time': timezone.now() - timezone.timedelta(days=i),
                    'end_time': timezone.now() - timezone.timedelta(days=i, hours=1),
                    'executed_by': admin_user,
                    'result': {
                        'passed': 15 if i % 2 == 0 else 10,
                        'failed': 2 if i % 2 == 0 else 5,
                        'total': 17 if i % 2 == 0 else 15,
                        'duration': 120.5,
                        'report_url': f'{config.base_url}/reports/exec-{i+1}'
                    },
                    'logs': f'示例执行日志{i+1}...'
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'创建示例执行记录: {execution.name}'))
        
        # 创建示例任务
        for i in range(3):
            task_types = ['TESTCASE_GENERATION', 'TEST_EXECUTION', 'KNOWLEDGE_MANAGEMENT']
            execution_statuses = ['SUCCESS', 'FAILED', 'RUNNING']
            
            task, created = WHartTestTask.objects.get_or_create(
                name=f'示例任务{i+1}',
                defaults={
                    'project': project,
                    'task_type': task_types[i % len(task_types)],
                    'status': execution_statuses[i % len(execution_statuses)],
                    'task_data': {'sample_key': f'sample_value_{i+1}'},
                    'description': f'这是示例任务{i+1}',
                    'created_by': admin_user
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'创建示例任务: {task.name}'))
        
        # 创建示例集成日志
        for i in range(5):
            log, created = WHartTestIntegrationLog.objects.get_or_create(
                message=f'示例集成日志{i+1}',
                defaults={
                    'config': config,
                    'log_level': 'INFO' if i % 2 == 0 else 'ERROR',
                    'request_data': {'action': f'test-action-{i+1}'},
                    'response_data': {'status': 'success' if i % 2 == 0 else 'error'},
                    'error_details': f'示例错误详情{i+1}' if i % 2 != 0 else None
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'创建示例集成日志: {log.message}'))
        
        self.stdout.write(self.style.SUCCESS('WHartTest示例数据插入完成！'))
