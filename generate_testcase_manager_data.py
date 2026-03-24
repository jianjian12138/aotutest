import os
import django
import sys
from datetime import timedelta
import random

# 设置 Django 环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.utils import timezone
from apps.core_platform.models import User, Project
from apps.testcases.models import TestCaseModule, TestCase, TestCaseStep

def populate_testcases_manager():
    print("🚀 开始向【测试用例】(TestCase Management) 核心看板注入仿真平台数据...")

    # 获取默认用户和项目
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.first()
    
    project = Project.objects.filter(name="针对平台自身的自测项目").first()
    if not project:
        project = Project.objects.first()

    now = timezone.now()

    # 清除旧数据防止重复展示
    TestCaseModule.objects.all().delete()
    TestCase.objects.all().delete()

    # 1. 创建树形模块架构 (TestCaseModule)
    root_module_1 = TestCaseModule.objects.create(project=project, name="AI平台功能验证模块", order=1, created_at=now)
    sub_mod_api = TestCaseModule.objects.create(project=project, name="API 自动化引擎", parent=root_module_1, order=1, created_at=now)
    sub_mod_ui = TestCaseModule.objects.create(project=project, name="Web UI 回放引擎", parent=root_module_1, order=2, created_at=now)

    root_module_2 = TestCaseModule.objects.create(project=project, name="基础架构巡检", order=2, created_at=now)
    sub_mod_scheduler = TestCaseModule.objects.create(project=project, name="分布式调度器 (Cron)", parent=root_module_2, order=1, created_at=now)
    sub_mod_notification = TestCaseModule.objects.create(project=project, name="Webhook 通知分发中心", parent=root_module_2, order=2, created_at=now)

    modules_map = {
        "API": sub_mod_api,
        "UI": sub_mod_ui,
        "调度": sub_mod_scheduler,
        "通知": sub_mod_notification
    }

    # 2. 创建真实存在的测试用例 (TestCase)
    cases_data = [
        {
            "title": "验证 [接口自动化] 在高并发流量集控下的响应准确率 (HTTP 200)",
            "module": "API",
            "type": "api",
            "priority": "high",
            "status": "active",
            "preconditions": "1. 平台后端 4545 端口全负载均衡开启\n2. 数据库读写分离正常",
            "expected_result": "接口流转成功，并且数据库状态被完整追踪",
            "steps": [
                {"action": "在接口库中选择并发执行节点 2000 个", "expected": "节点分配成功，进入 Waiting 池"},
                {"action": "触发立即发送", "expected": "引擎下发网络包并在 500ms 内全部响应"}
            ]
        },
        {
            "title": "验证 [UI 自动化] 针对 Playwright 浏览器节点的挂载热启动",
            "module": "UI",
            "type": "ui",
            "priority": "critical",
            "status": "active",
            "preconditions": "1. Chromium Headless Shell 驱动已经全局安装完毕\n2. 前端 5656 Vue工程正在运行",
            "expected_result": "Chrome 无头浏览器能够正常挂载，且在 10秒内走完表单回填录像",
            "steps": [
                {"action": "读取录制的 Playwright JSON 流执行字典", "expected": "字典反序列化成功"},
                {"action": "在 Chromium 环境执行 page.locator().fill()", "expected": "成功操作 DOM"}
            ]
        },
        {
            "title": "确保 [分布式调度器] 凌晨 2:00 定时任务如期抛出执行块",
            "module": "调度",
            "type": "functional",
            "priority": "high",
            "status": "draft",
            "preconditions": "1. APScheduler 配置启动无抛错",
            "expected_result": "底层进程日志准时输出了执行指令",
            "steps": [
                {"action": "配置 Cron 为 0 2 * * *", "expected": "成功写入 SQLite Scheduler Task 表"},
                {"action": "模拟时钟平移到 02:00:00", "expected": "消费者自动捕获并派发任务模型"}
            ]
        },
        {
            "title": "测试 [Webhook 分发] 能否精准适配飞书机器人 Markdown 卡片",
            "module": "通知",
            "type": "integration",
            "priority": "medium",
            "status": "active",
            "preconditions": "飞书沙盒群及公开 Webhook Token 生成完毕",
            "expected_result": "群聊收到了彩色警报卡片，涵盖通过率和测试名称",
            "steps": [
                {"action": "拦截 TestReportSerializer 汇总的 JSON 模型", "expected": "抓获包含 total_steps 和 failed_steps 的嵌套包"},
                {"action": "发起 HTTP Post 到飞书开放接口", "expected": "收到 Status 0 及发送成功的回执"}
            ]
        }
    ]

    for data in cases_data:
        tc = TestCase.objects.create(
            project=project,
            module=modules_map[data['module']],
            title=data['title'],
            description=f"关于系统模块 {data['module']} 的回归测试详细用例。",
            preconditions=data['preconditions'],
            expected_result=data['expected_result'],
            priority=data['priority'],
            status=data['status'],
            test_type=data['type'],
            author=admin_user,
            created_at=now - timedelta(hours=random.randint(1, 48))
        )
        print(f"✅ 生成具体用例: {tc.title} [{tc.test_type}]")

        # 3. 关联并生成 TestCaseStep 长串步骤表
        for idx, step in enumerate(data['steps']):
            TestCaseStep.objects.create(
                testcase=tc,
                step_number=idx + 1,
                action=step['action'],
                expected=step['expected']
            )

    print("\n🎉 【测试用例】底层数据表铺设完成！请刷新页面查看左树及列表展示效果。")

if __name__ == "__main__":
    populate_testcases_manager()
