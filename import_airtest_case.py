import os
import sys
import yaml
import shutil
import django

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model
from apps.ui_automation.models import (
    UiProject, TestCase, TestCaseStep, Element, LocatorStrategy, ElementGroup
)

def import_airtest_case():
    # Paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    airtest_dir = os.path.join(base_dir, 'mobile_airtest')
    yaml_path = os.path.join(airtest_dir, 'examples', 'login.yaml')
    air_path = os.path.join(airtest_dir, 'examples', 'login.air')
    
    # Read YAML
    with open(yaml_path, 'r', encoding='utf-8') as f:
        case_data = yaml.safe_load(f)
    
    print(f"Importing case: {case_data['case_name']}")
    
    # Get User
    User = get_user_model()
    user = User.objects.first()
    if not user:
        print("No user found. Please create a user first.")
        return

    # Get Project (Use 'Multi-Engine Demo Project' as seen in screenshot)
    project_name = "Multi-Engine Demo Project"
    project = UiProject.objects.filter(name=project_name).first()
    if not project:
        print(f"Project '{project_name}' not found. Creating new one.")
        project = UiProject.objects.create(
            name=project_name,
            description="Imported Airtest Project",
            base_url="http://localhost",
            owner=user
        )
    
    # Get or Create Image Strategy
    img_strategy, _ = LocatorStrategy.objects.get_or_create(
        name='IMAGE',
        defaults={'description': 'Airtest Image Recognition'}
    )
    
    # Create Element Group for this case
    group, _ = ElementGroup.objects.get_or_create(
        project=project,
        name=case_data['case_name'],
        defaults={'description': 'Elements for imported Airtest case'}
    )
    
    # Create TestCase
    test_case, created = TestCase.objects.get_or_create(
        project=project,
        name=case_data['case_name'],
        defaults={
            'description': f"Imported from {yaml_path}",
            'priority': case_data.get('priority', 'medium'),
            'status': 'ready',
            'created_by': user
        }
    )
    
    # Clear existing steps if updating
    if not created:
        print("Updating existing test case...")
        test_case.steps.all().delete()
    
    # Setup Media Directory for Images
    target_img_dir = os.path.join(settings.MEDIA_ROOT, 'airtest_images', str(project.id))
    os.makedirs(target_img_dir, exist_ok=True)
    
    # Process Steps
    step_number = 1
    
    def process_actions(actions_list, parent_desc=""):
        nonlocal step_number
        for action in actions_list:
            action_type = action.get('type')
            target = action.get('target')
            value = action.get('value')
            
            # Construct description
            desc = parent_desc
            if action_type == 'touch':
                desc += f"点击图片 {target}"
            elif action_type == 'text':
                desc += f"输入文本 '{value}'"
            elif action_type == 'sleep':
                desc += f"等待 {action.get('seconds')}秒"
            elif action_type == 'if_exists':
                desc += f"如果图片 {target} 存在"
            elif action_type == 'keyevent':
                desc += f"按键 {action.get('key')}"
            
            # Map action types
            mapped_action = 'custom'
            if action_type == 'touch':
                mapped_action = 'click'
            elif action_type == 'text':
                mapped_action = 'fill'
            elif action_type == 'sleep':
                mapped_action = 'wait'
            
            element = None
            input_value = str(value) if value else ""
            
            # Handle Image Element
            if target and str(target).endswith('.png'):
                src_img_path = os.path.join(air_path, target)
                if os.path.exists(src_img_path):
                    # Copy image
                    dst_img_name = f"{case_data['case_code']}_{target}"
                    dst_img_path = os.path.join(target_img_dir, dst_img_name)
                    shutil.copy2(src_img_path, dst_img_path)
                    
                    # Relative path for DB
                    db_img_path = os.path.join('airtest_images', str(project.id), dst_img_name).replace('\\', '/')
                    
                    # Create Element
                    element, _ = Element.objects.get_or_create(
                        project=project,
                        name=f"{case_data['case_code']}_{target}",
                        defaults={
                            'group': group,
                            'element_type': 'IMAGE',
                            'locator_strategy': img_strategy,
                            'locator_value': db_img_path,
                            'description': f"Image for {desc}",
                            'created_by': user
                        }
                    )
            
            # Create Step for this action
            # Skip container actions like if_exists for the step itself, but process its children
            if action_type not in ['if_exists', 'repeat']:
                TestCaseStep.objects.create(
                    test_case=test_case,
                    step_number=step_number,
                    action_type=mapped_action,
                    element=element,
                    input_value=input_value,
                    description=desc,
                    wait_time=int(action.get('seconds', 1.0) * 1000) if action_type == 'sleep' else 1000,
                    created_at=django.utils.timezone.now()
                )
                step_number += 1
            
            # Handle nested actions
            if action_type == 'if_exists':
                if 'actions' in action:
                    process_actions(action['actions'], parent_desc=f"[如果存在 {target}] ")
                if 'else_actions' in action:
                    process_actions(action['else_actions'], parent_desc=f"[否则] ")
            elif action_type == 'repeat':
                if 'actions' in action:
                    process_actions(action['actions'], parent_desc=f"[重复 {action.get('times')}次] ")

    for step_info in case_data['steps']:
        step_name = step_info['step_name']
        print(f"Processing step group: {step_name}")
        process_actions(step_info['actions'], parent_desc=f"{step_name} - ")


    print(f"Successfully imported test case '{test_case.name}' with {step_number-1} steps.")

if __name__ == '__main__':
    import_airtest_case()
