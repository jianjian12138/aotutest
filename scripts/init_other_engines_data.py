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

def create_other_engines_data():
    # 1. Get User
    user = User.objects.first()
    if not user:
        print("No user found, creating admin")
        user = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')

    # 2. Create Project
    project, created = UiProject.objects.get_or_create(
        name="Multi-Engine Demo Project",
        defaults={
            'description': 'Demo project for Playwright, Selenium, and Appium features',
            'base_url': 'https://www.example.com',
            'owner': user
        }
    )
    print(f"Project: {project.name}")

    # 3. Ensure Locator Strategies exist
    strategies_map = {
        'CSS': ('css', 'CSS Selector'),
        'XPATH': ('xpath', 'XPath'),
        'ID': ('id', 'Element ID'),
        'ACCESSIBILITY_ID': ('accessibility_id', 'Accessibility ID (Appium)')
    }
    
    strategy_objs = {}
    for key, (name, desc) in strategies_map.items():
        obj, _ = LocatorStrategy.objects.get_or_create(
            name=name,
            defaults={'description': desc}
        )
        strategy_objs[key] = obj

    # ==========================================
    # Playwright Data (Web)
    # ==========================================
    print("\n--- Creating Playwright Data ---")
    # Elements
    pw_user_input, _ = Element.objects.get_or_create(
        project=project,
        name="Username Input (PW)",
        defaults={
            'element_type': 'INPUT',
            'locator_strategy': strategy_objs['CSS'],
            'locator_value': '#username',
            'description': 'Login username input field'
        }
    )
    pw_pass_input, _ = Element.objects.get_or_create(
        project=project,
        name="Password Input (PW)",
        defaults={
            'element_type': 'INPUT',
            'locator_strategy': strategy_objs['CSS'],
            'locator_value': '#password',
            'description': 'Login password input field'
        }
    )
    pw_login_btn, _ = Element.objects.get_or_create(
        project=project,
        name="Login Button (PW)",
        defaults={
            'element_type': 'BUTTON',
            'locator_strategy': strategy_objs['CSS'],
            'locator_value': 'button[type="submit"]',
            'description': 'Login submit button'
        }
    )

    # Test Case
    case_pw, _ = TestCase.objects.get_or_create(
        project=project,
        name="Playwright Login Demo",
        defaults={
            'description': 'Standard web login flow using Playwright',
            'created_by': user,
            'status': 'ready',
            'priority': 'high'
        }
    )
    case_pw.steps.all().delete()
    TestCaseStep.objects.create(test_case=case_pw, step_number=1, action_type='fill', element=pw_user_input, input_value='testuser', description='Enter username')
    TestCaseStep.objects.create(test_case=case_pw, step_number=2, action_type='fill', element=pw_pass_input, input_value='password123', description='Enter password')
    TestCaseStep.objects.create(test_case=case_pw, step_number=3, action_type='click', element=pw_login_btn, description='Click login button')
    TestCaseStep.objects.create(test_case=case_pw, step_number=4, action_type='assert', assert_type='textContains', assert_value='Welcome', description='Verify welcome message')
    print(f"Created Case: {case_pw.name}")

    # ==========================================
    # Selenium Data (Web)
    # ==========================================
    print("\n--- Creating Selenium Data ---")
    # Elements
    sel_search_box, _ = Element.objects.get_or_create(
        project=project,
        name="Search Box (Selenium)",
        defaults={
            'element_type': 'INPUT',
            'locator_strategy': strategy_objs['ID'],
            'locator_value': 'search-input',
            'description': 'Main search input'
        }
    )
    sel_search_btn, _ = Element.objects.get_or_create(
        project=project,
        name="Search Button (Selenium)",
        defaults={
            'element_type': 'BUTTON',
            'locator_strategy': strategy_objs['XPATH'],
            'locator_value': '//button[@aria-label="Search"]',
            'description': 'Search submit button'
        }
    )

    # Test Case
    case_sel, _ = TestCase.objects.get_or_create(
        project=project,
        name="Selenium Search Demo",
        defaults={
            'description': 'Search functionality test using Selenium',
            'created_by': user,
            'status': 'ready',
            'priority': 'medium'
        }
    )
    case_sel.steps.all().delete()
    TestCaseStep.objects.create(test_case=case_sel, step_number=1, action_type='fill', element=sel_search_box, input_value='Automated Testing', description='Type search query')
    TestCaseStep.objects.create(test_case=case_sel, step_number=2, action_type='click', element=sel_search_btn, description='Click search button')
    TestCaseStep.objects.create(test_case=case_sel, step_number=3, action_type='wait', wait_time=2000, description='Wait for results')
    TestCaseStep.objects.create(test_case=case_sel, step_number=4, action_type='screenshot', description='Capture results page')
    print(f"Created Case: {case_sel.name}")

    # ==========================================
    # Appium Data (Mobile)
    # ==========================================
    print("\n--- Creating Appium Data ---")
    # Elements
    app_menu_btn, _ = Element.objects.get_or_create(
        project=project,
        name="Menu Button (Appium)",
        defaults={
            'element_type': 'BUTTON',
            'locator_strategy': strategy_objs['ACCESSIBILITY_ID'],
            'locator_value': 'Open Menu',
            'description': 'Mobile app menu button'
        }
    )
    app_settings_item, _ = Element.objects.get_or_create(
        project=project,
        name="Settings Item (Appium)",
        defaults={
            'element_type': 'LINK',
            'locator_strategy': strategy_objs['XPATH'],
            'locator_value': '//android.widget.TextView[@text="Settings"]',
            'description': 'Settings menu item'
        }
    )

    # Test Case
    case_app, _ = TestCase.objects.get_or_create(
        project=project,
        name="Appium Mobile Demo",
        defaults={
            'description': 'Mobile app navigation demo using Appium',
            'created_by': user,
            'status': 'ready',
            'priority': 'low'
        }
    )
    case_app.steps.all().delete()
    TestCaseStep.objects.create(test_case=case_app, step_number=1, action_type='click', element=app_menu_btn, description='Tap menu button')
    TestCaseStep.objects.create(test_case=case_app, step_number=2, action_type='wait', wait_time=1000, description='Wait for menu animation')
    TestCaseStep.objects.create(test_case=case_app, step_number=3, action_type='click', element=app_settings_item, description='Tap settings')
    TestCaseStep.objects.create(test_case=case_app, step_number=4, action_type='assert', assert_type='exists', element=app_settings_item, description='Verify still visible (demo)')
    print(f"Created Case: {case_app.name}")

if __name__ == '__main__':
    create_other_engines_data()
