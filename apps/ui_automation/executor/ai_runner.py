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




class AIRunnerMixin:
    def execute_test_suite_ai(self, task_description):
        """
        使用 AI Agent 执行测试套件
        
        Args:
            task_description: 自然语言任务描述
            
        Returns:
            dict: 执行结果，包含状态、步骤详情等
        """
        from .ai_agent import run_ai_task_sync
        
        print(f"🤖 开始 AI 模式执行测试套件: {self.test_suite.name}")
        print(f"📝 任务描述: {task_description}")
        
        start_time = time.time()
        
        try:
            # 更新套件状态为运行中
            self.test_suite.execution_status = 'running'
            self.test_suite.save()
            
            # 执行 AI 任务
            print("🚀 正在调用 AI Agent...")
            history = run_ai_task_sync(task_description)
            
            # 解析执行结果
            all_results = history.all_results if hasattr(history, 'all_results') else []
            model_outputs = history.all_model_outputs if hasattr(history, 'all_model_outputs') else []
            
            # 统计成功和失败的步骤
            passed_count = 0
            failed_count = 0
            steps_detail = []
            
            for i, result in enumerate(all_results):
                step_info = {
                    'step': i + 1,
                    'action': result.extracted_content or str(result.error) if result.error else '未知操作',
                    'success': not result.error,
                    'error': str(result.error) if result.error else None
                }
                
                if result.error:
                    failed_count += 1
                    print(f"  ❌ 步骤 {i + 1}: {step_info['action']} - 失败")
                else:
                    passed_count += 1
                    print(f"  ✅ 步骤 {i + 1}: {step_info['action']}")
                
                steps_detail.append(step_info)
            
            # 判断整体执行状态
            execution_status = 'passed' if failed_count == 0 and passed_count > 0 else 'failed'
            
            # 计算执行时间
            duration = time.time() - start_time
            
            # 更新套件状态
            self.test_suite.execution_status = execution_status
            self.test_suite.passed_count = passed_count
            self.test_suite.failed_count = failed_count
            self.test_suite.save()
            
            # 更新执行记录（如果存在）
            if hasattr(self, 'execution') and self.execution:
                self.update_execution_result(
                    status=execution_status,
                    passed=passed_count,
                    failed=failed_count,
                    skipped=0,
                    duration=duration
                )
            
            result_summary = {
                'status': 'success',
                'execution_status': execution_status,
                'passed_count': passed_count,
                'failed_count': failed_count,
                'total_steps': len(all_results),
                'duration': round(duration, 2),
                'steps': steps_detail,
                'model_outputs': model_outputs
            }
            
            print(f"\n✅ AI 执行完成!")
            print(f"   状态: {execution_status}")
            print(f"   通过: {passed_count}, 失败: {failed_count}")
            print(f"   耗时: {duration:.2f}秒")
            
            return result_summary
            
        except Exception as e:
            # 执行失败，更新状态
            duration = time.time() - start_time
            error_msg = str(e)
            
            print(f"\n❌ AI 执行失败: {error_msg}")
            
            self.test_suite.execution_status = 'failed'
            self.test_suite.failed_count = 1
            self.test_suite.passed_count = 0
            self.test_suite.save()
            
            # 更新执行记录
            if hasattr(self, 'execution') and self.execution:
                self.update_execution_result(
                    status='failed',
                    passed=0,
                    failed=1,
                    skipped=0,
                    duration=duration,
                    error_msg=error_msg
                )
            
            return {
                'status': 'error',
                'execution_status': 'failed',
                'error': error_msg,
                'duration': round(duration, 2)
            }


