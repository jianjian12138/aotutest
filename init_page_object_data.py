import os
import sys
import django

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from apps.ui_automation.models import UiProject, PageObject, Element, PageObjectElement, LocatorStrategy
from django.contrib.auth import get_user_model

def init_data():
    User = get_user_model()
    user = User.objects.first()
    if not user:
        print("Error: No user found. Please create a superuser first.")
        return

    # 1. Get Project
    project_name = "Multi-Engine Demo Project"
    project = UiProject.objects.filter(name=project_name).first()
    if not project:
        print(f"Project '{project_name}' not found. Creating...")
        project = UiProject.objects.create(
            name=project_name,
            description="Demo Project for UI Automation",
            base_url="https://www.example.com",
            owner=user
        )
    
    # 2. Ensure Strategies exist
    css_strategy, _ = LocatorStrategy.objects.get_or_create(name="css", defaults={'description': 'CSS Selector'})
    xpath_strategy, _ = LocatorStrategy.objects.get_or_create(name="xpath", defaults={'description': 'XPath'})

    # 3. Create Elements
    elements_config = [
        {
            'name': '用户名输入框',
            'type': 'INPUT',
            'strategy': css_strategy,
            'value': 'input[name="username"]',
            'desc': '登录页面的用户名输入框'
        },
        {
            'name': '密码输入框',
            'type': 'INPUT',
            'strategy': css_strategy,
            'value': 'input[name="password"]',
            'desc': '登录页面的密码输入框'
        },
        {
            'name': '登录按钮',
            'type': 'BUTTON',
            'strategy': css_strategy,
            'value': 'button.login-btn',
            'desc': '登录提交按钮'
        },
        {
            'name': '错误提示信息',
            'type': 'TEXT',
            'strategy': xpath_strategy,
            'value': '//div[@class="error-msg"]',
            'desc': '登录失败时的错误提示'
        }
    ]

    created_elements = {}
    for cfg in elements_config:
        element, _ = Element.objects.get_or_create(
            project=project,
            name=cfg['name'],
            defaults={
                'element_type': cfg['type'],
                'locator_strategy': cfg['strategy'],
                'locator_value': cfg['value'],
                'description': cfg['desc'],
                'created_by': user
            }
        )
        created_elements[cfg['name']] = element
        print(f"Element ensured: {element.name}")

    # 4. Create Page Object: LoginPage
    page_object, created = PageObject.objects.get_or_create(
        project=project,
        name="登录页面 (LoginPage)",
        defaults={
            'class_name': 'LoginPage',
            'url_pattern': '/login',
            'description': '系统标准登录页面对象模型',
            'created_by': user
        }
    )
    print(f"PageObject ensured: {page_object.name}")

    # 5. Link Elements to Page Object
    po_links = [
        {
            'element_name': '用户名输入框',
            'method_name': 'username_input',
            'is_property': True,
            'order': 10
        },
        {
            'element_name': '密码输入框',
            'method_name': 'password_input',
            'is_property': True,
            'order': 20
        },
        {
            'element_name': '登录按钮',
            'method_name': 'click_login',
            'is_property': False, # Method
            'order': 30
        },
        {
            'element_name': '错误提示信息',
            'method_name': 'get_error_message',
            'is_property': False, # Method
            'order': 40
        }
    ]

    for link in po_links:
        element = created_elements.get(link['element_name'])
        if element:
            PageObjectElement.objects.update_or_create(
                page_object=page_object,
                method_name=link['method_name'],
                defaults={
                    'element': element,
                    'is_property': link['is_property'],
                    'order': link['order']
                }
            )
            print(f"  - Linked: {link['method_name']} -> {element.name}")

    # 6. Create Page Object: HomePage (Another example)
    home_page, _ = PageObject.objects.get_or_create(
        project=project,
        name="首页 (HomePage)",
        defaults={
            'class_name': 'HomePage',
            'url_pattern': '/dashboard',
            'description': '登录后的系统首页',
            'created_by': user
        }
    )
    print(f"PageObject ensured: {home_page.name}")

if __name__ == "__main__":
    init_data()
