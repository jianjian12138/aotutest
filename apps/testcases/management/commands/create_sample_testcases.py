from django.core.management.base import BaseCommand
from apps.users.models import User
from apps.projects.models import Project, ProjectMember
from apps.testcases.models import TestCase

class Command(BaseCommand):
    help = 'Create sample test cases for current users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Username to create sample data for (optional)',
        )

    def handle(self, *args, **options):
        username = options.get('username')
        
        if username:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User "{username}" not found.'))
                return
        else:
            # 获取最后一个注册的用户（通常是刚注册的测试用户）
            user = User.objects.order_by('-date_joined').first()
            if not user:
                self.stdout.write(self.style.ERROR('No users found. Please create a user first.'))
                return
        
        self.stdout.write(f'Creating sample data for user: {user.username}')
        
        try:
            # 创建或获取项目，确保用户是项目的所有者
            project, created = Project.objects.get_or_create(
                name="测试项目",
                defaults={
                    'owner': user,
                    'description': '用于测试的示例项目',
                    'status': 'active'
                }
            )
            
            # 如果项目已存在但不是当前用户的，将用户添加为项目成员
            if not created and project.owner != user:
                ProjectMember.objects.get_or_create(
                    project=project,
                    user=user,
                    defaults={'role': 'admin'}
                )
                self.stdout.write(f'Added {user.username} as member to existing project: {project.name}')
            elif created:
                self.stdout.write(f'Created new project: {project.name} for {user.username}')
            else:
                self.stdout.write(f'Using existing project: {project.name} owned by {user.username}')
            
            # 删除该项目下已存在的示例数据，避免重复
            TestCase.objects.filter(project=project, title__contains='测试').delete()
            
            # 创建示例测试用例
            test_cases_data = [
                {
                    'title': '用户登录功能测试',
                    'description': '测试用户登录功能是否正常工作',
                    'preconditions': '用户已注册账号',
                    'expected_result': '用户能够成功登录系统',
                    'priority': 'high',
                    'test_type': 'functional',
                    'status': 'active'
                },
                {
                    'title': '用户注册功能测试',
                    'description': '测试用户注册功能',
                    'preconditions': '系统正常运行',
                    'expected_result': '用户能够成功注册新账号',
                    'priority': 'critical',
                    'test_type': 'functional',
                    'status': 'active'
                },
                {
                    'title': 'API接口性能测试',
                    'description': '测试API接口的响应性能',
                    'preconditions': 'API服务已启动',
                    'expected_result': '接口响应时间在500ms以内',
                    'priority': 'medium',
                    'test_type': 'performance',
                    'status': 'draft'
                },
                {
                    'title': '数据库连接测试',
                    'description': '测试应用与数据库的连接是否正常',
                    'preconditions': '数据库服务已启动',
                    'expected_result': '应用能够正常连接并操作数据库',
                    'priority': 'high',
                    'test_type': 'integration',
                    'status': 'active'
                },
                {
                    'title': '前端页面加载测试',
                    'description': '测试前端页面是否能正常加载显示',
                    'preconditions': '前端服务已启动',
                    'expected_result': '页面在3秒内完成加载',
                    'priority': 'medium',
                    'test_type': 'ui',
                    'status': 'active'
                }
            ]
            
            created_count = 0
            for case_data in test_cases_data:
                testcase = TestCase.objects.create(
                    project=project,
                    author=user,
                    **case_data
                )
                created_count += 1
                self.stdout.write(f'Created test case: {testcase.title}')
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created {created_count} test cases for {user.username}')
            )
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating sample data: {e}'))