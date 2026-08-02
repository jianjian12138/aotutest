"""
UI自动化测试执行服务
支持 Playwright 和 Selenium 测试引擎
"""
import time
import json
from datetime import datetime
from django.utils import timezone
from django.db import connection
from playwright.sync_api import sync_playwright
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.safari.options import Options as SafariOptions
from selenium.webdriver.edge.options import Options as EdgeOptions

from ..models import (
    TestSuite, TestExecution, TestCase, TestCaseStep,
    TestCaseExecution, Element
)
from .variable_resolver import resolve_variables




class MiniumRunnerMixin:
    def run_with_minium(self):
        """执行Minium测试用例"""
        from .minium_engine import MiniumTestEngine
        start_time = time.time()
        passed = 0
        failed = 0
        skipped = 0
        
        # 预先获取所有测试用例的步骤数据
        test_cases_data = []
        for test_case in self.test_cases:
            case_data = {
                'id': test_case.id,
                'name': test_case.name,
                'steps': list(test_case.steps.select_related('element', 'element__locator_strategy').order_by('step_number'))
            }
            test_cases_data.append(case_data)
            
        case_executions = {}
        for case_data in test_cases_data:
            case_execution = TestCaseExecution.objects.create(
                test_case_id=case_data['id'],
                project_id=self.test_suite.project.id,
                test_suite=self.test_suite,
                execution_source='suite',
                status='pending',
                engine=self.engine,
                browser=self.browser,
                headless=self.headless,
                created_by=self.executed_by
            )
            case_executions[case_data['id']] = case_execution
            
        engine = MiniumTestEngine(
            project_path=self.test_suite.project.minium_project_path if hasattr(self.test_suite.project, 'minium_project_path') else None
        )
        
        try:
            engine.start()
            for case_data in test_cases_data:
                case_execution = case_executions[case_data['id']]
                case_execution.started_at = timezone.now()
                case_execution.status = 'running'
                case_execution.save()
                
                steps_results = []
                case_status = 'passed'
                case_error = None
                
                for step in case_data['steps']:
                    element_data = {}
                    if step.element:
                        element_data = {
                            'name': step.element.name,
                            'locator_strategy': step.element.locator_strategy.name if step.element.locator_strategy else 'css',
                            'locator_value': step.element.locator_value
                        }
                    
                    if step.action_type == 'urlJump':
                        # Minium navigate
                        success, log_msg = engine.navigate(step.input_value)
                        screenshot = None
                    else:
                        success, log_msg, screenshot = engine.execute_step(step, element_data)
                        
                    step_result = {
                        'step_number': step.step_number,
                        'action_type': step.action_type,
                        'description': log_msg,
                        'success': success,
                        'error': log_msg if not success else None,
                        'screenshot': screenshot
                    }
                    steps_results.append(step_result)
                    
                    if not success:
                        case_status = 'failed'
                        case_error = log_msg
                        break
                        
                case_execution.status = case_status
                case_execution.finished_at = timezone.now()
                case_execution.execution_time = (case_execution.finished_at - case_execution.started_at).total_seconds()
                case_execution.execution_logs = json.dumps(steps_results, ensure_ascii=False)
                if case_error:
                    case_execution.error_message = case_error
                # Filter screenshots
                screenshots = [s['screenshot'] for s in steps_results if s.get('screenshot')]
                if screenshots:
                    case_execution.screenshots = [{'url': s, 'description': f"Step failure"} for s in screenshots]
                case_execution.save()
                
                if case_status == 'passed':
                    passed += 1
                else:
                    failed += 1
        except Exception as e:
            failed += len(test_cases_data) - passed
            for cid, exec_obj in case_executions.items():
                if exec_obj.status == 'pending':
                    exec_obj.status = 'failed'
                    exec_obj.error_message = f"引擎异常: {str(e)}"
                    exec_obj.save()
        finally:
            engine.stop()
            
        duration = time.time() - start_time
        status = 'SUCCESS' if failed == 0 else 'FAILED'
        self.update_execution_result(status, passed, failed, skipped, duration)


