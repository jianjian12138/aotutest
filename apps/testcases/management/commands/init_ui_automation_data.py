from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
import random

from apps.ui_automation.models import (
    UiProject, LocatorStrategy, Element, TestScript, 
    TestSuite, TestSuiteScript, TestExecution, Screenshot,
    ElementGroup, ScriptStep, TestCase, TestCaseStep, TestCaseExecution,
    TestSuiteTestCase
)

User = get_user_model()

class Command(BaseCommand):
    help = '初始化UI自动化测试数据'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('开始初始化UI自动化测试数据...'))
        
        # 创建或获取默认用户
        user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'password': 'admin123456'
            }
        )
        
        # 创建项目
        project, created = UiProject.objects.get_or_create(
            name='测试项目',
            defaults={
                'description': '用于UI自动化测试的项目',
                'owner': user,
                'status': 'active',
                'created_at': timezone.now(),
                'updated_at': timezone.now()
            }
        )
        
        # 创建定位策略
        locator_strategies = {
            'id': 'ID选择器',
            'name': '名称选择器',
            'class_name': '类选择器',
            'css': 'CSS选择器',
            'xpath': 'XPath选择器',
            'link_text': '链接文本',
            'partial_link_text': '部分链接文本',
            'tag_name': '标签名'
        }
        
        for strategy_name, description in locator_strategies.items():
            LocatorStrategy.objects.get_or_create(
                name=strategy_name,
                defaults={'description': description}
            )
        
        # 创建元素组
        element_groups = ['登录页面', '首页', '详情页', '设置页']
        groups = {}
        for group_name in element_groups:
            group, created = ElementGroup.objects.get_or_create(
                name=group_name,
                project=project,
                defaults={'description': f'{group_name}元素组'}
            )
            groups[group_name] = group
        
        # 创建元素
        elements_data = [
            {
                'name': '用户名输入框',
                'element_type': 'INPUT',
                'locator_value': '//input[@id="username"]',
                'group': groups['登录页面'],
                'page': 'login'
            },
            {
                'name': '密码输入框',
                'element_type': 'INPUT',
                'locator_value': '//input[@id="password"]',
                'group': groups['登录页面'],
                'page': 'login'
            },
            {
                'name': '登录按钮',
                'element_type': 'BUTTON',
                'locator_value': '//button[@id="login-btn"]',
                'group': groups['登录页面'],
                'page': 'login'
            },
            {
                'name': '首页标题',
                'element_type': 'TEXT',
                'locator_value': '//h1[@id="home-title"]',
                'group': groups['首页'],
                'page': 'home'
            },
            {
                'name': '详情页标题',
                'element_type': 'TEXT',
                'locator_value': '//h1[@id="detail-title"]',
                'group': groups['详情页'],
                'page': 'detail'
            }
        ]
        
        elements = []
        for element_data in elements_data:
            locator_strategy = LocatorStrategy.objects.get(name='xpath')
            element, created = Element.objects.get_or_create(
                name=element_data['name'],
                project=project,
                defaults={
                    'element_type': element_data['element_type'],
                    'locator_strategy': locator_strategy,
                    'locator_value': element_data['locator_value'],
                    'group': element_data['group'],
                    'page': element_data['page'],
                    'validation_status': 'VALID'
                }
            )
            elements.append(element)
        
        # 创建测试脚本
        scripts_data = [
            {
                'name': '登录脚本',
                'script_type': 'CODE',
                'language': 'python',
                'content': '# 登录脚本示例\n# 代码内容...'
            },
            {
                'name': '首页测试脚本',
                'script_type': 'CODE',
                'language': 'python',
                'content': '# 首页测试脚本示例\n# 代码内容...'
            }
        ]
        
        scripts = []
        for script_data in scripts_data:
            script, created = TestScript.objects.get_or_create(
                name=script_data['name'],
                project=project,
                defaults={
                    'script_type': script_data['script_type'],
                    'language': script_data['language'],
                    'content': script_data['content']
                }
            )
            scripts.append(script)
        
        # 创建测试用例
        test_cases_data = [
            {
                'name': '登录功能测试',
                'priority': 'high',
                'status': 'active'
            },
            {
                'name': '首页显示测试',
                'priority': 'medium',
                'status': 'active'
            },
            {
                'name': '详情页测试',
                'priority': 'medium',
                'status': 'draft'
            }
        ]
        
        test_cases = []
        for case_data in test_cases_data:
            test_case, created = TestCase.objects.get_or_create(
                name=case_data['name'],
                project=project,
                defaults={
                    'description': f'{case_data["name"]}的描述',
                    'priority': case_data['priority'],
                    'status': case_data['status'],
                    'created_by': user,
                    'created_at': timezone.now(),
                    'updated_at': timezone.now()
                }
            )
            test_cases.append(test_case)
        
        # 为测试用例添加步骤
        for test_case in test_cases:
            # 检查是否已有步骤，没有则添加
            if not test_case.steps.exists():
                step_count = random.randint(2, 5)
                for i in range(step_count):
                    TestCaseStep.objects.create(
                        test_case=test_case,
                        step_number=i + 1,
                        action_type=random.choice(['click', 'fill', 'wait', 'assert']),
                        element=random.choice(elements) if random.random() > 0.3 else None,
                        input_value=f'test_value_{i}' if random.choice(['click', 'fill', 'wait', 'assert']) == 'fill' else '',
                        wait_time=random.randint(500, 2000),
                        assert_type=random.choice(['equals', 'contains', 'exists']) if random.choice(['click', 'fill', 'wait', 'assert']) == 'assert' else '',
                        assert_value=f'expected_{i}' if random.choice(['click', 'fill', 'wait', 'assert']) == 'assert' else '',
                        description=f'Step {i + 1} for {test_case.name}'
                    )
        
        # 创建测试套件
        test_suites_data = [
            {'name': '冒烟测试套件', 'description': '基础功能冒烟测试'},
            {'name': '回归测试套件', 'description': '完整回归测试'}
        ]
        
        test_suites = []
        for suite_data in test_suites_data:
            test_suite, created = TestSuite.objects.get_or_create(
                name=suite_data['name'],
                project=project,
                defaults={
                    'description': suite_data['description'],
                    'created_at': timezone.now(),
                    'updated_at': timezone.now()
                }
            )
            test_suites.append(test_suite)
        
        # 为测试套件添加测试用例
        for test_suite in test_suites:
            # 为每个套件添加1-3个测试用例
            suite_test_cases = random.sample(test_cases, random.randint(1, 3))
            for i, test_case in enumerate(suite_test_cases):
                TestSuiteTestCase.objects.get_or_create(
                    test_suite=test_suite,
                    test_case=test_case,
                    defaults={'order': i + 1}
                )
        
        # 创建测试执行记录
        for _ in range(5):
            # 随机选择一个测试套件或测试脚本
            if random.random() > 0.5 and test_suites:
                test_suite = random.choice(test_suites)
                test_execution, created = TestExecution.objects.get_or_create(
                    project=project,
                    test_suite=test_suite,
                    defaults={
                        'executed_by': user,
                        'status': random.choice(['SUCCESS', 'FAILED', 'ABORTED']),
                        'started_at': timezone.now() - timezone.timedelta(minutes=random.randint(10, 120)),
                        'finished_at': timezone.now() - timezone.timedelta(minutes=random.randint(5, 60)),
                        'duration': random.randint(30, 300),
                        'engine': random.choice(['playwright', 'selenium']),
                        'browser': random.choice(['chrome', 'firefox', 'edge']),
                        'headless': True
                    }
                )
            elif scripts:
                test_script = random.choice(scripts)
                test_execution, created = TestExecution.objects.get_or_create(
                    project=project,
                    test_script=test_script,
                    defaults={
                        'executed_by': user,
                        'status': random.choice(['SUCCESS', 'FAILED', 'ABORTED']),
                        'started_at': timezone.now() - timezone.timedelta(minutes=random.randint(10, 120)),
                        'finished_at': timezone.now() - timezone.timedelta(minutes=random.randint(5, 60)),
                        'duration': random.randint(30, 300),
                        'engine': random.choice(['playwright', 'selenium']),
                        'browser': random.choice(['chrome', 'firefox', 'edge']),
                        'headless': True
                    }
                )
        
        # 创建测试用例执行记录
        for _ in range(10):
            test_case = random.choice(test_cases)
            test_case_execution, created = TestCaseExecution.objects.get_or_create(
                project=project,
                test_case=test_case,
                defaults={
                    'created_by': user,
                    'status': random.choice(['passed', 'failed', 'error']),
                    'started_at': timezone.now() - timezone.timedelta(minutes=random.randint(10, 120)),
                    'finished_at': timezone.now() - timezone.timedelta(minutes=random.randint(5, 60)),
                    'execution_time': random.randint(30, 300),
                    'engine': random.choice(['playwright', 'selenium']),
                    'browser': random.choice(['chrome', 'firefox', 'edge']),
                    'headless': True
                }
            )
        
        self.stdout.write(self.style.SUCCESS('UI自动化测试数据初始化完成！'))
