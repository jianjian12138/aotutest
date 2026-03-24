import sys
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.core_platform.models import Project
from apps.notifications.models import NotificationConfig
from apps.scheduler.models import ScheduledTask

# Testing Apps Models
from apps.api_testing.models import ApiProject, ApiTestCase, TestSuite as ApiTestSuite, TestSuiteTestCase as ApiTestSuiteTestCase
from apps.ui_automation.models.project import UiProject
from apps.ui_automation.models.testcase import TestCase as UiTestCase
from apps.ui_automation.models.execution import TestSuite as UiTestSuite, TestSuiteTestCase as UiTestSuiteTestCase

User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first()
if not admin_user:
    admin_user = User.objects.first()

print(f"Executing CI/CD Storage Linkage as: {admin_user.username}")

try:
    # 1. CREATE FEISHU NOTIFICATION CONFIG
    print("1. Binding Feishu Webhook Configuration...")
    webhook_payload = {
        "feishu": {
            "name": "Platform Self-Test Alarm Robot",
            "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/8ed9f640-5e03-47fe-9298-31e5820d2a2e",
            "enabled": True
        }
    }
    
    notify_config, _ = NotificationConfig.objects.get_or_create(
        name="[Core System Alert] Self-Test Feishu Engine",
        defaults={
            "config_type": "webhook_feishu",
            "webhook_bots": webhook_payload,
            "is_default": True,
            "is_active": True,
            "enable_ui_automation": True,
            "enable_api_testing": True,
            "created_by": admin_user
        }
    )

    core_project = Project.objects.filter(name="testhub_genuine_massive_tests").first()
    if not core_project:
         raise Exception("The fundamental massive suite [testhub_genuine_massive_tests] was not found!")

    # 2. CREATE API TEST SUITE
    print("2. Packaging Base API Cases into execution suite...")
    api_project = ApiProject.objects.filter(name="platform_massive_backend_api").first()
    
    api_suite, _ = ApiTestSuite.objects.get_or_create(
        project=api_project,
        name="Nightly Backend Regression Suite",
        defaults={
            "description": "Full E2E check of all 10 local API Backend modules",
            "created_by": admin_user
        }
    )
    # Clear old linkages to be safe
    ApiTestSuiteTestCase.objects.filter(test_suite=api_suite).delete()
    
    # Grab first 40 test cases to put into Suite (Mass execution chunk)
    api_cases = list(ApiTestCase.objects.filter(project=api_project)[:40])
    for idx, tc in enumerate(api_cases, 1):
        ApiTestSuiteTestCase.objects.create(
            test_suite=api_suite,
            test_case=tc,
            order=idx
        )

    # 3. CREATE UI TEST SUITE
    print("3. Packaging Base UI Web Cases into execution suite...")
    ui_project = UiProject.objects.filter(name="platform_massive_frontend_ui").first()
    
    ui_suite, _ = UiTestSuite.objects.get_or_create(
        project=ui_project,
        name="Nightly Web UI E2E Validation",
        defaults={
            "description": "Automated headless chromium visual validation pipeline"
        }
    )
    # Clear old linkages
    UiTestSuiteTestCase.objects.filter(test_suite=ui_suite).delete()
    
    ui_cases = list(UiTestCase.objects.filter(project=ui_project)[:20])
    for idx, tc in enumerate(ui_cases, 1):
        UiTestSuiteTestCase.objects.create(
            test_suite=ui_suite,
            test_case=tc,
            order=idx
        )

    # 4. BIND SCHEDULER CI/CD HOOKS
    print("4. Registering tasks deeply within Platform Scheduler CRON Engine...")
    
    # Task 1: API Task at 02:00
    ScheduledTask.objects.get_or_create(
        name="System Task: Nightly Backend API Healthcheck",
        defaults={
            "description": "Trigger all 40+ HTTP APIs automatically at lowest traffic hour.",
            "project": core_project,
            "api_project": api_project,
            "task_type": "API",
            "api_test_suite": api_suite,
            "trigger_type": "CRON",
            "cron_expression": "0 2 * * *",  # 2AM Daily
            "status": "ACTIVE",
            "notification_config": notify_config,
            "notify_on_success": True,
            "notify_on_failure": True,
            "created_by": admin_user
        }
    )
    
    # Task 2: UI Task at 04:00
    ScheduledTask.objects.get_or_create(
        name="System Task: Pre-Dawn Browser Navigation Tests",
        defaults={
            "description": "Trigger web E2E checks locally to ensure DOM logic prior to startup.",
            "project": core_project,
            "task_type": "UI",
            "ui_test_suite": ui_suite,
            "trigger_type": "CRON",
            "cron_expression": "0 4 * * *",  # 4AM Daily
            "status": "ACTIVE",
            "notification_config": notify_config,
            "notify_on_success": True,
            "notify_on_failure": True,
            "created_by": admin_user
        }
    )

    print("\n[SUCCESS] CI/CD Pipeline Fully Generated: Feishu hooks online and CRON Jobs linked to true datasets!")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"\n[ERROR] Generation failed: {str(e)}")
