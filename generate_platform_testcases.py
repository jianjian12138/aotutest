import sys
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first()
if not admin_user:
    admin_user = User.objects.first()

print(f"Injecting test cases as user: {admin_user.username}")

try:
    # --- 1. Core Platform Project ---
    from apps.core_platform.models import Project
    print("Creating Master Project...")
    master_proj, _ = Project.objects.get_or_create(
        name="testhub_master",
        defaults={
            "description": "Auto-generated comprehensive test suite",
            "owner": admin_user,
            "status": "active"
        }
    )

    # --- 2. API Testing Module ---
    from apps.api_testing.models import ApiProject, ApiCollection, ApiRequest, ApiTestCase
    print("Generating API Testing Cases...")
    api_proj, _ = ApiProject.objects.get_or_create(
        name="testhub_api_testing",
        defaults={
            "description": "Backend API Validation",
            "project_type": "HTTP",
            "status": "IN_PROGRESS",
            "owner": admin_user
        }
    )
    api_col, _ = ApiCollection.objects.get_or_create(
        project=api_proj,
        name="User Authentication API"
    )
    # Generate API Requests
    api_req1, _ = ApiRequest.objects.get_or_create(
        collection=api_col,
        name="POST Login",
        defaults={
            "method": "POST",
            "url": "/api/auth/login/",
            "created_by": admin_user
        }
    )
    api_req2, _ = ApiRequest.objects.get_or_create(
        collection=api_col,
        name="GET Profile",
        defaults={
            "method": "GET",
            "url": "/api/auth/user/",
            "created_by": admin_user
        }
    )
    # Generate API Test Cases
    ApiTestCase.objects.get_or_create(
        project=api_proj,
        name="T1: Admin Login Success Flow",
        defaults={
            "description": "Verifies that an admin can login and receive a 200 OK JWT token",
            "priority": "P1",
            "created_by": admin_user
        }
    )

    # --- 3. UI Automation Module ---
    from apps.ui_automation.models.project import UiProject
    from apps.ui_automation.models.element import LocatorStrategy, Element
    from apps.ui_automation.models.testcase import TestCase, TestCaseStep
    
    print("Generating UI Automation Cases...")
    ui_proj, _ = UiProject.objects.get_or_create(
        name="testhub_ui_automation",
        defaults={
            "description": "Frontend UI Validation",
            "base_url": "http://127.0.0.1:3000",
            "owner": admin_user
        }
    )
    # Create Locator Strategy
    ls_css, _ = LocatorStrategy.objects.get_or_create(name="css", defaults={"description": "CSS Selector"})
    
    # Create Elements
    login_btn, _ = Element.objects.get_or_create(
        project=ui_proj,
        name="Dashboard Login Button",
        defaults={
            "locator_strategy": ls_css,
            "locator_value": ".btn-login",
            "created_by": admin_user
        }
    )

    # Create UI Test Case
    ui_tc, _ = TestCase.objects.get_or_create(
        project=ui_proj,
        name="WEB-01: Admin Dashboard Navigation",
        defaults={
            "description": "Navigate to UI and capture full dashboard layout",
            "status": "ready",
            "priority": "high",
            "created_by": admin_user
        }
    )
    
    # Create Steps for UI Case
    TestCaseStep.objects.get_or_create(
        test_case=ui_tc,
        step_number=1,
        defaults={
            "action_type": "urlJump",
            "input_value": "/home",
            "description": "Navigate to Home"
        }
    )
    TestCaseStep.objects.get_or_create(
        test_case=ui_tc,
        step_number=2,
        defaults={
            "action_type": "screenshot",
            "description": "Capture Homepage layout"
        }
    )
    TestCaseStep.objects.get_or_create(
        test_case=ui_tc,
        step_number=3,
        defaults={
            "action_type": "assert",
            "assert_type": "urlContains",
            "assert_value": "/home",
            "description": "Verify URL is correct"
        }
    )

    # --- 4. Performance Testing Module ---
    from apps.performance_test.models import PerformanceProject, PerformanceCollection, PerformanceRequest, PerformanceEnvironment
    print("Generating Performance Testing Scenarios...")
    perf_proj, _ = PerformanceProject.objects.get_or_create(
        name="testhub_performance",
        defaults={
            "owner": admin_user,
            "description": "Load and stress testing scenarios"
        }
    )
    perf_col, _ = PerformanceCollection.objects.get_or_create(
        project=perf_proj,
        name="High Concurrency Load Tests"
    )
    PerformanceRequest.objects.get_or_create(
        collection=perf_col,
        name="Spike Test - Dashboard Load",
        defaults={
            "method": "GET",
            "url": "http://127.0.0.1:3000/home",
            "created_by": admin_user
        }
    )

    # --- 5. Security Testing Module ---
    from apps.strix_security.models import StrixConfig, SecurityTestProject
    print("Generating Security Scanning Configurations...")
    strix_cfg, _ = StrixConfig.objects.get_or_create(
        name="Local Strix Engine Configuration",
        defaults={
            "base_url": "http://127.0.0.1:8000",
            "api_key": "sec-test-key-001",
            "created_by": admin_user
        }
    )
    SecurityTestProject.objects.get_or_create(
        name="testhub_security_audit",
        defaults={
            "description": "OWASP Top 10 automated proactive scan",
            "target_url": "http://127.0.0.1:8000",
            "config": strix_cfg,
            "created_by": admin_user
        }
    )

    print("\n[SUCCESS] Successfully generated diverse test cases across API, UI, Performance, and Security modules!")
    print("Instruct the user to refresh http://localhost:5656/home to see the populated platform.")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"\n[ERROR] Generation failed: {str(e)}")
