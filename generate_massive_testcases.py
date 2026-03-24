import sys
import os
import django
import random
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first()
if not admin_user:
    admin_user = User.objects.first()

print(f"Injecting massive test volume as: {admin_user.username if admin_user else 'System'}")

try:
    # --- 1. Core Platform Project ---
    from apps.core_platform.models import Project
    print("Creating Massive Master Project...")
    master_proj, _ = Project.objects.get_or_create(
        name="testhub_massive_suite",
        defaults={
            "description": "Enterprise-scale massive volume test suite",
            "owner": admin_user,
            "status": "active"
        }
    )

    # --- 2. API Testing Module ---
    from apps.api_testing.models import ApiProject, ApiCollection, ApiRequest, ApiTestCase
    print("Generating 50+ API Testing Cases...")
    api_proj, _ = ApiProject.objects.get_or_create(
        name="testhub_massive_api",
        defaults={
            "description": "Massive API Volume target",
            "project_type": "HTTP",
            "status": "IN_PROGRESS",
            "owner": admin_user
        }
    )
    
    api_domains = ["User Auth", "Order System", "Payment Gateway", "Inventory Sync", "Notification API"]
    for i, domain in enumerate(api_domains, 1):
        col, _ = ApiCollection.objects.get_or_create(
            project=api_proj,
            name=f"{domain} v{i}.0"
        )
        for j in range(1, 11):
            method = random.choice(["GET", "POST", "PUT", "DELETE"])
            ApiRequest.objects.get_or_create(
                collection=col,
                name=f"{method} {domain} Route {j}",
                defaults={
                    "method": method,
                    "url": f"/api/v{i}/{domain.lower().replace(' ', '_')}/{j}/",
                    "created_by": admin_user
                }
            )
            ApiTestCase.objects.get_or_create(
                project=api_proj,
                name=f"T-API-{i}-{j}: Validate {domain} - Flow {j}",
                defaults={
                    "description": f"Auto-generated test to validate {method} behavior for {domain}",
                    "priority": random.choice(["P0", "P1", "P2", "P3"]),
                    "created_by": admin_user
                }
            )

    # --- 3. UI Automation Module ---
    from apps.ui_automation.models.project import UiProject
    from apps.ui_automation.models.element import LocatorStrategy, Element, PageObject
    from apps.ui_automation.models.testcase import TestCase, TestCaseStep
    
    print("Generating 30+ UI Automation Cases...")
    ui_proj, _ = UiProject.objects.get_or_create(
        name="testhub_massive_ui",
        defaults={
            "description": "Massive UI Web tests",
            "base_url": "http://127.0.0.1:3000",
            "owner": admin_user
        }
    )
    
    ls_css, _ = LocatorStrategy.objects.get_or_create(name="css", defaults={"description": "CSS Selector"})
    
    ui_pages = ["Login", "Dashboard", "UserProfile", "Settings", "ReportView", "OrderHistory", "Cart", "Checkout", "ProductList", "AdminPanel"]
    for i, page_name in enumerate(ui_pages, 1):
        po, _ = PageObject.objects.get_or_create(
            project=ui_proj,
            name=f"{page_name} Page",
            defaults={"class_name": f"{page_name}Page", "created_by": admin_user}
        )
        
        # 3 test cases per page
        for j in range(1, 4):
            tc, _ = TestCase.objects.get_or_create(
                project=ui_proj,
                name=f"WEB-{i*100 + j}: {page_name} Functional Flow {j}",
                defaults={
                    "description": f"Verify {page_name} layout and interactivity.",
                    "status": "ready",
                    "priority": random.choice(["high", "medium", "low"]),
                    "created_by": admin_user
                }
            )
            # Create Steps
            TestCaseStep.objects.get_or_create(
                test_case=tc,
                step_number=1,
                defaults={"action_type": "urlJump", "input_value": f"/{page_name.lower()}", "description": f"Go to {page_name}"}
            )
            TestCaseStep.objects.get_or_create(
                test_case=tc,
                step_number=2,
                defaults={"action_type": "wait", "wait_time": 2000, "description": "Wait for elements"}
            )
            TestCaseStep.objects.get_or_create(
                test_case=tc,
                step_number=3,
                defaults={"action_type": "screenshot", "description": "Capture state"}
            )

    # --- 4. Performance Testing Module ---
    from apps.performance_test.models import PerformanceProject, PerformanceCollection, PerformanceRequest, PerformanceEnvironment
    print("Generating 20+ Performance Testing Scenarios...")
    perf_proj, _ = PerformanceProject.objects.get_or_create(
        name="testhub_massive_perf",
        defaults={
            "owner": admin_user,
            "description": "Massive Stress testing configurations"
        }
    )
    
    perf_levels = [1000, 5000, 10000, 50000]
    for i, level in enumerate(perf_levels, 1):
        perf_col, _ = PerformanceCollection.objects.get_or_create(
            project=perf_proj,
            name=f"Stress Test Suite - {level} CCU"
        )
        for j in range(1, 6): # 5 scenarios per level
            PerformanceRequest.objects.get_or_create(
                collection=perf_col,
                name=f"Load Model: {level} users on Node {j}",
                defaults={
                    "method": "GET",
                    "url": f"http://127.0.0.1:3000/api/perf/{j}",
                    "created_by": admin_user
                }
            )

    # --- 5. Security Testing Module ---
    from apps.strix_security.models import StrixConfig, SecurityTestProject
    print("Generating 10+ Security Scanning Configurations...")
    strix_cfg, _ = StrixConfig.objects.get_or_create(
        name="Global Strix Cluster",
        defaults={
            "base_url": "http://127.0.0.1:8000",
            "api_key": "sec-massive-key",
            "created_by": admin_user
        }
    )
    
    vuln_types = ["SQL Injection", "Cross-Site Scripting (XSS)", "CSRF Prevention", "IDOR Check", "Directory Traversal", "Rate Limiting", "SSRF", "Data Leakage", "Weak Crypto", "Config Mismanagement"]
    for i, vuln in enumerate(vuln_types, 1):
        SecurityTestProject.objects.get_or_create(
            name=f"SEC-{i}: {vuln} Audit",
            defaults={
                "description": f"Automated proactive scanning specifically checking for {vuln} across the microservices.",
                "target_url": "http://127.0.0.1:8000",
                "config": strix_cfg,
                "created_by": admin_user
            }
        )

    print("\n[SUCCESS] Massively flooded all platform databases with over 110 diverse test cases!")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"\n[ERROR] Generation failed: {str(e)}")
