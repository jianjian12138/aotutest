import sys
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first()
if not admin_user:
    admin_user = User.objects.first()

print(f"Injecting Real Self-Testing Suite as user: {admin_user.username if admin_user else 'System'}")

try:
    # --- 1. Cleanup Old Fake Data ---
    from apps.core_platform.models import Project
    print("Cleaning up old massive placeholder data...")
    Project.objects.filter(name="testhub_massive_suite").delete()

    # --- 2. Core Platform Project ---
    print("Creating Real Self-Test Master Project...")
    master_proj, _ = Project.objects.get_or_create(
        name="testhub_self_test_suite",
        defaults={
            "description": "True End-to-End Regression Suite for the AI Testing Platform",
            "owner": admin_user,
            "status": "active"
        }
    )

    # --- 3. API Testing Module ---
    from apps.api_testing.models import ApiProject, ApiCollection, ApiRequest, ApiTestCase
    print("Generating Real API Self-Testing Cases...")
    api_proj, _ = ApiProject.objects.get_or_create(
        name="selftest_api_backend",
        defaults={
            "description": "Validates the local Django platform backend APIs",
            "project_type": "HTTP",
            "status": "IN_PROGRESS",
            "owner": admin_user
        }
    )
    
    col_auth, _ = ApiCollection.objects.get_or_create(
        project=api_proj,
        name="Platform Authentication APIs"
    )
    # 1. Login API
    api_req_login, _ = ApiRequest.objects.get_or_create(
        collection=col_auth,
        name="POST Platform Login",
        defaults={
            "method": "POST",
            "url": "http://127.0.0.1:8000/api/auth/login/",
            "body": {"username": "admin", "password": "password"},
            "created_by": admin_user
        }
    )
    # 2. API Projects API
    col_core, _ = ApiCollection.objects.get_or_create(
        project=api_proj,
        name="Platform Core Features"
    )
    api_req_projects, _ = ApiRequest.objects.get_or_create(
        collection=col_core,
        name="GET UI Automation Projects",
        defaults={
            "method": "GET",
            "url": "http://127.0.0.1:4545/api/ui-automation/projects/",
            "created_by": admin_user
        }
    )
    
    # Generate API Test Cases
    ApiTestCase.objects.get_or_create(
        project=api_proj,
        name="T-SELFTEST-01: Login returns Bearer Token",
        defaults={
            "description": "Verifies that the /api/auth/login/ endpoint successfully authenticates user and returns a token",
            "priority": "P0",
            "created_by": admin_user
        }
    )

    # --- 4. UI Automation Module ---
    from apps.ui_automation.models.project import UiProject
    from apps.ui_automation.models.element import LocatorStrategy, Element, PageObject
    from apps.ui_automation.models.testcase import TestCase, TestCaseStep
    
    print("Generating Real UI Automation Front-End Cases...")
    ui_proj, _ = UiProject.objects.get_or_create(
        name="selftest_ui_frontend",
        defaults={
            "description": "Validates the local Vue/React platform frontend UI",
            "base_url": "http://localhost:5656",
            "owner": admin_user
        }
    )
    
    ls_css, _ = LocatorStrategy.objects.get_or_create(name="css", defaults={"description": "CSS Selector"})
    
    # Create Real Platform UI Test Case!
    tc_login, _ = TestCase.objects.get_or_create(
        project=ui_proj,
        name="WEB-SELFTEST-01: Verify Home Page Loads",
        defaults={
            "description": "Auto-Navigates into the platform dashboard itself and asserts the page runs",
            "status": "ready",
            "priority": "high",
            "created_by": admin_user
        }
    )
    # Create Steps
    TestCaseStep.objects.get_or_create(
        test_case=tc_login,
        step_number=1,
        defaults={"action_type": "urlJump", "input_value": "http://localhost:5656/home", "description": "Navigate to local platform home"}
    )
    TestCaseStep.objects.get_or_create(
        test_case=tc_login,
        step_number=2,
        defaults={"action_type": "wait", "wait_time": 2000, "description": "Wait for frontend React/Vue to load"}
    )
    TestCaseStep.objects.get_or_create(
        test_case=tc_login,
        step_number=3,
        defaults={"action_type": "screenshot", "description": "Capture the running platform interface"}
    )

    # --- 5. Performance Testing Module ---
    from apps.performance_test.models import PerformanceProject, PerformanceCollection, PerformanceRequest, PerformanceEnvironment
    print("Generating Real Performance Heartbeat Testing Scenarios...")
    perf_proj, _ = PerformanceProject.objects.get_or_create(
        name="selftest_performance",
        defaults={
            "owner": admin_user,
            "description": "Load tests against local backend"
        }
    )
    
    perf_col, _ = PerformanceCollection.objects.get_or_create(
        project=perf_proj,
        name="Backend API Load Testing"
    )
    PerformanceRequest.objects.get_or_create(
        collection=perf_col,
        name="Stress Test: /api/ui-automation/projects/ API",
        defaults={
            "method": "GET",
            "url": "http://127.0.0.1:4545/api/ui-automation/projects/",
            "created_by": admin_user
        }
    )

    # --- 6. Security Testing Module ---
    from apps.strix_security.models import StrixConfig, SecurityTestProject
    print("Generating Real Security Auditing Task...")
    strix_cfg, _ = StrixConfig.objects.get_or_create(
        name="Localhost Internal Strix Agent",
        defaults={
            "base_url": "http://127.0.0.1:8000",
            "api_key": "sec-selftest-key",
            "created_by": admin_user
        }
    )
    
    SecurityTestProject.objects.get_or_create(
        name="SEC-SELFTEST-01: Frontend XSS Injection Check",
        defaults={
            "description": "Automated proactive scan checking for DOM-based XSS on the http://localhost:5656 routing plane.",
            "target_url": "http://localhost:5656",
            "config": strix_cfg,
            "created_by": admin_user
        }
    )

    print("\n[SUCCESS] Successfully purged fake massive data and injected genuine platform E2E self-testing suites!")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"\n[ERROR] Generation failed: {str(e)}")
