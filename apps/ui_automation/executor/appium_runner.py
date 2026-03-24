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




class AppiumRunnerMixin:
    def run_with_appium(self):
        """使用 Appium 执行原生 App 测试"""
        start_time = time.time()
        passed = 0
        failed = 0
        skipped = 0
        
        try:
            from .appium_engine import AppiumTestExecutor
        except ImportError as e:
            error_msg = f"Appium 引擎导入失败: {e}. 请确保正确安装 Appium-Python-Client。"
            print(f"❌ {error_msg}")
            if self.execution:
                self.update_execution_result(status='FAILED', failed=len(self.test_cases), error_msg=error_msg)
            return
            
        try:
            # 使用新建的 Appium Executor 驱动执行
            appium_executor = AppiumTestExecutor(
                test_suite=self.test_suite,
                device_name=self.device_name,
                environment=self.environment,
                executed_by=self.executed_by
            )
            
            results = appium_executor.run()
            self.results = results
            
            for res in results:
                if res['status'] == 'passed':
                    passed += 1
                elif res['status'] == 'failed':
                    failed += 1
                else:
                    skipped += 1
                    
        except Exception as e:
            print(f"✗ Appium 套件执行异常: {str(e)}")
            failed = len(self.test_cases)
            if self.execution:
                self.execution.error_message = str(e)
                self.execution.save()
            
        duration = time.time() - start_time
        status = 'SUCCESS' if failed == 0 else 'FAILED'
        self.update_execution_result(status, passed, failed, skipped, duration)


