import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from apps.ui_automation.models import (
    UiProject, LocatorStrategy, Element, TestCase, TestCaseStep
)
from django.contrib.auth import get_user_model

User = get_user_model()

def create_airtest_demo_data():
    # 1. Get or Create User
    user = User.objects.first()
    if not user:
        print("No user found, creating admin")
        user = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')

    # 2. Create Project
    project, created = UiProject.objects.get_or_create(
        name="Airtest Demo Project",
        defaults={
            'description': 'Demo project for Airtest features',
            'base_url': 'http://localhost:8080',
            'owner': user
        }
    )
    print(f"Project: {project.name}")

    # 3. Create Locator Strategies
    strategies = {
        'IMAGE': 'Airtest Image Recognition',
        'POCO': 'Poco UI Inspector',
        'COORDINATE': 'Absolute Coordinates'
    }
    
    strategy_objs = {}
    for name, desc in strategies.items():
        obj, _ = LocatorStrategy.objects.get_or_create(
            name=name,
            defaults={'description': desc}
        )
        strategy_objs[name] = obj
        print(f"Strategy: {obj.name}")

    # 4. Create Elements
    # Image Element
    img_element, _ = Element.objects.get_or_create(
        project=project,
        name="Login Button (Image)",
        defaults={
            'element_type': 'BUTTON',
            'locator_strategy': strategy_objs['IMAGE'],
            'locator_value': 'assets/login_btn.png',
            'description': 'Login button identified by image'
        }
    )
    
    # Poco Element
    poco_element, _ = Element.objects.get_or_create(
        project=project,
        name="Start Button (Poco)",
        defaults={
            'element_type': 'BUTTON',
            'locator_strategy': strategy_objs['POCO'],
            'locator_value': 'name=btn_start',
            'description': 'Start button identified by Poco'
        }
    )

    # 5. Create Test Cases
    
    # Case 1: Airtest Script (.air) - Image Based
    case_air, _ = TestCase.objects.get_or_create(
        project=project,
        name="Airtest Script Demo (.air)",
        defaults={
            'description': 'Demonstrates Airtest image recognition (.air style)',
            'created_by': user,
            'status': 'ready'
        }
    )
    # Clear existing steps
    case_air.steps.all().delete()
    TestCaseStep.objects.create(
        test_case=case_air,
        step_number=1,
        action_type='click',
        element=img_element,
        description='Touch the login button image'
    )
    TestCaseStep.objects.create(
        test_case=case_air,
        step_number=2,
        action_type='wait',
        wait_time=2000,
        description='Wait for 2 seconds'
    )
    print(f"Created Case: {case_air.name}")

    # Case 2: Python Script (.py) - API Based
    case_py, _ = TestCase.objects.get_or_create(
        project=project,
        name="Airtest Python Demo (.py)",
        defaults={
            'description': 'Demonstrates Airtest Python API usage',
            'created_by': user,
            'status': 'ready'
        }
    )
    case_py.steps.all().delete()
    # Note: Since we don't have a "Script" step, we simulate with standard actions
    TestCaseStep.objects.create(
        test_case=case_py,
        step_number=1,
        action_type='wait',
        wait_time=1000,
        description='Simulating api.sleep(1.0)'
    )
    TestCaseStep.objects.create(
        test_case=case_py,
        step_number=2,
        action_type='screenshot',
        description='Simulating api.snapshot()'
    )
    print(f"Created Case: {case_py.name}")

    # Case 3: Poco Script - UI Inspection
    case_poco, _ = TestCase.objects.get_or_create(
        project=project,
        name="Airtest Poco Demo",
        defaults={
            'description': 'Demonstrates Poco UI automation',
            'created_by': user,
            'status': 'ready'
        }
    )
    case_poco.steps.all().delete()
    TestCaseStep.objects.create(
        test_case=case_poco,
        step_number=1,
        action_type='click',
        element=poco_element,
        description='poco("btn_start").click()'
    )
    TestCaseStep.objects.create(
        test_case=case_poco,
        step_number=2,
        action_type='assert',
        assert_type='exists',
        element=poco_element,
        description='assert_exists(poco("btn_start"))'
    )
    print(f"Created Case: {case_poco.name}")

if __name__ == '__main__':
    create_airtest_demo_data()
