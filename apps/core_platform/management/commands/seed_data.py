"""
Django Management Command: seed_data
Populates the database with realistic sample data for all modules.
Usage: python manage.py seed_data
"""
from apps.notifications.models import NotificationConfig, NotificationLog
import random
import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

User = get_user_model()


class Command(BaseCommand):
    help = '为所有菜单模块填充示例演示数据'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='清除现有示例数据后重新创建',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('[SEED] 开始填充示例数据...'))

        # Get or create admin user
        admin, _ = User.objects.get_or_create(
            username='admin',
            defaults={
                'is_staff': True,
                'is_superuser': True,
                'email': 'admin@testing.com',
                'first_name': '系统',
                'last_name': '管理员',
            }
        )
        if not admin.has_usable_password():
            admin.set_password('admin123456')
            admin.save()

        # Create demo users
        users = self._seed_users(admin)
        self.stdout.write(self.style.SUCCESS('  [OK] 用户数据完成'))

        # Seed core platform: projects & versions
        projects, versions = self._seed_projects_and_versions(admin, users)
        self.stdout.write(self.style.SUCCESS('  [OK] 项目与版本数据完成'))

        # Seed test cases
        testcases = self._seed_testcases(projects, admin, users, versions)
        self.stdout.write(self.style.SUCCESS('  [OK] 测试用例数据完成'))

        # Seed test suites
        testsuites = self._seed_testsuites(projects, admin, testcases)
        self.stdout.write(self.style.SUCCESS('  [OK] 测试套件数据完成'))

        # Seed test plans & executions
        self._seed_test_plans_and_runs(projects, admin, users, versions, testcases)
        self.stdout.write(self.style.SUCCESS('  [OK] 测试计划与执行数据完成'))

        # Seed API testing
        self._seed_api_testing(admin, users)
        self.stdout.write(self.style.SUCCESS('  [OK] API测试数据完成'))

        # Seed review templates & reviews
        self._seed_reviews(projects, admin, users, testcases)
        self.stdout.write(self.style.SUCCESS('  [OK] 评审数据完成'))

        # Seed unified management: notifications, scheduler
        self._seed_unified_management(admin, users)
        self.stdout.write(self.style.SUCCESS('  [OK] 统一管理数据完成'))

        # Seed configuration
        self._seed_configuration(projects, admin)
        # Seed UI automation projects
        self._seed_ui_automation(admin, users)
        self.stdout.write(self.style.SUCCESS('  [OK] UI自动化项目数据完成'))

        # Seed Performance testing projects
        self._seed_performance_test(admin, users)
        self.stdout.write(self.style.SUCCESS('  [OK] 性能测试项目数据完成'))

        # Seed Security testing projects
        self._seed_security_test(admin, users)
        self.stdout.write(self.style.SUCCESS('  [OK] 安全测试项目数据完成'))

        self.stdout.write(self.style.SUCCESS('\n[DONE] 所有示例数据填充完成！'))
        self.stdout.write(self.style.NOTICE('  访问 http://localhost:5656 查看效果'))

    # =============================================
    # USERS
    # =============================================
    def _seed_users(self, admin):
        demo_users_data = [
            ('zhangsan', '张三', '张', '三', 'zhangsan@testing.com', '质量保障部', '高级测试工程师'),
            ('lisi', '李四', '李', '四', 'lisi@testing.com', '研发部', '软件开发工程师'),
            ('wangwu', '王五', '王', '五', 'wangwu@testing.com', '质量保障部', '测试负责人'),
            ('zhaoliu', '赵六', '赵', '六', 'zhaoliu@testing.com', '产品部', '产品经理'),
            ('sunqi', '孙七', '孙', '七', 'sunqi@testing.com', '研发部', '前端工程师'),
        ]
        users = [admin]
        for username, full_name, last, first, email, dept, pos in demo_users_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': first,
                    'last_name': last,
                    'department': dept,
                    'position': pos,
                }
            )
            if created:
                user.set_password('test123456')
                user.save()
            users.append(user)
        return users

    # =============================================
    # PROJECTS & VERSIONS
    # =============================================
    def _seed_projects_and_versions(self, admin, users):
        from apps.core_platform.models import Project, ProjectMember, Version

        projects_data = [
            ('电商平台测试项目', '负责电商平台核心业务的全面测试，包含用户、订单、支付等模块。', 'API', 'active'),
            ('移动应用UI自动化', '覆盖Android/iOS双端的UI自动化测试，保障移动端用户体验。', 'UI', 'active'),
            ('支付系统性能测试', '针对支付系统的高并发、大吞吐量场景进行系统性性能评估。', 'PERFORMANCE', 'active'),
            ('用户中台通用测试', '用户身份认证、权限管理等通用功能的集成测试项目。', 'GENERAL', 'active'),
            ('推荐引擎测试', '针对个性化推荐算法和服务的功能与性能测试。', 'API', 'paused'),
        ]

        projects = []
        for name, desc, ptype, status in projects_data:
            project, _ = Project.objects.get_or_create(
                name=name,
                defaults={
                    'description': desc,
                    'project_type': ptype,
                    'status': status,
                    'owner': admin,
                }
            )
            # Add members
            roles = ['owner', 'admin', 'developer', 'tester', 'viewer']
            for i, user in enumerate(users[:5]):
                ProjectMember.objects.get_or_create(
                    project=project,
                    user=user,
                    defaults={'role': roles[i % len(roles)]}
                )
            projects.append(project)

        versions_data = [
            ('v1.0.0', '产品首个正式版本，包含核心功能', True),
            ('v1.1.0', '第一个迭代版本，修复若干已知缺陷', False),
            ('v2.0.0', '重大版本升级，引入新架构', False),
            ('v2.1.0-beta', '2.1.0 beta预发布版本', False),
        ]
        versions = []
        for name, desc, is_baseline in versions_data:
            version, _ = Version.objects.get_or_create(
                name=name,
                defaults={
                    'description': desc,
                    'is_baseline': is_baseline,
                    'created_by': admin,
                }
            )
            version.projects.set(projects[:3])
            versions.append(version)

        return projects, versions

    # =============================================
    # TEST CASES
    # =============================================
    def _seed_testcases(self, projects, admin, users, versions):
        from apps.testcases.models import TestCase, TestCaseStep

        testcase_data = [
            # (title, priority, status, test_type, steps, expected, tags)
            ('用户登录功能验证', 'high', 'active', 'functional',
             '1. 打开登录页面\n2. 输入正确的用户名和密码\n3. 点击登录按钮',
             '登录成功，跳转到首页，显示用户欢迎信息', ['认证', '登录', '核心功能']),
            ('购物车商品数量边界测试', 'medium', 'active', 'functional',
             '1. 进入商品详情页\n2. 将购买数量设为0\n3. 点击加入购物车',
             '系统提示数量不能为零，无法加入购物车', ['购物车', '边界值', '电商']),
            ('支付接口响应时间测试', 'critical', 'active', 'performance',
             '1. 并发100个用户发起支付请求\n2. 记录每个请求的响应时间',
             '99%的请求响应时间在500ms以内，无超时错误', ['性能', '支付', 'P0']),
            ('用户注册输入校验', 'medium', 'active', 'functional',
             '1. 打开注册页面\n2. 输入非法格式的邮箱地址\n3. 点击注册',
             '系统显示邮箱格式不正确的错误提示，不提交表单', ['注册', '输入校验', '用户']),
            ('搜索功能SQL注入防护', 'high', 'active', 'security',
             '1. 在搜索框输入 SQL 注入字符串\n2. 提交搜索',
             '系统正常返回空结果或无关结果，不执行注入的SQL', ['安全', '搜索', 'SQL注入']),
            ('订单状态流转验证', 'high', 'active', 'functional',
             '1. 创建一个新订单\n2. 完成支付\n3. 确认收货',
             '订单状态依次变为：待支付 → 待发货 → 已发货 → 已完成', ['订单', '状态流转', '核心功能']),
            ('商品分类接口测试', 'low', 'active', 'api',
             '1. 调用GET /api/categories\n2. 检查返回数据结构',
             '接口返回200状态码，包含id、name、children字段', ['API', '商品', '分类']),
            ('首页Banner UI自动化', 'medium', 'draft', 'ui',
             '1. 打开首页\n2. 等待Banner加载完成\n3. 验证Banner图片和文字',
             'Banner正常显示，图片加载完成，文字清晰可读', ['UI', '首页', 'Banner']),
            ('用户权限隔离测试', 'high', 'active', 'security',
             '1. 以普通用户身份登录\n2. 尝试访问管理员专属页面',
             '系统返回403禁止访问错误，不显示管理员内容', ['安全', '权限', '认证']),
            ('大批量数据导出性能', 'medium', 'active', 'performance',
             '1. 选择10万条数据\n2. 点击导出Excel\n3. 等待下载完成',
             '导出操作在30秒内完成，文件数据完整无误', ['性能', '导出', '大数据']),
        ]

        testcases = []
        for i, (title, priority, status, ttype, steps, expected, tags) in enumerate(testcase_data):
            project = projects[i % len(projects)]
            author = users[i % len(users)]
            tc, created = TestCase.objects.get_or_create(
                title=title,
                project=project,
                defaults={
                    'description': f'{title}的详细描述，确保测试覆盖该功能的所有边界情况和正常流程。',
                    'preconditions': '系统正常运行，测试账号已创建，测试数据已准备就绪。',
                    'steps': steps,
                    'expected_result': expected,
                    'priority': priority,
                    'status': status,
                    'test_type': ttype,
                    'tags': tags,
                    'author': author,
                }
            )
            if created and versions:
                tc.versions.set(versions[:2])

            # Add step details
            if created:
                step_lines = steps.split('\n')
                for j, line in enumerate(step_lines):
                    line = line.strip().lstrip(f'{j+1}. ').strip()
                    TestCaseStep.objects.get_or_create(
                        testcase=tc,
                        step_number=j + 1,
                        defaults={
                            'action': line,
                            'expected': expected if j == len(step_lines) - 1 else '步骤执行成功'
                        }
                    )
            testcases.append(tc)

        return testcases

    # =============================================
    # TEST SUITES
    # =============================================
    def _seed_testsuites(self, projects, admin, testcases):
        from apps.testsuites.models import TestSuite, TestSuiteCase

        suites_data = [
            ('核心功能冒烟测试套件', '包含所有核心业务功能的冒烟测试，每次发版必跑。', 0),
            ('安全与权限测试套件', '覆盖系统所有安全相关、权限相关的测试用例。', 1),
            ('API接口全量测试套件', '系统所有API接口的功能和边界测试。', 2),
            ('性能基准测试套件', '系统关键性能指标的测试基线套件。', 3),
        ]

        suites = []
        for name, desc, proj_idx in suites_data:
            project = projects[proj_idx % len(projects)]
            suite, created = TestSuite.objects.get_or_create(
                name=name,
                project=project,
                defaults={
                    'description': desc,
                    'author': admin,
                }
            )
            if created:
                # Add some testcases to suite
                cases_to_add = testcases[:5]
                for order, tc in enumerate(cases_to_add):
                    TestSuiteCase.objects.get_or_create(
                        testsuite=suite,
                        testcase=tc,
                        defaults={'order': order}
                    )
            suites.append(suite)

        return suites

    # =============================================
    # TEST PLANS & RUNS
    # =============================================
    def _seed_test_plans_and_runs(self, projects, admin, users, versions, testcases):
        from apps.executions.models import TestPlan, TestRun, TestRunCase

        plans_data = [
            ('v1.0.0 发版测试计划', '1.0.0版本正式发版前的全量测试计划'),
            ('Sprint 12 回归测试计划', 'Sprint 12迭代的回归测试计划，覆盖本次迭代所有变更'),
            ('每日冒烟测试计划', '每日构建后的自动化冒烟测试计划'),
        ]

        statuses = ['untested', 'in_progress', 'completed']
        run_case_statuses = ['passed', 'failed', 'untested', 'passed', 'passed', 'blocked']

        for i, (name, desc) in enumerate(plans_data):
            project = projects[i % len(projects)]
            version = versions[i % len(versions)] if versions else None
            plan, _ = TestPlan.objects.get_or_create(
                name=name,
                defaults={
                    'description': desc,
                    'creator': admin,
                    'version': version,
                }
            )
            plan.projects.set([project])
            plan.assignees.set(users[:3])

            # Create test runs for each plan
            runs_data = [
                (f'{name} - 第一轮执行', statuses[i % len(statuses)]),
                (f'{name} - 回归轮次', 'completed'),
            ]
            for run_name, run_status in runs_data:
                run, created = TestRun.objects.get_or_create(
                    name=run_name,
                    test_plan=plan,
                    defaults={
                        'description': f'{run_name}的执行批次',
                        'project': project,
                        'version': version,
                        'assignee': users[i % len(users)],
                        'creator': admin,
                        'status': run_status,
                        'started_at': timezone.now() - timedelta(days=random.randint(1, 10)),
                        'completed_at': timezone.now() - timedelta(hours=random.randint(1, 5)) if run_status == 'completed' else None,
                    }
                )
                if created:
                    for j, tc in enumerate(testcases[:6]):
                        try:
                            TestRunCase.objects.get_or_create(
                                test_run=run,
                                testcase=tc,
                                defaults={
                                    'status': run_case_statuses[j % len(run_case_statuses)],
                                    'priority': tc.priority,
                                    'actual_result': '实际结果与预期一致' if run_case_statuses[j % len(run_case_statuses)] == 'passed' else '发现异常，见缺陷报告 BUG-001',
                                    'executed_by': users[j % len(users)],
                                    'executed_at': timezone.now() - timedelta(hours=j),
                                }
                            )
                        except Exception:
                            pass

    # =============================================
    # API TESTING
    # =============================================
    def _seed_api_testing(self, admin, users):
        from apps.api_testing.models import (
            ApiProject, ApiCollection, ApiRequest, Environment,
            ApiTestCase, ApiTestCaseStep, TestSuite as ApiTestSuite
        )

        # Create API projects
        api_projects_data = [
            ('电商平台API', 'HTTP', 'IN_PROGRESS', '电商平台后端API接口测试项目'),
            ('用户中台API', 'HTTP', 'IN_PROGRESS', '用户身份与权限管理API测试项目'),
            ('推荐引擎API', 'HTTP', 'NOT_STARTED', '个性化推荐服务API测试项目'),
        ]
        api_projects = []
        for name, ptype, status, desc in api_projects_data:
            proj, created = ApiProject.objects.get_or_create(
                name=name,
                defaults={
                    'description': desc,
                    'project_type': ptype,
                    'status': status,
                    'owner': admin,
                }
            )
            if created:
                proj.members.set(users[:3])
            api_projects.append(proj)

        # Create environments
        for api_project in api_projects:
            Environment.objects.get_or_create(
                name='测试环境',
                project=api_project,
                defaults={
                    'scope': 'LOCAL',
                    'variables': {'BASE_URL': 'http://test-api.example.com', 'TOKEN': 'demo-token-xyz'},
                    'is_active': True,
                    'created_by': admin,
                }
            )
            Environment.objects.get_or_create(
                name='生产环境',
                project=api_project,
                defaults={
                    'scope': 'LOCAL',
                    'variables': {'BASE_URL': 'https://api.example.com', 'TOKEN': ''},
                    'is_active': False,
                    'created_by': admin,
                }
            )

        # Create collections and API requests
        api_project = api_projects[0]
        collections_data = [
            ('用户模块', '用户注册、登录、个人信息相关接口'),
            ('商品模块', '商品查询、分类、详情相关接口'),
            ('订单模块', '订单创建、查询、状态更新相关接口'),
            ('购物车模块', '购物车增删改查相关接口'),
        ]
        collections = []
        for name, desc in collections_data:
            coll, _ = ApiCollection.objects.get_or_create(
                name=name,
                project=api_project,
                defaults={'description': desc}
            )
            collections.append(coll)

        requests_data = [
            (collections[0], 'POST', '/api/auth/login', '用户登录', {'Content-Type': 'application/json'},
             {'username': 'demo', 'password': '123456'}, [{'type': 'status_code', 'expected': 200}]),
            (collections[0], 'POST', '/api/auth/register', '用户注册', {'Content-Type': 'application/json'},
             {'username': 'newuser', 'email': 'new@test.com', 'password': 'pass123'}, [{'type': 'status_code', 'expected': 201}]),
            (collections[0], 'GET', '/api/users/me', '获取当前用户信息', {'Authorization': 'Bearer {{TOKEN}}'},
             {}, [{'type': 'status_code', 'expected': 200}, {'type': 'json_path', 'path': '$.username', 'expected': 'admin'}]),
            (collections[1], 'GET', '/api/products', '获取商品列表', {},
             {}, [{'type': 'status_code', 'expected': 200}]),
            (collections[1], 'GET', '/api/products/1', '获取商品详情', {},
             {}, [{'type': 'status_code', 'expected': 200}, {'type': 'json_path', 'path': '$.id', 'expected': 1}]),
            (collections[2], 'POST', '/api/orders', '创建订单', {'Content-Type': 'application/json'},
             {'items': [{'product_id': 1, 'quantity': 2}]}, [{'type': 'status_code', 'expected': 201}]),
            (collections[2], 'GET', '/api/orders', '获取订单列表', {},
             {}, [{'type': 'status_code', 'expected': 200}]),
            (collections[3], 'POST', '/api/cart/add', '加入购物车', {'Content-Type': 'application/json'},
             {'product_id': 1, 'quantity': 1}, [{'type': 'status_code', 'expected': 200}]),
        ]
        api_requests = []
        for order, (coll, method, url, name, headers, body, assertions) in enumerate(requests_data):
            req, _ = ApiRequest.objects.get_or_create(
                name=name,
                collection=coll,
                defaults={
                    'method': method,
                    'url': url,
                    'headers': headers,
                    'body': {'type': 'json', 'content': body} if body else {},
                    'assertions': assertions,
                    'order': order,
                    'created_by': admin,
                }
            )
            api_requests.append(req)

        # Create API test cases
        test_cases_data = [
            ('登录流程端到端测试', 'high', 'ready', '验证用户从注册到登录的完整流程'),
            ('商品浏览与下单流程', 'high', 'passed', '验证用户从浏览商品到成功下单的完整流程'),
            ('购物车异常场景测试', 'medium', 'draft', '测试购物车在各种边界场景下的行为'),
        ]
        for name, priority, status, desc in test_cases_data:
            tc, created = ApiTestCase.objects.get_or_create(
                name=name,
                project=api_project,
                defaults={
                    'description': desc,
                    'priority': priority,
                    'status': status,
                    'created_by': admin,
                }
            )
            if created and api_requests:
                for step_num, req in enumerate(api_requests[:3], start=1):
                    try:
                        ApiTestCaseStep.objects.get_or_create(
                            test_case=tc,
                            step_number=step_num,
                            defaults={
                                'name': f'步骤{step_num}: {req.name}',
                                'api_request': req,
                                'method': req.method,
                                'url': req.url,
                                'assertions': req.assertions,
                            }
                        )
                    except Exception:
                        pass

    # =============================================
    # REVIEWS
    # =============================================
    def _seed_reviews(self, projects, admin, users, testcases):
        from apps.reviews.models import ReviewTemplate, TestCaseReview, ReviewAssignment

        # Create review templates
        templates_data = [
            ('功能测试用例评审模板', '适用于功能测试用例的标准评审清单', [
                {'id': 1, 'item': '用例标题是否清晰描述测试目的', 'required': True},
                {'id': 2, 'item': '前置条件是否完整且可重现', 'required': True},
                {'id': 3, 'item': '测试步骤是否详细且无歧义', 'required': True},
                {'id': 4, 'item': '预期结果是否可验证', 'required': True},
                {'id': 5, 'item': '是否覆盖正向和反向场景', 'required': False},
            ]),
            ('API测试用例评审模板', '适用于API接口测试用例的评审标准', [
                {'id': 1, 'item': '接口URL和HTTP方法是否正确', 'required': True},
                {'id': 2, 'item': '请求参数是否包含所有边界情况', 'required': True},
                {'id': 3, 'item': '断言规则是否完整', 'required': True},
                {'id': 4, 'item': '是否包含鉴权异常测试', 'required': False},
            ]),
            ('性能测试用例评审模板', '适用于性能和压力测试场景的评审', [
                {'id': 1, 'item': '并发用户数是否符合实际业务场景', 'required': True},
                {'id': 2, 'item': '性能指标（TPS、RT）是否有明确阈值', 'required': True},
                {'id': 3, 'item': '测试持续时间是否合理', 'required': True},
            ]),
        ]
        templates = []
        for name, desc, checklist in templates_data:
            template, _ = ReviewTemplate.objects.get_or_create(
                name=name,
                defaults={
                    'description': desc,
                    'checklist': checklist,
                    'creator': admin,
                    'is_active': True,
                }
            )
            template.project.set(projects[:2])
            if users:
                template.default_reviewers.set(users[:3])
            templates.append(template)

        # Create reviews
        reviews_data = [
            ('v1.0.0 核心用例评审', 'pending', 'high', templates[0]),
            ('Sprint 12 API用例评审', 'in_progress', 'medium', templates[1]),
            ('性能测试用例评审', 'approved', 'low', templates[2]),
            ('登录安全用例专项评审', 'rejected', 'urgent', templates[0]),
        ]
        for title, status, priority, template in reviews_data:
            review, created = TestCaseReview.objects.get_or_create(
                title=title,
                defaults={
                    'description': f'{title}的详细说明，请评审人仔细核对每个测试用例。',
                    'creator': admin,
                    'template': template,
                    'status': status,
                    'priority': priority,
                    'deadline': timezone.now() + timedelta(days=7),
                }
            )
            if created:
                review.projects.set(projects[:2])
                if testcases:
                    review.testcases.set(testcases[:5])
                # Add reviewers
                for reviewer in users[1:4]:
                    ReviewAssignment.objects.get_or_create(
                        review=review,
                        reviewer=reviewer,
                        defaults={
                            'status': 'approved' if status == 'approved' else 'pending',
                            'comment': '用例描述清晰，逻辑完整，建议通过。' if status == 'approved' else '',
                        }
                    )

    # =============================================
    # UNIFIED MANAGEMENT: NOTIFICATIONS & SCHEDULER
    # =============================================
    def _seed_unified_management(self, admin, users):
        from apps.scheduler.models import ScheduledTask
        from apps.core_platform.models import Project

        # Get all projects
        projects = Project.objects.all()
        if not projects:
            return

        # Notification configs
        configs_data = [
            ('飞书测试群通知', 'webhook_feishu', 'https://open.feishu.cn/open-apis/bot/v2/hook/demo-key'),
            ('企业微信告警通知', 'webhook_wechat', 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=demo-key'),
            ('钉钉CI/CD通知', 'webhook_dingtalk', 'https://oapi.dingtalk.com/robot/send?access_token=demo-token'),
        ]
        for name, config_type, webhook_url in configs_data:
            NotificationConfig.objects.get_or_create(
                name=name,
                defaults={
                    'config_type': config_type,
                    'webhook_url': webhook_url,
                    'is_active': True,
                    'description': f'{name} - 用于自动化测试结果通知',
                    'project': random.choice(projects),
                    'created_by': admin,
                }
            )

        # Scheduler tasks
        tasks_data = [
            ('每日 API 冒烟测试', 'API', 'CRON', '0 9 * * *', 'ACTIVE', 15, 14),
            ('每周全量 UI 回归', 'UI', 'CRON', '0 22 * * 5', 'ACTIVE', 8, 7),
            ('每小时接口健康检查', 'API', 'INTERVAL', None, 'ACTIVE', 48, 47),
            ('上线前性能测试（单次）', 'PERFORMANCE', 'ONCE', None, 'PAUSED', 2, 2),
            ('推荐引擎核心链路压测', 'PERFORMANCE', 'INTERVAL', None, 'ACTIVE', 120, 118),
            ('移动端周常稳定性测试', 'UI', 'CRON', '0 0 * * 0', 'ACTIVE', 52, 50),
        ]
        for name, ttype, trigger, cron, status, total_runs, success_runs in tasks_data:
            task_defaults = {
                'description': f'{name}的自动化调度任务',
                'task_type': ttype,
                'trigger_type': trigger,
                'status': status,
                'total_runs': total_runs,
                'successful_runs': success_runs,
                'failed_runs': total_runs - success_runs,
                'last_run_time': timezone.now() - timedelta(hours=random.randint(1, 24)),
                'next_run_time': timezone.now() + timedelta(hours=random.randint(1, 12)),
                'notify_on_success': False,
                'notify_on_failure': True,
                'project': random.choice(projects),
                'created_by': admin,
            }
            if cron:
                task_defaults['cron_expression'] = cron
            if trigger == 'INTERVAL':
                task_defaults['interval_seconds'] = 3600
            if trigger == 'ONCE':
                task_defaults['execute_at'] = timezone.now() + timedelta(days=1)
            ScheduledTask.objects.get_or_create(name=name, defaults=task_defaults)

        # Seed environments, suites and reports for all projects
        self._seed_project_metadata(projects, admin, users)

    def _seed_project_metadata(self, projects, admin, users):
        from apps.core_platform.models import ProjectEnvironment
        from apps.testsuites.models import TestSuite
        from apps.reports.models import TestReport
        from apps.executions.models import TestRun

        for project in projects:
            # Environments
            envs = [
                ('开发环境', f'http://dev-{project.id}.example.com', True),
                ('测试环境', f'http://test-{project.id}.example.com', False),
                ('预发布环境', f'http://stg-{project.id}.example.com', False),
            ]
            for name, url, is_default in envs:
                ProjectEnvironment.objects.get_or_create(
                    project=project,
                    name=name,
                    defaults={
                        'base_url': url,
                        'is_default': is_default,
                        'description': f'{project.name}的{name}'
                    }
                )

            # Test Suites (especially for Project 5 '推荐引擎测试')
            if project.name == '推荐引擎测试' or random.random() > 0.5:
                suites_data = [
                    ('核心冒烟套件', '包含本项目最核心的冒烟测试用例'),
                    ('全量回归套件', '项目所有功能模块的全量回归测试'),
                ]
                for sname, sdesc in suites_data:
                    TestSuite.objects.get_or_create(
                        project=project,
                        name=sname,
                        defaults={
                            'description': sdesc,
                            'author': admin
                        }
                    )

            # Reports
            if project.name == '推荐引擎测试' or random.random() > 0.7:
                for i in range(3):
                    report_name = f'{project.name}_自动化测试报告_{timezone.now().strftime("%Y%m%d")}_{i+1}'
                    TestReport.objects.create(
                        project=project,
                        name=report_name,
                        report_type='execution',
                        summary={
                            'total': 100,
                            'passed': 95 + i,
                            'failed': 5 - i,
                            'skipped': 0,
                            'duration': 120 + i * 10
                        },
                        generated_by=admin
                    )

    # =============================================
    # CONFIGURATION
    # =============================================
    def _seed_configuration(self, projects, admin):
        from apps.core_platform.models import GlobalParameter, CommonMethod

        params_data = [
            ('BASE_URL', 'https://api.example.com', '全局API基础URL，供各测试用例调用'),
            ('DEFAULT_TIMEOUT', '30000', '默认请求超时时间（毫秒）'),
            ('API_VERSION', 'v2', '当前API版本号'),
            ('RETRY_COUNT', '3', '接口请求失败时的重试次数'),
            ('TEST_USER_TOKEN', 'eyJhbGciOiJSUzI1NiJ9.demo.signature', '测试用账号的认证Token'),
            ('MAX_CONCURRENT', '100', '并发测试最大并发用户数'),
        ]
        for key, value, desc in params_data:
            GlobalParameter.objects.get_or_create(
                key=key,
                defaults={
                    'value': value,
                    'description': desc,
                    'project': projects[0] if projects else None,
                    'created_by': admin,
                }
            )

        methods_data = [
            ('获取认证Token', 'get_auth_token', '调用登录接口获取并返回认证Token，供后续接口使用。',
             'import requests\nresp = requests.post(f"{BASE_URL}/auth/login", json={"username":"admin","password":"pass"})\nreturn resp.json()["token"]'),
            ('生成随机用户名', 'random_username', '生成一个随机用户名，格式为 user_XXXXX',
             'import random, string\nreturn "user_" + "".join(random.choices(string.digits, k=5))'),
            ('等待并检查', 'wait_and_check', '等待指定毫秒后执行断言检查',
             'import time\ntime.sleep(ms / 1000)\nassert condition, message'),
            ('格式化时间戳', 'format_timestamp', '将Unix时间戳格式化为可读的日期时间字符串',
             'from datetime import datetime\nreturn datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")'),
        ]
        for name, keyword, desc, code in methods_data:
            CommonMethod.objects.get_or_create(
                keyword=keyword,
                defaults={
                    'name': name,
                    'description': desc,
                    'code_snippet': code,
                    'project': projects[0] if projects else None,
                    'created_by': admin,
                }
            )

    # =============================================
    # UI AUTOMATION
    # =============================================
    def _seed_ui_automation(self, admin, users):
        from apps.ui_automation.models import UiProject, LocatorStrategy, ElementGroup, Element

        ui_projects_data = [
            ('移动应用UI自动化', '覆盖Android/iOS双端的UI自动化测试项目', 'IN_PROGRESS', 'http://mobile.example.com'),
            ('电商平台UI测试', '电商平台 Web 端核心业务流自动化测试', 'IN_PROGRESS', 'http://mall.example.com'),
        ]

        ui_projects = []
        for name, desc, status, base_url in ui_projects_data:
            proj, created = UiProject.objects.get_or_create(
                name=name,
                defaults={
                    'description': desc,
                    'status': status,
                    'base_url': base_url,
                    'owner': admin,
                }
            )
            if created:
                proj.members.set(users[:3])
            ui_projects.append(proj)

        # Locator strategies
        strategies = ['ID', 'CSS', 'XPath', 'Name', 'Link Text', 'Partial Link Text']
        strategy_objs = []
        for sname in strategies:
            strategy, _ = LocatorStrategy.objects.get_or_create(name=sname)
            strategy_objs.append(strategy)

        # Element groups (Pages)
        if ui_projects:
            proj = ui_projects[0]
            pages_data = [
                ('登录页', '系统登录页面'),
                ('首页', '登录后的主页面'),
                ('购物车页', '电商购物车详情页'),
            ]
            for pname, pdesc in pages_data:
                group, created = ElementGroup.objects.get_or_create(
                    name=pname,
                    project=proj,
                    defaults={'description': pdesc}
                )
                if created:
                    # Add some elements
                    Element.objects.get_or_create(
                        name='用户名输入框',
                        project=proj,
                        defaults={
                            'group': group,
                            'element_type': 'INPUT',
                            'locator_strategy': strategy_objs[1], # CSS
                            'locator_value': '#username',
                            'page': pname
                        }
                    )
                    Element.objects.get_or_create(
                        name='密码输入框',
                        project=proj,
                        defaults={
                            'group': group,
                            'element_type': 'INPUT',
                            'locator_strategy': strategy_objs[1], # CSS
                            'locator_value': '#password',
                            'page': pname
                        }
                    )
                    Element.objects.get_or_create(
                        name='登录按钮',
                        project=proj,
                        defaults={
                            'group': group,
                            'element_type': 'BUTTON',
                            'locator_strategy': strategy_objs[0], # ID
                            'locator_value': 'login-btn',
                            'page': pname
                        }
                    )

    # =============================================
    # PERFORMANCE TESTING
    # =============================================
    def _seed_performance_test(self, admin, users):
        from apps.performance_test.models import PerformanceProject, PerformanceEnvironment

        perf_projects_data = [
            ('支付系统性能测试', '针对支付系统高并发场景的压力测试项目', 'IN_PROGRESS'),
            ('核心接口性能基准', '全系统核心 API 的性能基准持续监控', 'IN_PROGRESS'),
        ]

        for name, desc, status in perf_projects_data:
            proj, created = PerformanceProject.objects.get_or_create(
                name=name,
                defaults={
                    'description': desc,
                    'status': status,
                    'owner': admin,
                }
            )
            if created:
                proj.members.set(users[:3])
                
                # Create default environment
                PerformanceEnvironment.objects.get_or_create(
                    name='性能测试集群',
                    project=proj,
                    defaults={
                        'scope': 'PROJECT',
                        'variables': {'TARGET_HOST': 'http://perf-target.example.com'},
                        'is_active': True,
                        'created_by': admin
                    }
                )

    # =============================================
    # SECURITY TESTING
    # =============================================
    def _seed_security_test(self, admin, users):
        from apps.strix_security.models import StrixConfig, SecurityTestProject

        # Strix Config
        config, _ = StrixConfig.objects.get_or_create(
            name='默认Strix扫描配置',
            defaults={
                'description': '生产环境安全扫描标准配置',
                'base_url': 'http://strix-scanner:8080',
                'api_key': 'strix-demo-key-12345',
                'created_by': admin,
                'is_active': True
            }
        )

        security_projects_data = [
            ('电商平台安全审计', '对电商全站进行漏洞扫描与安全合规审计', 'http://mall.example.com'),
            ('用户中台隐私检查', '用户敏感数据接口的安全性专项巡检', 'http://users.example.com'),
        ]

        for name, desc, target in security_projects_data:
            SecurityTestProject.objects.get_or_create(
                name=name,
                defaults={
                    'description': desc,
                    'target_url': target,
                    'config': config,
                    'created_by': admin,
                    'is_active': True
                }
            )
