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




class AirtestRunnerMixin:
    def run_with_airtest(self):
        """使用 Airtest 执行测试"""
        start_time = time.time()
        passed = 0
        failed = 0
        skipped = 0

        # 检查 Airtest 是否可用
        try:
            from airtest.core.api import auto_setup
            from airtest_selenium.proxy import WebChrome
        except ImportError as e:
            error_msg = (
                "Airtest 模块未正确安装。\n\n"
                "请确保已安装: pip install airtest airtest-selenium\n"
                f"详细错误: {str(e)}"
            )
            print(f"❌ {error_msg}")
            
            if self.execution:
                self.update_execution_result(
                    status='FAILED',
                    failed=len(self.test_cases),
                    error_msg=error_msg
                )
            return

        # 预先获取所有测试用例的步骤数据
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
                    'element': None
                }

                if step.element:
                    step_data['element'] = {
                        'id': step.element.id,
                        'name': step.element.name,
                        'locator_value': step.element.locator_value,
                        'locator_strategy': step.element.locator_strategy.name if step.element.locator_strategy else 'css'
                    }

                case_data['steps'].append(step_data)

            test_cases_data.append(case_data)

        # 预先创建所有测试用例执行记录
        case_executions = {}
        
        # 引入全局跨用例上下文变量池
        suite_context_variables = {}
        
        for case_data in test_cases_data:
            case_execution = TestCaseExecution.objects.create(
                test_case_id=case_data['id'],
                project_id=case_data['project_id'],
                test_suite=self.test_suite,
                execution_source='suite',
                status='pending',
                engine=self.engine,
                browser=self.browser,
                headless=self.headless,
                created_by=self.executed_by
            )
            case_executions[case_data['id']] = case_execution

        # Airtest 初始化
        import os
        log_dir = os.path.join('logs', 'airtest', f'exec_{self.execution.id if self.execution else int(time.time())}')
        os.makedirs(log_dir, exist_ok=True)
        # 初始化 Airtest
        auto_setup(__file__, logdir=log_dir, devices=[])

        print(f"准备执行 {len(test_cases_data)} 个测试用例 (Airtest)")
        
        driver = None
        try:
            driver = self.create_airtest_driver()
            print(f"✓ Airtest 浏览器已启动\n")
        except Exception as e:
            print(f"✗ Airtest 浏览器启动失败: {str(e)}")
            for case_data in test_cases_data:
                self.results.append({
                    'test_case_id': case_data['id'],
                    'test_case_name': case_data['name'],
                    'status': 'failed',
                    'steps': [],
                    'error': f"浏览器启动失败: {str(e)}",
                    'start_time': datetime.now().isoformat(),
                    'end_time': datetime.now().isoformat(),
                    'screenshots': []
                })
                failed += 1
            
            for case_result in self.results:
                case_execution = case_executions[case_result['test_case_id']]
                case_execution.status = 'failed'
                case_execution.finished_at = timezone.now()
                case_execution.execution_time = 0
                case_execution.error_message = case_result['error']
                case_execution.save()
            
            duration = time.time() - start_time
            self.update_execution_result('FAILED', 0, len(test_cases_data), 0, duration)
            return

        # 执行测试用例
        for i, case_data in enumerate(test_cases_data, 1):
            print(f"\n{'='*60}")
            print(f"正在执行第 {i}/{len(test_cases_data)} 个用例: {case_data['name']}")
            print(f"{'='*60}")
            
            case_execution = case_executions[case_data['id']]
            case_execution.started_at = timezone.now()
            case_execution.status = 'running'
            case_execution.save()

            try:
                # 清理浏览器状态
                # modify by Trae: 注释掉清理逻辑，支持 Test Suite 内的会话保持（Login Once）
                # if i > 1:
                #     try:
                #         driver.delete_all_cookies()
                #         driver.execute_script("window.localStorage.clear();")
                #         driver.execute_script("window.sessionStorage.clear();")
                #     except:
                #         pass
                
                # 导航
                if self.test_suite.project.base_url:
                    try:
                        print(f"正在导航到: {self.test_suite.project.base_url}")
                        driver.get(self.test_suite.project.base_url)
                        
                        # 等待页面加载
                        try:
                            WebDriverWait(driver, 10).until(
                                lambda d: d.execute_script("return document.readyState") == "complete"
                            )
                        except:
                            pass

                        time.sleep(2)
                        print(f"✓ 成功导航到: {self.test_suite.project.base_url}")
                    except Exception as e:
                        print(f"✗ 导航失败: {str(e)}")
                        self.results.append({
                            'test_case_id': case_data['id'],
                            'test_case_name': case_data['name'],
                            'status': 'failed',
                            'steps': [],
                            'error': f"导航到基础URL失败: {str(e)}",
                            'start_time': datetime.now().isoformat(),
                            'end_time': datetime.now().isoformat(),
                            'screenshots': []
                        })
                        failed += 1
                        continue

                # 复用 Selenium 执行逻辑 (WebChrome 兼容 Selenium WebDriver)
                case_result = self.execute_test_case_selenium_no_db(driver, case_data)
                self.results.append(case_result)
                print(f"✓ 用例执行完成，状态: {case_result['status']}")
                
                # 更新执行记录
                case_execution.status = case_result['status']
                case_execution.finished_at = timezone.now()
                case_execution.execution_time = (case_execution.finished_at - case_execution.started_at).total_seconds()
                case_execution.execution_logs = json.dumps(case_result['steps'], ensure_ascii=False)
                if case_result['error']:
                    case_execution.error_message = case_result['error']
                if case_result.get('screenshots'):
                    case_execution.screenshots = case_result['screenshots']
                case_execution.save()

                if case_result['status'] == 'passed':
                    passed += 1
                elif case_result['status'] == 'failed':
                    failed += 1
                else:
                    skipped += 1

            except Exception as e:
                print(f"✗ 用例执行出现异常: {str(e)}")
                self.results.append({
                    'test_case_id': case_data['id'],
                    'test_case_name': case_data['name'],
                    'status': 'failed',
                    'steps': [],
                    'error': f"用例执行异常: {str(e)}",
                    'start_time': datetime.now().isoformat(),
                    'end_time': datetime.now().isoformat(),
                    'screenshots': []
                })
                failed += 1
                
                case_execution.status = 'failed'
                case_execution.finished_at = timezone.now()
                case_execution.execution_time = (case_execution.finished_at - case_execution.started_at).total_seconds()
                case_execution.error_message = f"用例执行异常: {str(e)}"
                case_execution.save()
        
        # 关闭浏览器
        if driver:
            try:
                print(f"\n{'='*60}")
                print(f"正在关闭浏览器...")
                driver.quit()
                print(f"✓ 浏览器已关闭")
                print(f"{'='*60}\n")
            except Exception as e:
                print(f"✗ 关闭浏览器时出错: {str(e)}")

        duration = time.time() - start_time
        status = 'SUCCESS' if failed == 0 else 'FAILED'
        self.update_execution_result(status, passed, failed, skipped, duration)


    def create_airtest_driver(self):
        """创建 Airtest WebChrome"""
        from airtest_selenium.proxy import WebChrome
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service as ChromeService
        
        options = Options()
        if self.headless:
            options.add_argument('--headless')
        
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        # 安装驱动
        driver_path = ChromeDriverManager().install()
        
        # 创建 WebChrome 实例
        # 注意：WebChrome 构造函数参数可能与 Selenium 不同，通常接受 chrome_options
        driver = WebChrome(executable_path=driver_path, chrome_options=options)
        return driver


