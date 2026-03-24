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
def resolve_variables(text, variables):
    """Stubbed variable resolver"""
    return text
    



class BaseTestExecutor:
    def __init__(self, test_suite, engine='playwright', browser='chrome', headless=False, executed_by=None, environment_id=None, device_name=None):
        self.test_suite = test_suite
        self.engine = engine
        self.browser = browser
        self.headless = headless
        self.executed_by = executed_by
        self.environment_id = environment_id
        self.device_name = device_name
        
        # 加载环境配置
        self.environment = None
        if self.environment_id:
            try:
                from .models import TestEnvironment
                self.environment = TestEnvironment.objects.get(id=self.environment_id)
            except Exception as e:
                print(f"Warning: Failed to load environment {self.environment_id}: {str(e)}")
        
        
        self.execution = None
        self.test_cases = []
        self.results = []
        self.context_variables = {}  # 跨用例传递上下文变量池


    def create_execution_record(self):
        """创建测试执行记录"""
        self.execution = TestExecution.objects.create(
            project=self.test_suite.project,
            test_suite=self.test_suite,
            status='RUNNING',
            engine=self.engine,
            browser=self.browser,
            headless=self.headless,
            executed_by=self.executed_by,
            environment=self.browser.upper() if isinstance(self.browser, str) else 'CHROME',
            started_at=timezone.now()
        )
        return self.execution


    def update_execution_result(self, status, passed=0, failed=0, skipped=0, duration=0, error_msg=''):
        """更新执行结果"""
        self.execution.status = status
        self.execution.passed_cases = passed
        self.execution.failed_cases = failed
        self.execution.skipped_cases = skipped
        self.execution.total_cases = passed + failed + skipped
        self.execution.duration = duration
        self.execution.finished_at = timezone.now()
        self.execution.error_message = error_msg
        self.execution.result_data = {
            'test_cases': self.results,
            'summary': {
                'total': self.execution.total_cases,
                'passed': passed,
                'failed': failed,
                'skipped': skipped,
                'pass_rate': round((passed / self.execution.total_cases * 100) if self.execution.total_cases > 0 else 0, 2)
            }
        }
        self.execution.save()

        # 更新套件统计
        self.test_suite.passed_count = passed
        self.test_suite.failed_count = failed
        self.test_suite.execution_status = 'passed' if failed == 0 and passed > 0 else 'failed'
        self.test_suite.save()


    def get_test_cases(self):
        """获取测试套件中的所有测试用例"""
        suite_test_cases = self.test_suite.suite_test_cases.select_related('test_case').order_by('order')
        self.test_cases = [stc.test_case for stc in suite_test_cases]
        print(f"从套件 '{self.test_suite.name}' 获取到 {len(self.test_cases)} 个测试用例")
        for i, tc in enumerate(self.test_cases, 1):
            print(f"  {i}. {tc.name} (ID: {tc.id})")
        return self.test_cases


    def run(self):
        """执行测试套件"""
        # 处理多浏览器并行执行
        browsers = []
        if isinstance(self.browser, list):
            browsers = self.browser
        elif isinstance(self.browser, str):
            self.browser = self.browser.strip()
            if self.browser.startswith('[') and self.browser.endswith(']'):
                try:
                    browsers = json.loads(self.browser)
                except:
                    browsers = [self.browser]
            elif ',' in self.browser:
                browsers = [b.strip() for b in self.browser.split(',')]
            else:
                browsers = [self.browser]
        
        # 如果包含多个浏览器，则分裂为多个执行器
        if len(browsers) > 1:
            print(f"检测到多浏览器配置: {browsers}，开始批量执行...")
            for b in browsers:
                print(f"=== 启动子任务: {b} ===")
                executor = TestExecutor(
                    test_suite=self.test_suite,
                    engine=self.engine,
                    browser=b,
                    headless=self.headless,
                    executed_by=self.executed_by
                )
                executor.run()
            return

        try:
            # 设置环境变量，允许在后台线程中使用同步 ORM
            # 这对于 Playwright 执行是必需的
            import os
            os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'
            
            # 关闭当前线程的数据库连接，避免线程间共享
            connection.close()

            # 创建执行记录
            self.create_execution_record()

            # 获取测试用例
            self.get_test_cases()

            # 根据引擎选择执行方式
            if self.engine == 'playwright':
                self.run_with_playwright()
            elif self.engine == 'appium':
                self.run_with_appium()
            elif self.engine == 'airtest':
                self.run_with_airtest()
            elif self.engine == 'minium':
                self.run_with_minium()
            else:
                self.run_with_selenium()

        except Exception as e:
            print(f"测试执行失败: {str(e)}")
            import traceback
            traceback.print_exc()
            if self.execution:
                self.update_execution_result(
                    status='FAILED',
                    error_msg=f"执行失败: {str(e)}"
                )
        finally:
            # 确保关闭数据库连接
            connection.close()


    def _capture_debug_data(self, page, step_data, project_config=None, timing="after"):
        """采集调试数据"""
        captured_data = {}
        try:
            # 1. 检查是否开启全局采集
            if not project_config or not project_config.get('enable_debug_capture', False):
                return None
            
            # 2. 检查步骤是否开启采集
            if not step_data.get('enable_debug_capture', False):
                return None

            # 3. 检查时机配置
            debug_config = project_config.get('debug_config', {})
            if not debug_config.get(f'enable_{timing}', False):
                return None

            items = debug_config.get(f'{timing}_items', [])
            if not items:
                return None

            import os
            import json
            import time
            from django.conf import settings
            
            # 创建调试数据目录
            # 结构: media/debug_data/project_id/case_id/
            project_id = self.project.id
            case_id = step_data.get('test_case')
            step_name = step_data.get('name', 'unknown_step')
            
            # 使用 MEDIA_ROOT
            relative_dir = os.path.join('debug_data', str(project_id), str(case_id))
            base_dir = os.path.join(settings.MEDIA_ROOT, relative_dir)
            os.makedirs(base_dir, exist_ok=True)
            
            timestamp = int(time.time() * 1000)
            file_prefix = f"{step_name}_{timing}_{timestamp}"
            
            data = {}
            
            # 采集各项数据
            if "annotated" in items:
                pass
                
            if "dom" in items:
                try:
                    data["dom"] = page.content()
                except:
                    pass
            
            if "dropdown" in items:
                pass
                
            if "elements" in items:
                pass

            if "iframes" in items:
                try:
                    data["iframes"] = [frame.url for frame in page.frames]
                except:
                    pass
                    
            if "text_candidates" in items:
                try:
                    data["text_candidates"] = page.evaluate("() => document.body.innerText")
                except:
                    pass
            
            if "logs" in items:
                pass

            # 保存JSON数据
            if data:
                json_filename = f"{file_prefix}.json"
                json_path = os.path.join(base_dir, json_filename)
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                captured_data['data_file'] = os.path.join(settings.MEDIA_URL, relative_dir, json_filename).replace('\\', '/')
                    
            # 截图作为额外文件
            screenshot_filename = f"{file_prefix}.png"
            screenshot_path = os.path.join(base_dir, screenshot_filename)
            try:
                page.screenshot(path=screenshot_path)
                captured_data['screenshot'] = os.path.join(settings.MEDIA_URL, relative_dir, screenshot_filename).replace('\\', '/')
            except:
                pass
            
            return captured_data

        except Exception as e:
            print(f"Error capturing debug data: {e}")
            return None


