from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.users.models import User
from apps.projects.models import Project
from apps.testcases.models import TestCase
from apps.reviews.models import ReviewTemplate, TestCaseReview, ReviewAssignment

class Command(BaseCommand):
    help = 'Insert sample data for review templates and reviews'

    def handle(self, *args, **options):
        self.stdout.write('开始生成评审管理示例数据...')

        try:
            # 获取默认用户（通常是admin）
            admin_user = User.objects.filter(is_superuser=True).first()
            if not admin_user:
                admin_user = User.objects.order_by('-date_joined').first()
                if not admin_user:
                    self.stdout.write(self.style.ERROR('未找到用户，请先创建用户'))
                    return

            # 获取或创建示例项目
            project, created = Project.objects.get_or_create(
                name='示例项目',
                defaults={
                    'owner': admin_user,
                    'description': '用于测试评审管理的示例项目',
                    'status': 'active'
                }
            )
            if created:
                self.stdout.write(f'创建了示例项目: {project.name}')

            # 获取或创建测试用例
            testcase, created = TestCase.objects.get_or_create(
                title='示例测试用例',
                project=project,
                defaults={
                    'author': admin_user,
                    'description': '用于测试评审管理的示例测试用例',
                    'priority': 'medium',
                    'status': 'active',
                    'preconditions': '系统已登录',
                    'steps': '1. 点击按钮\n2. 输入内容\n3. 提交表单',
                    'expected_result': '表单提交成功',
                    'test_type': 'functional'
                }
            )
            if created:
                self.stdout.write(f'创建了示例测试用例: {testcase.title}')

            # 创建评审模板
            self.stdout.write('\n生成评审模板...')
            templates = [
                {
                    'name': '基础功能评审模板',
                    'description': '适用于基础功能的评审模板',
                    'checklist': [
                        '功能是否符合需求',
                        '用例是否覆盖所有场景',
                        '步骤描述是否清晰',
                        '预期结果是否明确',
                        '是否考虑了边界情况'
                    ],
                    'default_reviewers': [admin_user]
                },
                {
                    'name': '性能测试评审模板',
                    'description': '适用于性能测试的评审模板',
                    'checklist': [
                        '性能指标是否明确',
                        '测试环境是否合理',
                        '测试数据是否真实',
                        '监控指标是否全面',
                        '结果分析是否深入'
                    ],
                    'default_reviewers': [admin_user]
                },
                {
                    'name': '安全测试评审模板',
                    'description': '适用于安全测试的评审模板',
                    'checklist': [
                        '是否存在安全漏洞',
                        '认证机制是否安全',
                        '数据加密是否完整',
                        '权限控制是否合理',
                        '日志记录是否全面'
                    ],
                    'default_reviewers': [admin_user]
                }
            ]

            for template_data in templates:
                template, created = ReviewTemplate.objects.update_or_create(
                    name=template_data['name'],
                    defaults={
                        'description': template_data['description'],
                        'creator': admin_user,
                        'checklist': template_data['checklist'],
                        'is_active': True
                    }
                )
                template.project.add(project)
                for reviewer in template_data['default_reviewers']:
                    template.default_reviewers.add(reviewer)
                
                if created:
                    self.stdout.write(f'创建了评审模板: {template.name}')
                else:
                    self.stdout.write(f'更新了评审模板: {template.name}')

            # 创建评审列表
            self.stdout.write('\n生成评审列表...')
            reviews = [
                {
                    'title': '登录功能评审',
                    'description': '登录功能的测试用例评审',
                    'status': 'in_progress',
                    'priority': 'high',
                    'deadline': timezone.now() + timezone.timedelta(days=7)
                },
                {
                    'title': '注册功能评审',
                    'description': '注册功能的测试用例评审',
                    'status': 'pending',
                    'priority': 'medium',
                    'deadline': timezone.now() + timezone.timedelta(days=14)
                },
                {
                    'title': '搜索功能评审',
                    'description': '搜索功能的测试用例评审',
                    'status': 'approved',
                    'priority': 'low',
                    'deadline': timezone.now() + timezone.timedelta(days=30)
                },
                {
                    'title': '支付功能评审',
                    'description': '支付功能的测试用例评审',
                    'status': 'rejected',
                    'priority': 'urgent',
                    'deadline': timezone.now() + timezone.timedelta(days=5)
                }
            ]

            # 获取第一个评审模板
            template = ReviewTemplate.objects.first()

            for review_data in reviews:
                review, created = TestCaseReview.objects.update_or_create(
                    title=review_data['title'],
                    defaults={
                        'description': review_data['description'],
                        'creator': admin_user,
                        'status': review_data['status'],
                        'priority': review_data['priority'],
                        'deadline': review_data['deadline'],
                        'template': template
                    }
                )
                
                # 关联项目和测试用例
                review.projects.add(project)
                review.testcases.add(testcase)
                
                # 添加评审人员
                assignment, a_created = ReviewAssignment.objects.update_or_create(
                    review=review,
                    reviewer=admin_user,
                    defaults={
                        'status': 'in_progress' if review.status == 'in_progress' else 'pending',
                        'comment': '这是一条示例评审意见'
                    }
                )
                
                if created:
                    self.stdout.write(f'创建了评审: {review.title}')
                else:
                    self.stdout.write(f'更新了评审: {review.title}')

            self.stdout.write('\n' + self.style.SUCCESS('评审管理示例数据生成完成！'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'生成示例数据失败: {e}'))
            import traceback
            traceback.print_exc()