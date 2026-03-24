import os
import yaml
import re
import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.api_testing.models import (
    Environment, ApiProject, ApiRequest, ApiCollection,
    ApiTestCase, ApiTestCaseStep
)
from apps.ui_automation.models import (
    UiProject, PageObject, Element, PageObjectElement, 
    TestCase, TestCaseStep, LocatorStrategy, ElementGroup
)
from apps.core_platform.models import GlobalParameter, CommonMethod
from apps.core_platform.models import Project

User = get_user_model()

class Command(BaseCommand):
    help = 'Import AI_TEST project source code into the platform'

    def add_arguments(self, parser):
        parser.add_argument('--path', type=str, required=True, help='Path to AI_TEST source code directory')
        parser.add_argument('--user', type=str, default='admin', help='Username to assign as owner')
        parser.add_argument('--project', type=str, default='AI_TEST_Imported', help='Target project name')
        parser.add_argument('--file', type=str, help='Specific file to import (relative to path)')

    def handle(self, *args, **options):
        source_path = Path(options['path'])
        username = options['user']
        project_name = options['project']
        specific_file = options.get('file')
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = User.objects.first()
            if not user:
                self.stdout.write(self.style.ERROR(f"User {username} not found and no users exist."))
                return

        self.stdout.write(self.style.SUCCESS(f"Starting import from {source_path} as user {user.username} into project {project_name}"))

        if specific_file:
            file_path = source_path / specific_file
            if not file_path.exists():
                self.stdout.write(self.style.ERROR(f"File {file_path} does not exist."))
                return
            
            # Find or create API Project
            project, _ = ApiProject.objects.get_or_create(
                name=project_name,
                defaults={'owner': user, 'status': 'IN_PROGRESS', 'project_type': 'HTTP'}
            )
            
            if specific_file.endswith(('.yaml', '.yml')):
                # Check if it's an API file or Web file based on path
                if 'api' in specific_file or 'auto_generated' in specific_file:
                    self.stdout.write(f"Importing single API case: {specific_file}")
                    # For interface management, we need a collection
                    rel_path = Path(specific_file).parent
                    # Try to find if it's under 'cases/api' or 'cases/auto_generated/api'
                    for root in ['cases/api', 'cases/auto_generated/api']:
                        try:
                            rel_path = Path(specific_file).parent.relative_to(root)
                            break
                        except ValueError:
                            continue
                    
                    parent_col = None
                    if str(rel_path) != '.':
                        parent_col = self._get_or_create_collection_chain(project, rel_path)
                    
                    self._import_single_interface_file(file_path, project, user, parent_col)
                    self._import_single_api_case(file_path, project, user)
                else:
                    self.stdout.write(f"Importing single Web case: {specific_file}")
                    # UI Project handling
                    ui_project, _ = UiProject.objects.get_or_create(
                        name=f"{project_name}_UI",
                        defaults={'owner': user, 'status': 'IN_PROGRESS', 'base_url': 'http://localhost'}
                    )
                    self._import_single_web_case(file_path, ui_project, user)
            self.stdout.write(self.style.SUCCESS(f"Successfully imported {specific_file}"))
            return

        # 1. Import Environment
        self.import_environment(source_path, user, project_name)

        # 2. Import Page Objects
        self.import_page_objects(source_path, user, project_name)

        # 3. Import Web Cases
        self.import_web_cases(source_path, user, project_name)

        # 4. Import API Interfaces (Interface Management)
        self.import_api_interfaces(source_path, user, project_name)

        # 5. Import API Cases (Test Case Management)
        self.import_api_cases(source_path, user, project_name)

    def import_environment(self, source_path, user, project_name):
        env_file = source_path / 'config' / 'environment.yaml'
        if not env_file.exists():
            self.stdout.write(self.style.WARNING("config/environment.yaml not found, skipping environment import."))
            return

        self.stdout.write("Importing environment and global parameters...")
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                env_data = yaml.safe_load(f)

            # Find or create API Project for environment
            project, _ = ApiProject.objects.get_or_create(
                name=project_name,
                defaults={'owner': user, 'status': 'IN_PROGRESS', 'project_type': 'HTTP'}
            )
            
            # Find or create Generic Project for GlobalParameter
            param_project_name = f"{project_name}_Global_Config"
            generic_project, _ = Project.objects.get_or_create(
                name=param_project_name,
                defaults={'owner': user, 'status': 'active', 'description': 'Imported from AI_TEST'}
            )

            for env_name, config in env_data.items():
                if not isinstance(config, dict):
                    continue

                variables = {}
                # Flatten servers
                if 'servers' in config:
                    for k, v in config['servers'].items():
                        variables[k] = v
                        # Import as GlobalParameter
                        GlobalParameter.objects.update_or_create(
                            key=f"{env_name}_{k}",
                            defaults={
                                'value': str(v),
                                'description': f"Imported from {env_name}.servers.{k}",
                                'project': generic_project,
                                'created_by': user
                            }
                        )
                
                # Flatten global_variable
                if 'global_variable' in config:
                    for k, v in config['global_variable'].items():
                        variables[k] = v
                        # Import as GlobalParameter
                        GlobalParameter.objects.update_or_create(
                            key=f"{env_name}_{k}",
                            defaults={
                                'value': str(v),
                                'description': f"Imported from {env_name}.global_variable.{k}",
                                'project': generic_project,
                                'created_by': user
                            }
                        )

                # Create Environment
                env, created = Environment.objects.get_or_create(
                    name=f"AI_TEST_{env_name}",
                    defaults={
                        'scope': 'GLOBAL',
                        'is_active': True,
                        'project': project,
                        'created_by': user
                    }
                )
                env.variables = variables
                env.save()
                self.stdout.write(f"  Imported environment: {env.name}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to import environment: {e}"))

    # ... (rest of methods)

    def _parse_action(self, action_str, project):
        # ... (existing logic)
        
        # Import Common Method if detected
        match = re.match(r'\$(\w+)\((.*)\)', action_str)
        if match:
            func_name = match.group(1)
            # Create/Update CommonMethod
            # We need a project for CommonMethod. Use the generic one or UI project.
            # Assuming 'project' passed here is UiProject, but CommonMethod needs 'projects.Project'.
            # We will use the 'AI_TEST_Global_Config' project.
            
            try:
                generic_project = Project.objects.get(name="AI_TEST_Global_Config")
                CommonMethod.objects.get_or_create(
                    keyword=f"${func_name}",
                    defaults={
                        'name': func_name,
                        'description': f"Auto-imported from usage in test cases. Action: {action_str}",
                        'project': generic_project,
                        'created_by': project.owner # user
                    }
                )
            except Exception:
                pass # Ignore if project not found or other error

            # ... (rest of parsing)

    def import_page_objects(self, source_path, user, project_name):
        self.stdout.write("Importing page objects...")
        
        # Find or create UI Project
        project, _ = UiProject.objects.get_or_create(
            name=f"{project_name}_UI",
            defaults={
                'owner': user, 
                'status': 'IN_PROGRESS', 
                'base_url': 'http://localhost'
            }
        )

        # Ensure Locator Strategies exist
        strategies = {
            'xpath': LocatorStrategy.objects.get_or_create(name='xpath')[0],
            'css': LocatorStrategy.objects.get_or_create(name='css')[0],
            'text': LocatorStrategy.objects.get_or_create(name='text', defaults={'description': 'Text content'})[0],
            'id': LocatorStrategy.objects.get_or_create(name='id')[0],
        }

        # Locate page element config files
        config_files = list(source_path.rglob('页面元素配置.yaml'))
        
        for config_file in config_files:
            self.stdout.write(f"  Processing {config_file}")
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                for page_name, elements in data.items():
                    if page_name in ['case_code', 'case_name']:
                        continue
                    
                    if not isinstance(elements, dict):
                        continue

                    # Create Page Object
                    po, _ = PageObject.objects.get_or_create(
                        name=page_name,
                        project=project,
                        defaults={
                            'class_name': ''.join(x.capitalize() for x in page_name.split('_')),
                            'created_by': user
                        }
                    )

                    # Create Element Group for this page
                    group, _ = ElementGroup.objects.get_or_create(
                        name=page_name,
                        project=project
                    )

                    for elem_name, locator_data in elements.items():
                        # Parse locator
                        strategy, value = self._parse_locator(locator_data)
                        
                        # Create Element
                        element, _ = Element.objects.get_or_create(
                            project=project,
                            name=elem_name,
                            page=page_name,
                            defaults={
                                'locator_strategy': strategies.get(strategy, strategies['xpath']),
                                'locator_value': value,
                                'group': group,
                                'created_by': user,
                                'description': f"Imported from {page_name}"
                            }
                        )
                        
                        # Link to Page Object
                        PageObjectElement.objects.get_or_create(
                            page_object=po,
                            element=element,
                            defaults={
                                'method_name': elem_name,
                                'is_property': True
                            }
                        )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to process {config_file}: {e}"))

    def _parse_locator(self, locator_data):
        # AI_TEST supports list of locators, we take the first one or the string itself
        raw_locator = locator_data
        if isinstance(locator_data, list):
            raw_locator = locator_data[0]
        
        if not isinstance(raw_locator, str):
            return 'xpath', str(raw_locator)

        # Parse prefix x, s, t, etc.
        if raw_locator.startswith('x,'):
            return 'xpath', raw_locator[2:]
        elif raw_locator.startswith('s,'):
            return 'css', raw_locator[2:]
        elif raw_locator.startswith('t,'):
            return 'text', raw_locator[2:]
        elif raw_locator.startswith('id,'):
            return 'id', raw_locator[2:]
        else:
            # Default fallback
            if '//' in raw_locator:
                return 'xpath', raw_locator
            return 'css', raw_locator

    def import_web_cases(self, source_path, user, project_name):
        self.stdout.write("Importing Web cases...")
        project = UiProject.objects.get(name=f"{project_name}_UI")
        
        # 1. Import Common Cases first
        common_path = source_path / 'cases' / 'web' / 'common_step'
        if common_path.exists():
            for case_file in list(common_path.glob('*.yaml')) + list(common_path.glob('*.yml')):
                if case_file.name == 'README.md': continue
                self._import_single_web_case(case_file, project, user, is_common=True)

        # 2. Import Regular Cases (Search all of cases recursively, excluding api)
        all_cases_path = source_path / 'cases'
        # Collect all yaml/yml files
        case_files = list(all_cases_path.rglob('*.yaml')) + list(all_cases_path.rglob('*.yml'))
        
        processed_files = set()
        
        for case_file in case_files:
            # Skip if common step (handled above or just skipped)
            if 'common_step' in str(case_file):
                continue
            # Skip config
            if case_file.name == '页面元素配置.yaml' or case_file.name == 'environment.yaml':
                continue
                
            # Exclude api folder (handled by import_api_cases)
            if 'cases\\api' in str(case_file) or 'cases/api' in str(case_file):
                continue
                
            self._import_single_web_case(case_file, project, user)
            processed_files.add(case_file)

    def _import_single_web_case(self, file_path, project, user, is_common=False):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            case_name = data.get('case_name', file_path.stem)
            if is_common:
                case_name = f"[Common] {case_name}"
            
            # Prepare description with variables
            description = f"Imported from {file_path.name}\n\n"
            if 'case_variables' in data:
                description += "### Case Variables\n| Variable | Value |\n| --- | --- |\n"
                
                # Get Generic Project
                generic_project = Project.objects.filter(name="AI_TEST_Global_Config").first()

                for k, v in data['case_variables'].items():
                    description += f"| {k} | {v} |\n"
                    # Also import as GlobalParameter (scoped by case name to avoid collisions if needed, but user wants them managed)
                    if generic_project:
                        GlobalParameter.objects.update_or_create(
                            key=f"{case_name}_{k}",
                            defaults={
                                'value': str(v),
                                'description': f"Variable for case {case_name}",
                                'project': generic_project,
                                'created_by': user
                            }
                        )

            # Create Test Case
            test_case, _ = TestCase.objects.get_or_create(
                name=case_name,
                project=project,
                defaults={
                    'created_by': user,
                    'status': 'ready',
                    'priority': 'medium'
                }
            )
            test_case.description = description
            test_case.save()

            # Clear existing steps
            test_case.steps.all().delete()

            # Import Steps
            steps = data.get('steps', [])
            self._import_steps(steps, test_case, project, file_path.parent)

            self.stdout.write(f"  Imported Web Case: {case_name}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to import Web case {file_path}: {e}"))

    def _import_steps(self, steps, test_case, project, base_path, current_order=1):
        self.stdout.write(f"    Importing steps for {test_case.name}, count: {len(steps)}")
        for step_data in steps:
            step_name = step_data.get('step_name', f"Step {current_order}")
            self.stdout.write(f"      Processing step: {step_name}")
            
            # Handle Common Step Reference (Flattening)
            if 'common_step' in step_data:
                # ... existing logic ...
                common_ref = step_data['common_step']
                common_file = self._find_common_step_file(base_path, common_ref)
                if common_file:
                    TestCaseStep.objects.create(
                        test_case=test_case,
                        step_number=current_order,
                        action_type='wait',
                        description=f"--- Start Common Step: {common_ref} ---",
                        wait_time=0
                    )
                    current_order += 1
                    # ...
                    try:
                        with open(common_file, 'r', encoding='utf-8') as f:
                            common_data = yaml.safe_load(f)
                        current_order = self._import_steps(common_data.get('steps', []), test_case, project, common_file.parent, current_order)
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"Error reading common step {common_file}: {e}"))
                    
                    TestCaseStep.objects.create(
                        test_case=test_case,
                        step_number=current_order,
                        action_type='wait',
                        description=f"--- End Common Step: {common_ref} ---",
                        wait_time=0
                    )
                    current_order += 1
                else:
                    self.stdout.write(self.style.WARNING(f"      Common step file not found: {common_ref}"))
                continue

            # Handle Actions
            actions = step_data.get('actions', [])
            if not actions:
                self.stdout.write(f"      No actions in step {step_name}")

            for action_item in actions:
                action_str = action_item.get('action') if isinstance(action_item, dict) else action_item
                
                if not action_str or not isinstance(action_str, str):
                    continue

                action_type, element, params, desc = self._parse_action(action_str, project)
                
                try:
                    TestCaseStep.objects.create(
                        test_case=test_case,
                        step_number=current_order,
                        action_type=action_type,
                        element=element,
                        input_value=params.get('input', '') if params else '',
                        action_params=params,
                        description=desc or step_name
                    )
                    current_order += 1
                    self.stdout.write(f"        Created step {current_order-1}: {action_type}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"        Failed to create step: {e}"))
                
                if isinstance(action_item, dict) and 'sleep' in action_item:
                    TestCaseStep.objects.create(
                        test_case=test_case,
                        step_number=current_order,
                        action_type='wait',
                        wait_time=int(float(action_item['sleep']) * 1000),
                        description=f"Sleep {action_item['sleep']}s"
                    )
                    current_order += 1
        
        return current_order

    def _find_common_step_file(self, current_path, common_ref):
        # Heuristic search for common step file
        # 1. Check current dir
        f = current_path / f"{common_ref}.yaml"
        if f.exists(): return f
        
        # 2. Check ../common_step/
        f = current_path.parent / 'common_step' / f"{common_ref}.yaml"
        if f.exists(): return f

        # 3. Check ../../common_step/
        f = current_path.parent.parent / 'common_step' / f"{common_ref}.yaml"
        if f.exists(): return f
        
        # 4. Search in whole tree (slow but safe)
        # Assuming we can get root from current_path by going up until 'cases' is found
        # Simplified: just return None if not found in nearby locations
        return None

    def _parse_action(self, action_str, project):
        # Example: $smart_click(&text_销售权益, 左侧导航-销售权益)
        # Example: $input_text(&input_user, admin)
        
        action_type = 'custom'
        element = None
        params = {'raw_action': action_str}
        description = action_str

        # Extract function name and args
        match = re.match(r'\$(\w+)\((.*)\)', action_str)
        if match:
            func_name = match.group(1)
            # Create/Update CommonMethod
            # We need a project for CommonMethod. Use the generic one or UI project.
            # Assuming 'project' passed here is UiProject, but CommonMethod needs 'projects.Project'.
            # We will use the 'AI_TEST_Global_Config' project.
            
            try:
                generic_project = Project.objects.get(name="AI_TEST_Global_Config")
                CommonMethod.objects.get_or_create(
                    keyword=f"${func_name}",
                    defaults={
                        'name': func_name,
                        'description': f"Auto-imported from usage in test cases. Action: {action_str}",
                        'project': generic_project,
                        'created_by': project.owner # user
                    }
                )
            except Exception:
                pass # Ignore if project not found or other error

            args_str = match.group(2)
            # Split args by comma, but ignore commas inside quotes (simplified split for now)
            args = [a.strip() for a in args_str.split(',')]
            
            # Map function to action type
            if 'click' in func_name:
                action_type = 'click'
            elif 'input' in func_name or 'fill' in func_name:
                action_type = 'fill'
            elif 'wait' in func_name:
                action_type = 'wait'
            elif 'hover' in func_name:
                action_type = 'hover'
            elif 'scroll' in func_name:
                action_type = 'scroll'
            
            # Extract Element Reference (&element_name)
            for arg in args:
                if arg.startswith('&'):
                    elem_name = arg[1:]
                    # Find element in project
                    element = Element.objects.filter(project=project, name=elem_name).first()
                elif action_type == 'fill' and not arg.startswith('&'):
                    params['input'] = arg
            
            if len(args) > 1 and not args[-1].startswith('&') and not args[-1].startswith('$'):
                 description = args[-1] # Assume last arg is description if it's plain text
            elif description == action_str:
                 # If no explicit description found, make a pretty one
                 # func_name + args
                 clean_args = [a for a in args if not a.startswith('&')]
                 description = f"{func_name}: {', '.join(clean_args)}"

        return action_type, element, params, description

    def import_api_interfaces(self, source_path, user, project_name):
        self.stdout.write("Importing API interfaces...")
        project, _ = ApiProject.objects.get_or_create(
            name=project_name,
            defaults={'owner': user, 'status': 'IN_PROGRESS', 'project_type': 'HTTP'}
        )
        
        # Cleanup existing interfaces for this project to avoid duplicates
        # We don't delete the project, just its collections and requests
        # ApiCollection.objects.filter(project=project).delete()

        # Search all yaml files under cases/api AND cases/auto_generated/api
        api_paths = [
            (source_path / 'cases' / 'api', 'cases/api'),
            (source_path / 'cases' / 'auto_generated' / 'api', 'cases/auto_generated/api')
        ]
        
        for path, root_rel in api_paths:
            if path.exists():
                for case_file in list(path.rglob('*.yaml')) + list(path.rglob('*.yml')):
                    # Determine relative path for collection hierarchy
                    try:
                        rel_path = case_file.parent.relative_to(path)
                    except ValueError:
                        rel_path = Path('.')
                    
                    parent_col = None
                    if str(rel_path) != '.':
                        parent_col = self._get_or_create_collection_chain(project, rel_path)
                    
                    self._import_single_interface_file(case_file, project, user, parent_col)

    def _get_or_create_collection_chain(self, project, rel_path):
        """Recursively create collection chain based on path components"""
        parts = rel_path.parts
        parent = None
        for part in parts:
            collection, _ = ApiCollection.objects.get_or_create(
                name=part,
                project=project,
                parent=parent,
                defaults={'description': f"Folder: {part}"}
            )
            parent = collection
        return parent

    def _import_single_interface_file(self, file_path, project, user, parent_collection):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
            # Use parent_collection (directory) directly to avoid redundant folder levels
            collection = parent_collection
            
            steps = data.get('steps', [])
            seen_interfaces = set()
            
            for idx, step in enumerate(steps):
                method = step.get('method', 'GET').upper()
                path = step.get('path', '')
                interface_key = (method, path)
                
                # Only create one interface definition per unique method/path in this collection
                if interface_key not in seen_interfaces:
                    # For interface name, if there's only one unique interface, use file name
                    # otherwise use the step_name of the first occurrence
                    interface_name = file_path.stem if len(steps) == 1 else step.get('step_name', f"{file_path.stem}_{idx}")
                    self._create_api_request(step, collection, user, idx, name_override=interface_name)
                    seen_interfaces.add(interface_key)
                
        except Exception as e:
             self.stdout.write(self.style.ERROR(f"Failed to import interface file {file_path}: {e}"))

    def _create_api_request(self, step_data, collection, user, order, name_override=None):
        name = name_override or step_data.get('step_name', f"Request {order}")
        method = step_data.get('method', 'GET').upper()
        
        # URL Construction
        path = step_data.get('path', '')
        host_raw = step_data.get('host', '')
        url = path
        if '$get_host' in host_raw:
             m = re.search(r'\$get_host\([^,]+,\s*([^)]+)\)', host_raw)
             if m:
                 key = m.group(1).strip()
                 url = f"{{{{{key}}}}}{path}"
        elif host_raw:
             url = f"{host_raw}{path}"
             
        # Headers
        headers = step_data.get('headers', {})
        header_list = []
        
        # Handle $generate_token shortcut
        if isinstance(headers, str) and '$generate_token' in headers:
             header_list.append({
                 'key': 'Authorization',
                 'value': 'Bearer {{token}}',
                 'enabled': True,
                 'description': 'Auto generated token'
             })
        elif isinstance(headers, dict):
            for k, v in headers.items():
                header_list.append({
                    'key': k,
                    'value': v,
                    'enabled': True,
                    'description': ''
                })
        
        # Body
        raw_body = step_data.get('data') or step_data.get('json') or {}
        body = {
            'type': 'json',
            'data': raw_body
        } if raw_body else {}
        
        # Assertions
        assertions = self._parse_assertions(step_data.get('response_assert', {}))
        
        # Extract Rules
        extract_rules = self._parse_extract_rules(step_data.get('extract', []))

        ApiRequest.objects.update_or_create(
            name=name,
            collection=collection,
            defaults={
                'method': method,
                'url': url,
                'headers': header_list,
                'body': body,
                'assertions': assertions,
                'extract_rules': extract_rules,
                'order': order,
                'created_by': user
            }
        )

    def _parse_assertions(self, assert_data):
        assertions = []
        if not assert_data:
            return assertions
            
        # Status Code
        if 'status_code_assert' in assert_data:
            assertions.append({
                'name': 'Status Code Check',
                'type': 'status_code',
                'expected': assert_data['status_code_assert']
            })
            
        # Response Data (Contains)
        if 'response_assert_data' in assert_data:
            assertions.append({
                'name': 'Response Content Check',
                'type': 'contains',
                'expected': assert_data['response_assert_data']
            })
            
        # JSONPath
        if 'jsonpath_assert' in assert_data:
            for i, jp in enumerate(assert_data['jsonpath_assert']):
                assertions.append({
                    'name': f'JSONPath Check {i+1}',
                    'type': 'json_path',
                    'json_path': jp, 
                    'operator': 'true', 
                    'expected': ''
                })
        return assertions

    def _parse_extract_rules(self, extract_list):
        rules = []
        if not extract_list:
            return rules
            
        for item in extract_list:
            # item is like {'extract': '$set_variable(...)'}
            cmd = item.get('extract')
            if not cmd: continue
            
            # Match $set_variable(name, $get_response_data(expr))
            m = re.match(r'\$set_variable\(([^,]+),\s*\$get_response_data\((.+)\)\)', cmd)
            if m:
                var_name = m.group(1).strip()
                expr = m.group(2).strip()
                rules.append({
                    'variable_name': var_name,
                    'type': 'json_path',
                    'json_path': expr
                })
        return rules

    def import_api_cases(self, source_path, user, project_name):
        self.stdout.write("Importing API cases...")
        project = ApiProject.objects.get(name=project_name)
        
        # Cleanup existing API cases for this project
        self.stdout.write("Cleaning up existing API cases...")
        ApiTestCase.objects.filter(project=project).delete()
        
        # Search all yaml files under cases/api AND cases/auto_generated/api
        api_paths = [
            source_path / 'cases' / 'api',
            source_path / 'cases' / 'auto_generated' / 'api'
        ]
        
        api_files = []
        for p in api_paths:
            if p.exists():
                api_files.extend(list(p.rglob('*.yaml')) + list(p.rglob('*.yml')))
        
        for case_file in api_files:
            self._import_single_api_case(case_file, project, user)

    def _import_single_api_case(self, file_path, project, user):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            case_name = data.get('case_name', file_path.stem)
            description = data.get('description', f"Imported from {file_path.name}")
            
            # Create ApiTestCase
            api_case, _ = ApiTestCase.objects.update_or_create(
                project=project,
                name=case_name,
                defaults={
                    'description': description,
                    'created_by': user,
                    'status': 'ready',
                    'priority': 'medium'
                }
            )
            
            # Clear existing steps
            api_case.steps.all().delete()

            steps = data.get('steps', [])
            for idx, step in enumerate(steps):
                step_name = step.get('step_name', f"Step {idx+1}")
                method = step.get('method', 'GET').upper()
                path = step.get('path', '')
                host_raw = step.get('host', '')
                
                # Handle URL Construction
                url = path
                if '$get_host' in host_raw:
                    m = re.search(r'\$get_host\([^,]+,\s*([^)]+)\)', host_raw)
                    if m:
                        key = m.group(1).strip()
                        url = f"{{{{{key}}}}}{path}"
                elif host_raw:
                    url = f"{host_raw}{path}"

                # Find corresponding ApiRequest (Interface)
                # We search by project, method and url to find the consolidated interface
                api_request = ApiRequest.objects.filter(
                    collection__project=project,
                    method=method,
                    url=url
                ).first()

                # Handle Headers for the step
                headers = step.get('headers', {})
                header_list = []
                if isinstance(headers, str) and '$generate_token' in headers:
                     header_list.append({
                         'key': 'Authorization',
                         'value': 'Bearer {{token}}',
                         'enabled': True,
                         'description': 'Auto generated token'
                     })
                elif isinstance(headers, dict):
                    for k, v in headers.items():
                        header_list.append({
                            'key': k,
                            'value': v,
                            'enabled': True,
                            'description': ''
                        })

                # Handle Body for the step
                raw_body = step.get('data') or step.get('json') or {}
                body = {
                    'type': 'json',
                    'data': raw_body
                } if raw_body else {}

                # Handle Assertions and Extract Rules for the step
                assertions = self._parse_assertions(step.get('response_assert', {}))
                extract_rules = self._parse_extract_rules(step.get('extract', []))

                # Create ApiTestCaseStep
                ApiTestCaseStep.objects.create(
                    test_case=api_case,
                    step_number=idx + 1,
                    name=step_name,
                    api_request=api_request,
                    method=method,
                    url=url,
                    headers=header_list,
                    body=body,
                    assertions=assertions,
                    extract_rules=extract_rules,
                    description=step.get('description', '')
                )
            self.stdout.write(f"  Imported API Case: {case_name} with {len(steps)} steps")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to import API case {file_path}: {e}"))
