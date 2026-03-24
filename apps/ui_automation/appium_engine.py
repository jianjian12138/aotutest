import time
import json
import base64
from datetime import datetime
from django.utils import timezone
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.options.ios import XCUITestOptions
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .variable_resolver import resolve_variables
from .models import TestCaseExecution


class AppiumTestExecutor:
    """Appium App Testing Engine for Android & iOS"""

    def __init__(self, test_suite, device_name=None, environment=None, executed_by=None):
        self.test_suite = test_suite
        self.device_name = device_name
        self.environment = environment
        self.executed_by = executed_by
        self.driver = None
        self.test_cases = []
        self.results = []
        self.context_variables = {}

    def get_test_cases(self):
        suite_test_cases = self.test_suite.suite_test_cases.select_related('test_case').order_by('order')
        self.test_cases = [stc.test_case for stc in suite_test_cases]
        return self.test_cases

    def run(self):
        self.get_test_cases()
        if not self.test_cases:
            return []

        # 获取环境配置中的 Appium 能力参数
        caps = self.environment.capabilities if self.environment else {}
        appium_server_url = caps.pop('appium_server_url', 'http://127.0.0.1:4723')
        platform_name = caps.get('platformName', 'Android').lower()

        if platform_name == 'android':
            options = UiAutomator2Options().load_capabilities(caps)
        elif platform_name == 'ios':
            options = XCUITestOptions().load_capabilities(caps)
        else:
            raise ValueError(f"Unsupported Appium platform: {platform_name}")

        test_cases_data = []
        for test_case in self.test_cases:
            case_data = {
                'id': test_case.id,
                'name': test_case.name,
                'project_id': self.test_suite.project.id,
                'steps': []
            }
            steps = test_case.steps.select_related('element', 'element__locator_strategy').order_by('step_number')
            for step in steps:
                step_data = {
                    'id': step.id,
                    'step_number': step.step_number,
                    'action_type': step.action_type,
                    'description': step.description,
                    'input_value': step.input_value,
                    'wait_time': step.wait_time,
                    'assert_type': step.assert_type,
                    'assert_value': step.assert_value,
                    'extract_key': getattr(step, 'extract_key', None),
                    'element': None
                }
                if step.element:
                    step_data['element'] = {
                        'id': step.element.id,
                        'name': step.element.name,
                        'locator_value': step.element.locator_value,
                        'locator_strategy': step.element.locator_strategy.name if step.element.locator_strategy else 'id'
                    }
                case_data['steps'].append(step_data)
            test_cases_data.append(case_data)

        case_executions = {}
        for case_data in test_cases_data:
            ce = TestCaseExecution.objects.create(
                test_case_id=case_data['id'],
                project_id=case_data['project_id'],
                test_suite=self.test_suite,
                execution_source='suite',
                status='pending',
                engine='appium',
                browser=platform_name,
                created_by=self.executed_by
            )
            case_executions[case_data['id']] = ce

        for i, case_data in enumerate(test_cases_data, 1):
            ce = case_executions[case_data['id']]
            ce.started_at = timezone.now()
            ce.status = 'running'
            ce.save()

            try:
                # 每个用例都启动一次 Driver 保证环境干净
                self.driver = webdriver.Remote(appium_server_url, options=options)
                self.driver.implicitly_wait(10)
                
                case_result = self.execute_test_case_appium(case_data)
                self.results.append(case_result)
                
                ce.status = case_result['status']
                ce.finished_at = timezone.now()
                ce.execution_time = (ce.finished_at - ce.started_at).total_seconds()
                ce.execution_logs = json.dumps(case_result['steps'], ensure_ascii=False)
                if case_result['error']:
                    ce.error_message = case_result['error']
                if case_result.get('screenshots'):
                    ce.screenshots = case_result['screenshots']
                ce.save()
            except Exception as e:
                ce.status = 'error'
                ce.error_message = str(e)
                ce.finished_at = timezone.now()
                ce.save()
            finally:
                if self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass
        
        return self.results

    def execute_test_case_appium(self, case_data):
        result = {
            'test_case_id': case_data['id'],
            'test_case_name': case_data['name'],
            'status': 'passed',
            'steps': [],
            'error': None,
            'start_time': datetime.now().isoformat(),
            'screenshots': []
        }

        try:
            for step_data in case_data['steps']:
                step_result = self.execute_step_appium(step_data)
                result['steps'].append(step_result)
                
                if not step_result['success']:
                    result['status'] = 'failed'
                    result['error'] = step_result.get('error', f"步骤 {step_data['step_number']} 执行失败")
                    
                    try:
                        screenshot_b64 = self.driver.get_screenshot_as_base64()
                        result['screenshots'].append({
                            'url': f'data:image/png;base64,{screenshot_b64}',
                            'description': f'Appium 失败截图: 步骤 {step_data["step_number"]}',
                            'step_number': step_data['step_number'],
                            'timestamp': datetime.now().isoformat()
                        })
                    except Exception as e:
                        print(f"Appium 截图失败: {e}")
                    
                    break
        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)

        result['end_time'] = datetime.now().isoformat()
        return result

    def get_appium_by(self, strategy_name):
        strategy_map = {
            'id': AppiumBy.ID,
            'xpath': AppiumBy.XPATH,
            'class name': AppiumBy.CLASS_NAME,
            'accessibility id': AppiumBy.ACCESSIBILITY_ID,
            'android uiautomator': AppiumBy.ANDROID_UIAUTOMATOR,
            'ios class chain': AppiumBy.IOS_CLASS_CHAIN,
            'ios predicate string': AppiumBy.IOS_PREDICATE,
            'name': AppiumBy.NAME
        }
        return strategy_map.get(strategy_name.lower(), AppiumBy.XPATH)

    def execute_step_appium(self, step_data):
        step_result = {
            'id': step_data['id'],
            'step_number': step_data['step_number'],
            'action_type': step_data['action_type'],
            'description': step_data['description'],
            'success': False,
            'error': None
        }

        try:
            wait = WebDriverWait(self.driver, 10)
            element = None
            if step_data.get('element'):
                locator_value = step_data['element']['locator_value']
                strategy = self.get_appium_by(step_data['element']['locator_strategy'])
                
                if '$' in locator_value or '{{' in locator_value:
                    locator_value = resolve_variables(locator_value, self.context_variables)
                
                if step_data['action_type'] in ['waitFor', 'assert', 'getText']:
                    element = wait.until(EC.presence_of_element_located((strategy, locator_value)))
                elif step_data['action_type'] in ['click', 'fill', 'clear']:
                    element = wait.until(EC.element_to_be_clickable((strategy, locator_value)))

            # 解析输入值
            input_val = step_data.get('input_value', '')
            if type(input_val) is str and ('$' in input_val or '{{' in input_val):
                input_val = resolve_variables(input_val, self.context_variables)

            action = step_data['action_type']
            
            if action == 'click':
                element.click()
            elif action == 'fill':
                element.clear()
                element.send_keys(input_val)
            elif action == 'clear':
                element.clear()
            elif action == 'getText':
                text = element.text
                if step_data.get('extract_key'):
                    self.context_variables[step_data['extract_key']] = text
                step_result['actual_value'] = text
            elif action == 'screenshot':
                b64 = self.driver.get_screenshot_as_base64()
                step_result['screenshot'] = f'data:image/png;base64,{b64}'
            elif action == 'wait':
                time.sleep(min(10, step_data.get('wait_time', 1000) / 1000.0))
            elif action == 'assert':
                actual = element.text if element else None
                expected = step_data.get('assert_value', '')
                a_type = step_data.get('assert_type', 'textEquals')
                
                if a_type == 'textEquals':
                    assert str(actual) == str(expected), f"Appium 断言失败: 期望 '{expected}', 实际 '{actual}'"
                elif a_type == 'textContains':
                    assert str(expected) in str(actual), f"Appium 断言失败: '{actual}' 不包含 '{expected}'"
                elif a_type == 'exists':
                    assert element is not None, "Appium 断言失败: 元素不存在"

            time.sleep(step_data.get('wait_time', 500) / 1000.0)
            step_result['success'] = True

        except Exception as e:
            step_result['success'] = False
            step_result['error'] = str(e)

        return step_result
