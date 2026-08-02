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




class SeleniumRunnerMixin:
    def run_with_selenium(self):
        """使用 Selenium 执行测试"""
        start_time = time.time()
        passed = 0
        failed = 0
        skipped = 0

        # 预先获取所有测试用例的步骤数据，避免在Selenium上下文中访问ORM
        test_cases_data = []
        for test_case in self.test_cases:
            case_data = {
                'id': test_case.id,
                'name': test_case.name,
                'project_id': self.test_suite.project.id,
                'steps': []
            }

            # 获取步骤并预先加载所有相关数据
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

                # 如果有元素，预先获取元素数据
                if step.element:
                    step_data['element'] = {
                        'id': step.element.id,
                        'name': step.element.name,
                        'locator_value': step.element.locator_value,
                        'locator_strategy': step.element.locator_strategy.name if step.element.locator_strategy else 'css'
                    }

                case_data['steps'].append(step_data)

            test_cases_data.append(case_data)

        # 预先创建所有测试用例执行记录（不设置 started_at，等实际执行时再设置）
        case_executions = {}
        for case_data in test_cases_data:
            case_execution = TestCaseExecution.objects.create(
                test_case_id=case_data['id'],
                project_id=case_data['project_id'],
                test_suite=self.test_suite,
                execution_source='suite',
                status='pending',  # 初始状态为 pending
                engine=self.engine,
                browser=self.browser,
                headless=self.headless,
                created_by=self.executed_by
                # 注意：不设置 started_at，等用例实际开始执行时再设置
            )
            case_executions[case_data['id']] = case_execution

        # 优化：整个测试套件共用一个浏览器实例，避免频繁启动/关闭
        # 注意：Safari 不支持浏览器复用（会话管理问题），需要每个用例独立启动
        print(f"准备执行 {len(test_cases_data)} 个测试用例")
        
        # Safari 需要独立浏览器实例，其他浏览器可以复用
        use_browser_reuse = self.browser != 'safari'
        
        if use_browser_reuse:
            # 在套件开始时启动一次浏览器（Chrome/Firefox/Edge）
            driver = None
            try:
                driver = self.create_selenium_driver()
                print(f"✓ 浏览器已启动（将复用于所有用例）\n")
            except Exception as e:
                print(f"✗ 浏览器启动失败: {str(e)}")
                # 标记所有用例为失败
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
                # 更新执行记录并返回
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
        else:
            # Safari：不预先启动浏览器，每个用例独立启动
            driver = None
            print(f"ℹ️  Safari 浏览器将为每个用例独立启动（Safari 不支持浏览器复用）\n")

        # 引入全局跨用例上下文变量池
        {}

        # 执行所有测试用例
        for i, case_data in enumerate(test_cases_data, 1):
            print(f"\n{'='*60}")
            print(f"正在执行第 {i}/{len(test_cases_data)} 个用例: {case_data['name']}")
            print(f"{'='*60}")
            
            # 记录用例实际开始执行时间
            case_execution = case_executions[case_data['id']]
            case_execution.started_at = timezone.now()
            case_execution.status = 'running'
            case_execution.save()

            # Safari：为每个用例启动新的浏览器
            if not use_browser_reuse:
                try:
                    driver = self.create_selenium_driver()
                    print(f"✓ Safari 浏览器已启动")
                except Exception as e:
                    print(f"✗ Safari 浏览器启动失败: {str(e)}")
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
                    # 更新执行记录
                    case_execution.status = 'failed'
                    case_execution.finished_at = timezone.now()
                    case_execution.execution_time = (case_execution.finished_at - case_execution.started_at).total_seconds()
                    case_execution.error_message = f"浏览器启动失败: {str(e)}"
                    case_execution.save()
                    continue

            try:
                # 在每个用例开始前清理浏览器状态（仅对复用浏览器的情况，且跳过第1个用例）
                # 第1个用例浏览器刚启动，无需清理；从第2个用例开始才需要清理
                if use_browser_reuse and i > 1:
                    try:
                        print(f"🧹 清理浏览器状态...")
                        # 清除所有 Cookie
                        driver.delete_all_cookies()
                        # 清除 localStorage 和 sessionStorage
                        driver.execute_script("window.localStorage.clear();")
                        driver.execute_script("window.sessionStorage.clear();")
                        print(f"✓ 浏览器状态已清理")
                    except Exception as clean_error:
                        print(f"⚠️  清理浏览器状态失败: {str(clean_error)}，继续执行...")
                        pass  # 如果清理失败，继续执行
                
                # 导航到项目基础URL
                if self.test_suite.project.base_url:
                    try:
                        print(f"正在导航到: {self.test_suite.project.base_url}")

                        # 检测是否在Linux服务器环境
                        import platform
                        is_linux = platform.system() == 'Linux'

                        # 导航到URL
                        driver.get(self.test_suite.project.base_url)

                        # 等待页面基本加载完成
                        # 在服务器环境（特别是无头模式）需要更长的等待时间
                        try:
                            WebDriverWait(driver, 15 if is_linux else 10).until(
                                lambda d: d.execute_script("return document.readyState") == "complete"
                            )
                        except Exception:
                            pass  # 即使超时也继续执行

                        # 额外等待，确保动态内容加载（Vue/React等SPA应用）
                        extra_wait = 3 if is_linux else 2
                        time.sleep(extra_wait)

                        print(f"✓ 成功导航到: {self.test_suite.project.base_url} (已等待页面加载完成，额外{extra_wait}秒)")
                    except Exception as e:
                        print(f"✗ 导航失败: {str(e)}")
                        # 导航失败，记录错误并继续下一个用例
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

                # 执行测试用例
                case_result = self.execute_test_case_selenium_no_db(driver, case_data, context_variables=self.context_variables)
                self.results.append(case_result)
                print(f"✓ 用例执行完成，状态: {case_result['status']}")

                # 立即更新该用例的执行记录（包含准确的执行时间）
                case_execution = case_executions[case_data['id']]
                case_execution.status = case_result['status']
                case_execution.finished_at = timezone.now()
                case_execution.execution_time = (case_execution.finished_at - case_execution.started_at).total_seconds()
                case_execution.execution_logs = json.dumps(case_result['steps'], ensure_ascii=False)
                if case_result['error']:
                    case_execution.error_message = case_result['error']
                if case_result.get('screenshots'):
                    case_execution.screenshots = case_result['screenshots']
                case_execution.save()
                
                print(f"⏱️  执行时长: {case_execution.execution_time:.2f}秒")

                if case_result['status'] == 'passed':
                    passed += 1
                elif case_result['status'] == 'failed':
                    failed += 1
                else:
                    skipped += 1

            except Exception as e:
                print(f"✗ 用例执行出现异常: {str(e)}")
                # 记录异常
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
                
                # 更新执行记录
                case_execution = case_executions[case_data['id']]
                case_execution.status = 'failed'
                case_execution.finished_at = timezone.now()
                case_execution.execution_time = (case_execution.finished_at - case_execution.started_at).total_seconds()
                case_execution.error_message = f"用例执行异常: {str(e)}"
                case_execution.save()
            
            finally:
                # Safari：每个用例执行完都关闭浏览器
                if not use_browser_reuse and driver:
                    try:
                        driver.quit()
                        print(f"✓ Safari 浏览器已关闭\n")
                    except Exception as e:
                        print(f"✗ 关闭 Safari 浏览器时出错: {str(e)}\n")
                    driver = None

        # 所有用例执行完毕后，关闭浏览器（仅对复用浏览器的情况）
        if use_browser_reuse and driver:
            try:
                print(f"\n{'='*60}")
                print(f"正在关闭浏览器...")
                driver.quit()
                print(f"✓ 浏览器已关闭")
                print(f"{'='*60}\n")
            except Exception as e:
                print(f"✗ 关闭浏览器时出错: {str(e)}")

        # 注意：每个用例的执行记录已在执行过程中实时更新，不需要在这里统一更新
        
        duration = time.time() - start_time
        status = 'SUCCESS' if failed == 0 else 'FAILED'
        self.update_execution_result(status, passed, failed, skipped, duration)


    def create_selenium_driver(self):
        """创建 Selenium WebDriver"""
        from selenium.webdriver.chrome.service import Service as ChromeService
        from selenium.webdriver.firefox.service import Service as FirefoxService
        from selenium.webdriver.edge.service import Service as EdgeService
        from webdriver_manager.chrome import ChromeDriverManager
        from webdriver_manager.firefox import GeckoDriverManager
        from webdriver_manager.microsoft import EdgeChromiumDriverManager
        from apps.ui_automation.selenium_engine import SeleniumTestEngine
        import os
        
        # 配置webdriver_manager使用本地缓存，避免每次下载
        # 缓存目录：~/.wdm
        os.environ['WDM_LOG_LEVEL'] = '0'  # 减少日志输出
        os.environ['WDM_PRINT_FIRST_LINE'] = 'False'  # 不打印首行信息
        
        # 检查浏览器是否可用
        is_available, error_msg = SeleniumTestEngine.check_browser_available(self.browser)
        if not is_available:
            # 提供安装建议
            install_tips = {
                'chrome': 'brew install --cask google-chrome',
                'firefox': 'brew install --cask firefox',
                'edge': 'brew install --cask microsoft-edge',
            }
            tip = install_tips.get(self.browser, '')
            full_error = f"{error_msg}\n\n💡 安装命令（macOS）：{tip}" if tip else error_msg
            raise Exception(full_error)
        
        if self.browser == 'chrome':
            options = ChromeOptions()
            if self.headless:
                options.add_argument('--headless')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            
            # 禁用自动化特征检测
            options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
            options.add_experimental_option('useAutomationExtension', False)
            
            # 禁用密码保存和泄露提醒（解决弹框遮挡元素的问题）
            prefs = {
                'credentials_enable_service': False,  # 禁用密码保存服务
                'profile.password_manager_enabled': False,  # 禁用密码管理器
                'profile.default_content_setting_values.notifications': 2,  # 禁用通知
                'autofill.profile_enabled': False,  # 禁用自动填充
                'profile.default_content_setting_values.automatic_downloads': 1,  # 允许自动下载
                'password_manager_leak_detection': False,  # 禁用密码泄露检测（prefs级别）
                'safebrowsing.enabled': False,  # 禁用安全浏览
                'safebrowsing.disable_download_protection': True,
                'intl.accept_languages': 'zh-CN,zh,en-US,en',  # 设置语言
                'profile.exit_type': 'Normal',  # 避免"Chrome未正常关闭"提示
            }
            options.add_experimental_option('prefs', prefs)
            
            # 禁用密码泄露检查和其他安全警告（更全面的设置）
            # 将所有 disable-features 合并为一个参数，避免覆盖
            disabled_features = [
                'PasswordLeakDetection',
                'PrivacySandboxSettings4',
                'TranslateUI',
                'SavePasswordBubble',
                'AutofillServerCommunication',
                'CreditCardSave',
                'HeaderUI',
                'AccountConsistency',
            ]
            options.add_argument(f'--disable-features={",".join(disabled_features)}')
            
            options.add_argument('--disable-infobars')  # 禁用信息栏
            options.add_argument('--disable-save-password-bubble')  # 禁用保存密码气泡
            options.add_argument('--disable-password-generation')  # 禁用密码生成
            options.add_argument('--disable-password-manager-reauthentication')  # 禁用密码管理器重新认证
            options.add_argument('--disable-popup-blocking')  # 禁用弹窗拦截
            options.add_argument('--disable-notifications')  # 禁用所有通知
            options.add_argument('--no-default-browser-check') # 禁用默认浏览器检查
            options.add_argument('--no-first-run') # 禁用首次运行界面
            
            # 针对密码弹窗的额外参数
            options.add_argument('--password-store=basic')
            options.add_argument('--use-mock-keychain')
            options.add_argument('--disable-background-timer-throttling')
            options.add_argument('--disable-renderer-backgrounding')
            options.add_argument('--disable-device-discovery-notifications')
            
            # 移动端设备模拟
            dev_name_to_use = self.device_name or (self.environment.device_name if self.environment else None)
            dev_type_to_use = self.environment.device_type if self.environment else None
            
            if dev_name_to_use:
                print(f"✓ 启用 Selenium 设备模拟: {dev_name_to_use}")
                mobile_emulation = {"deviceName": dev_name_to_use}
                options.add_experimental_option("mobileEmulation", mobile_emulation)
            elif dev_type_to_use == 'MOBILE':
                print("✓ 启用默认移动端模拟 (iPhone 12)")
                mobile_emulation = {"deviceName": "iPhone 12 Pro"} # Selenium Chrome 中通常有 iPhone 12 Pro
                options.add_experimental_option("mobileEmulation", mobile_emulation)
            
            # 使用缓存优先策略
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        elif self.browser == 'firefox':
            options = FirefoxOptions()
            if self.headless:
                options.add_argument('--headless')
            options.add_argument('--width=1920')
            options.add_argument('--height=1080')
            
            # 性能优化：禁用不必要的功能加快启动速度
            options.set_preference('browser.cache.disk.enable', False)
            options.set_preference('browser.cache.memory.enable', True)
            options.set_preference('browser.cache.offline.enable', False)
            options.set_preference('network.http.use-cache', False)
            options.set_preference('browser.startup.homepage', 'about:blank')
            options.set_preference('startup.homepage_welcome_url', 'about:blank')
            options.set_preference('startup.homepage_welcome_url.additional', 'about:blank')
            # 禁用自动更新检查
            options.set_preference('app.update.auto', False)
            options.set_preference('app.update.enabled', False)
            # 禁用扩展和插件检查
            options.set_preference('extensions.update.enabled', False)
            options.set_preference('extensions.update.autoUpdateDefault', False)
            
            # 使用缓存优先策略
            service = FirefoxService(GeckoDriverManager().install())
            driver = webdriver.Firefox(service=service, options=options)
        elif self.browser == 'safari':
            # Safari 不支持 headless 模式
            # 需要先启用：sudo safaridriver --enable
            # 并在 Safari 设置 -> 开发菜单中启用"允许远程自动化"
            try:
                driver = webdriver.Safari()
                driver.set_window_size(1920, 1080)
            except Exception as e:
                error_msg = str(e)
                if 'Could not create a session' in error_msg or 'InvalidSessionIdException' in error_msg:
                    raise Exception(
                        "Safari 远程自动化未启用。\n\n"
                        "请按以下步骤配置：\n"
                        "1. 在终端执行: sudo safaridriver --enable\n"
                        "2. 打开 Safari → 设置 → 高级 → 勾选'在菜单栏中显示开发菜单'\n"
                        "3. Safari 菜单栏 → 开发 → 勾选'允许远程自动化'\n\n"
                        f"原始错误: {error_msg}"
                    )
                raise
        elif self.browser == 'edge':
            options = EdgeOptions()
            if self.headless:
                options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            
            # 使用缓存优先策略
            service = EdgeService(EdgeChromiumDriverManager().install())
            driver = webdriver.Edge(service=service, options=options)
        else:
            # 默认使用Chrome
            options = ChromeOptions()
            if self.headless:
                options.add_argument('--headless')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            
            # 禁用自动化特征检测
            options.add_experimental_option('excludeSwitches', ['enable-automation'])
            options.add_experimental_option('useAutomationExtension', False)
            
            # 禁用密码保存和泄露提醒（解决弹框遮挡元素的问题）
            prefs = {
                'credentials_enable_service': False,  # 禁用密码保存服务
                'profile.password_manager_enabled': False,  # 禁用密码管理器
                'profile.default_content_setting_values.notifications': 2,  # 禁用通知
                'autofill.profile_enabled': False,  # 禁用自动填充
                'profile.default_content_setting_values.automatic_downloads': 1,  # 允许自动下载
            }
            options.add_experimental_option('prefs', prefs)
            
            # 禁用密码泄露检查和其他安全警告
            options.add_argument('--disable-features=PasswordLeakDetection')  # 禁用密码泄露检测
            options.add_argument('--disable-features=PrivacySandboxSettings4')  # 禁用隐私沙盒
            options.add_argument('--disable-features=TranslateUI')  # 禁用翻译提示
            options.add_argument('--disable-infobars')  # 禁用信息栏
            
            # 移动端设备模拟
            if self.environment and self.environment.device_name:
                print(f"✓ 启用 Selenium 设备模拟: {self.environment.device_name}")
                mobile_emulation = {"deviceName": self.environment.device_name}
                options.add_experimental_option("mobileEmulation", mobile_emulation)
            elif self.environment and self.environment.device_type == 'MOBILE':
                print("✓ 启用默认移动端模拟 (iPhone 12)")
                mobile_emulation = {"deviceName": "iPhone 12 Pro"}
                options.add_experimental_option("mobileEmulation", mobile_emulation)

            # 使用缓存优先策略
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)

        return driver


    def execute_test_case_selenium_no_db(self, driver, case_data, context_variables=None):
        """使用 Selenium 执行单个测试用例（不访问数据库）

        Args:
            driver: Selenium WebDriver对象
            case_data: 预先准备的用例数据字典，包含id, name, project_id, steps等
            context_variables: 运行时上下文变量池
        """
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
            # 遍历预先准备好的步骤数据
            for step_data in case_data['steps']:
                step_result = self.execute_step_selenium(driver, step_data, context_variables=context_variables)
                result['steps'].append(step_result)
                
                # 步骤执行完后添加短暂延迟，确保页面状态稳定
                # 特别是点击操作后，可能触发动画、下拉框展开等
                if step_result['success'] and step_data['action_type'] in ['click', 'fill', 'hover']:
                    # 点击操作后等待更长时间（下拉框展开动画）
                    if step_data['action_type'] == 'click':
                        time.sleep(0.8)  # 等待800ms，确保下拉框完全展开
                    else:
                        time.sleep(0.3)  # 其他操作等待300ms

                # 如果步骤失败,捕获失败截图
                if not step_result['success']:
                    result['status'] = 'failed'
                    # 使用step的error信息作为case的error
                    result['error'] = step_result.get('error', f"步骤 {step_data['step_number']} 执行失败")

                    # 捕获失败截图
                    try:
                        import base64
                        screenshot_bytes = driver.get_screenshot_as_png()
                        screenshot_base64 = base64.b64encode(screenshot_bytes).decode()
                        result['screenshots'].append({
                            'url': f'data:image/png;base64,{screenshot_base64}',
                            'description': f'步骤 {step_data["step_number"]} 失败截图: {step_data.get("description", "")}',
                            'step_number': step_data['step_number'],
                            'timestamp': datetime.now().isoformat()
                        })
                    except Exception as screenshot_error:
                        print(f"捕获失败截图失败: {str(screenshot_error)}")

                    break

        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)

            # 捕获异常截图
            try:
                import base64
                screenshot_bytes = driver.get_screenshot_as_png()
                screenshot_base64 = base64.b64encode(screenshot_bytes).decode()
                result['screenshots'].append({
                    'url': f'data:image/png;base64,{screenshot_base64}',
                    'description': f'异常截图: {str(e)}',
                    'step_number': None,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as screenshot_error:
                print(f"捕获异常截图失败: {str(screenshot_error)}")

        result['end_time'] = datetime.now().isoformat()
        return result


    def execute_test_case_selenium(self, driver, case_data):
        """使用 Selenium 执行单个测试用例 - 已弃用，保留用于���后兼容

        Args:
            driver: Selenium WebDriver对象
            case_data: 预先准备的用例数据字典，包含id, name, project_id, steps等
        """
        result = {
            'test_case_id': case_data['id'],
            'test_case_name': case_data['name'],
            'status': 'passed',
            'steps': [],
            'error': None,
            'start_time': datetime.now().isoformat()
        }

        case_execution = TestCaseExecution.objects.create(
            test_case_id=case_data['id'],
            project_id=case_data['project_id'],
            status='running',
            browser=self.browser,
            created_by=self.executed_by,
            started_at=timezone.now()
        )

        try:
            # 遍历预先准备好的步骤数据
            for step_data in case_data['steps']:
                step_result = self.execute_step_selenium(driver, step_data)
                result['steps'].append(step_result)

                if not step_result['success']:
                    result['status'] = 'failed'
                    # 使用step的error信息作为case的error
                    result['error'] = step_result.get('error', f"步骤 {step_data['step_number']} 执行失败")
                    break

            # 更新用例执行记录
            case_execution.status = result['status']
            case_execution.finished_at = timezone.now()
            case_execution.execution_time = (case_execution.finished_at - case_execution.started_at).total_seconds()
            case_execution.execution_logs = json.dumps(result['steps'], ensure_ascii=False)
            if result['error']:
                case_execution.error_message = result['error']
            case_execution.save()

        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)

            case_execution.status = 'error'
            case_execution.error_message = str(e)
            case_execution.finished_at = timezone.now()
            case_execution.save()

        result['end_time'] = datetime.now().isoformat()
        return result


    def execute_step_selenium(self, driver, step_data, context_variables=None):
        """使用 Selenium 执行单个步骤

        Args:
            driver: Selenium WebDriver对象
            step_data: 预先准备的步骤数据字典
        """
        from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
        start_time = time.time()

        step_result = {
            'step_number': step_data['step_number'],
            'action_type': step_data['action_type'],
            'description': step_data['description'],
            'success': False,
            'error': None
        }

        try:
            if step_data['element']:
                element = step_data['element']
                locator_value = element['locator_value']
                locator_strategy = element['locator_strategy'].lower()
                element_name = element.get('name', '未知元素')

                # 根据定位策略获取元素
                wait = WebDriverWait(driver, step_data['wait_time'] / 1000)

                # 自动修正定位策略：如果值以 // 开头，强制使用 XPath
                if locator_value.startswith('//') or locator_value.startswith('xpath='):
                    locator_strategy = 'xpath'
                    if locator_value.startswith('xpath='):
                        locator_value = locator_value[6:]

                # 根据定位策略构造 Playwright 选择器
                if locator_strategy in ['css', 'css selector']:
                    by = By.CSS_SELECTOR
                elif locator_strategy == 'xpath':
                    by = By.XPATH
                elif locator_strategy == 'id':
                    by = By.ID
                elif locator_strategy == 'name':
                    by = By.NAME
                elif locator_strategy in ['class', 'class name']:
                    by = By.CLASS_NAME
                elif locator_strategy in ['tag', 'tag name']:
                    by = By.TAG_NAME
                elif locator_strategy == 'link text':
                    by = By.LINK_TEXT
                elif locator_strategy == 'partial link text':
                    by = By.PARTIAL_LINK_TEXT
                else:
                    by = By.CSS_SELECTOR

                # 根据操作类型选择合适的等待条件
                if step_data['action_type'] == 'click':
                    # 点击操作：等待元素可点击（解决 stale element 问题）
                    # 通过定位器特征自动识别下拉框选项
                    is_dropdown_option = (
                        'dropdown' in locator_value.lower() or 
                        'el-select' in locator_value.lower() or 
                        'role="option"' in element_name.lower() or 
                        '下拉' in element_name or 
                        '选项' in element_name or
                        'el-select-dropdown__item' in locator_value.lower() or
                        ('//li' in locator_value and 'span=' in locator_value)  # XPath 下拉框模式
                    )
                    
                    if is_dropdown_option:
                        # 下拉框选项：特殊处理，遍历所有匹配元素找到可见的那个
                        print(f"  检测到下拉框选项（定位器匹配），尝试查找可见元素...")
                        
                        # 自定义等待逻辑：轮询查找可见元素
                        end_time = time.time() + (step_data['wait_time'] / 1000)
                        found_visible = False
                        
                        while time.time() < end_time:
                            try:
                                # 查找所有匹配元素
                                elements = driver.find_elements(by, locator_value)
                                for el in elements:
                                    if el.is_displayed():
                                        element_obj = el
                                        found_visible = True
                                        print(f"  ✓ 找到可见的下拉框选项")
                                        break
                                
                                if found_visible:
                                    break
                                    
                                time.sleep(0.5)
                            except Exception:
                                time.sleep(0.5)
                        
                        if not found_visible:
                            # 如果没找到可见元素，回退到默认行为（可能会抛出超时）
                            print(f"  ⚠️ 未找到可见的下拉框选项，尝试默认等待...")
                            element_obj = wait.until(EC.visibility_of_element_located((by, locator_value)))
                    else:
                        element_obj = wait.until(EC.element_to_be_clickable((by, locator_value)))
                else:
                    # 其他操作：等待元素出现
                    element_obj = wait.until(EC.presence_of_element_located((by, locator_value)))

                # 执行操作（添加 stale element 重试机制）
                max_retries = 3
                
                if step_data['action_type'] == 'click':
                    for attempt in range(max_retries):
                        try:
                            # 每次重试都重新查找元素（解决stale element问题）
                            if attempt > 0:
                                print(f"⚠️  重新查找元素（Stale Element 重试）... (尝试 {attempt + 1}/{max_retries})")
                                # 增加等待时间，让页面 DOM 稳定（对于 Vue/React 应用很重要）
                                wait_time = 1.0 if attempt == 1 else 1.5  # 第一次重试等1秒，第二次重试等1.5秒
                                print(f"等待 {wait_time}秒 让页面稳定...")
                                time.sleep(wait_time)
                                # 重新定位元素
                                if is_dropdown_option:
                                    element_obj = wait.until(EC.visibility_of_element_located((by, locator_value)))
                                else:
                                    element_obj = wait.until(EC.element_to_be_clickable((by, locator_value)))
                                # 等待元素状态稳定
                                time.sleep(0.3)
                                print(f"✓ 元素重新定位成功")
                            
                            # 对于下拉框选项，先滚动到可视区域
                            if 'dropdown' in locator_value.lower() or 'el-select' in locator_value.lower() or '下拉' in element_name or '选项' in element_name:
                                try:
                                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element_obj)
                                    time.sleep(0.3)  # 等待滚动完成
                                except Exception:
                                    pass
                            
                            # 如果是 el-select 容器，尝试点击内部的可点击区域
                            if 'el-select' in locator_value.lower() and 'ancestor::' in locator_value.lower():
                                # 这是点击 el-select 容器，需要找到真正的触发器
                                try:
                                    # 尝试找到并点击内部的 input 或 wrapper
                                    clickable = element_obj.find_element(By.CSS_SELECTOR, '.el-select__wrapper, input')
                                    clickable.click()
                                except Exception:
                                    # 如果找不到，直接点击容器
                                    element_obj.click()
                            else:
                                element_obj.click()
                            
                            step_result['success'] = True
                            break
                        except StaleElementReferenceException:
                            if attempt < max_retries - 1:
                                print(f"⚠️  元素过期，正在重试... ({attempt + 1}/{max_retries})")
                                # 继续下一次循环，会重新查找元素
                                continue
                            else:
                                raise
                        except Exception as click_error:
                            # 如果是下拉框选项且点击失败，尝试使用 JavaScript 点击
                            if attempt < max_retries - 1 and ('not visible' in str(click_error).lower() or 'not interactable' in str(click_error).lower()):
                                print(f"⚠️  元素不可交互，尝试使用 JavaScript 点击... ({attempt + 1}/{max_retries})")
                                try:
                                    driver.execute_script("arguments[0].click();", element_obj)
                                    step_result['success'] = True
                                    break
                                except Exception:
                                    if attempt < max_retries - 1:
                                        time.sleep(0.5)
                                        # 重新定位
                                        if 'dropdown' in locator_value.lower() or 'el-select' in locator_value.lower():
                                            element_obj = wait.until(EC.visibility_of_element_located((by, locator_value)))
                                        else:
                                            element_obj = wait.until(EC.element_to_be_clickable((by, locator_value)))
                                    else:
                                        raise
                            else:
                                raise

                elif step_data['action_type'] == 'fill':
                    # 解析输入值中的变量表达式
                    resolved_value = resolve_variables(step_data['input_value'], context_vars=context_variables)
                    
                    for attempt in range(max_retries):
                        try:
                            element_obj.clear()
                            element_obj.send_keys(resolved_value)
                            step_result['success'] = True
                            
                            # 记录解析后的值（用于调试）
                            if resolved_value != step_data['input_value']:
                                step_result['resolved_value'] = resolved_value
                                print(f"  ✓ 变量解析: {step_data['input_value']} -> {resolved_value}")
                            
                            break
                        except StaleElementReferenceException:
                            if attempt < max_retries - 1:
                                print(f"⚠️  元素过期（Stale Element），正在重试... (尝试 {attempt + 2}/{max_retries})")
                                # 增加等待时间，让页面 DOM 稳定
                                wait_time = 1.0 if attempt == 0 else 1.5
                                print(f"等待 {wait_time}秒 让页面稳定...")
                                time.sleep(wait_time)
                                element_obj = wait.until(EC.presence_of_element_located((by, locator_value)))
                                time.sleep(0.3)  # 确保元素状态稳定
                                print(f"✓ 元素重新定位成功")
                            else:
                                raise

                elif step_data['action_type'] == 'upload':
                    import os
                    from .variable_resolver import resolve_variables
                    file_path = resolve_variables(step_data['input_value'], context_vars=context_variables)
                    
                    if not os.path.exists(file_path):
                        step_result['success'] = False
                        step_result['error'] = f"✗ 文件不存在: '{file_path}'"
                    else:
                        for attempt in range(max_retries):
                            try:
                                element_obj.send_keys(file_path)
                                step_result['success'] = True
                                if file_path != step_data['input_value']:
                                    step_result['resolved_value'] = file_path
                                    print(f"  ✓ 文件路径解析: {step_data['input_value']} -> {file_path}")
                                break
                            except StaleElementReferenceException:
                                if attempt < max_retries - 1:
                                    print(f"⚠️  元素过期（Stale Element），正在重试... (尝试 {attempt + 2}/{max_retries})")
                                    wait_time = 1.0 if attempt == 0 else 1.5
                                    time.sleep(wait_time)
                                    element_obj = wait.until(EC.presence_of_element_located((by, locator_value)))
                                    time.sleep(0.3)
                                else:
                                    raise

                elif step_data['action_type'] == 'getText':
                    for attempt in range(max_retries):
                        try:
                            text = element_obj.text
                            step_result['result'] = text
                            step_result['success'] = True
                            
                            # 提取变量到上下文池
                            extract_key = step_data.get('extract_key')
                            if extract_key and context_variables is not None:
                                context_variables[extract_key] = text
                                print(f"  ✓ 提取变量至上下文: {extract_key} = {text}")
                            break
                        except StaleElementReferenceException:
                            if attempt < max_retries - 1:
                                print(f"⚠️  元素过期（Stale Element），正在重试... (尝试 {attempt + 2}/{max_retries})")
                                # 增加等待时间，让页面 DOM 稳定
                                wait_time = 1.0 if attempt == 0 else 1.5
                                print(f"等待 {wait_time}秒 让页面稳定...")
                                time.sleep(wait_time)
                                element_obj = wait.until(EC.presence_of_element_located((by, locator_value)))
                                time.sleep(0.3)  # 确保元素状态稳定
                                print(f"✓ 元素重新定位成功")
                            else:
                                raise

                elif step_data['action_type'] == 'hover':
                    from selenium.webdriver.common.action_chains import ActionChains
                    for attempt in range(max_retries):
                        try:
                            ActionChains(driver).move_to_element(element_obj).perform()
                            step_result['success'] = True
                            break
                        except StaleElementReferenceException:
                            if attempt < max_retries - 1:
                                print(f"⚠️  元素过期（Stale Element），正在重试... (尝试 {attempt + 2}/{max_retries})")
                                # 增加等待时间，让页面 DOM 稳定
                                wait_time = 1.0 if attempt == 0 else 1.5
                                print(f"等待 {wait_time}秒 让页面稳定...")
                                time.sleep(wait_time)
                                element_obj = wait.until(EC.presence_of_element_located((by, locator_value)))
                                time.sleep(0.3)  # 确保元素状态稳定
                                print(f"✓ 元素重新定位成功")
                            else:
                                raise

                elif step_data['action_type'] == 'screenshot':
                    screenshot_path = f'screenshots/step_{step_data["step_number"]}.png'
                    driver.save_screenshot(screenshot_path)
                    step_result['screenshot'] = screenshot_path
                    step_result['success'] = True

                elif step_data['action_type'] == 'assert':
                    # 解析断言值中的变量
                    from .variable_resolver import resolve_variables
                    resolved_assert_value = resolve_variables(step_data['assert_value'], context_vars=context_variables)
                    if resolved_assert_value != step_data['assert_value']:
                         print(f"  ✓ 断言变量解析: {step_data['assert_value']} -> {resolved_assert_value}")

                    if step_data['assert_type'] == 'textContains':
                        text = element_obj.text
                        if resolved_assert_value in text:
                            step_result['success'] = True
                        else:
                            # 格式化为详细的错误信息，与selenium_engine.py保持一致
                            log = f"✗ 断言失败: 文本不包含 '{resolved_assert_value}'\n"
                            log += f"  - 实际文本: '{text}'"
                            step_result['error'] = log
                    elif step_data['assert_type'] == 'textEquals':
                        text = element_obj.text
                        if text == resolved_assert_value:
                            step_result['success'] = True
                        else:
                            # 格式化为详细的错误信息
                            log = f"✗ 断言失败: 文本不等于 '{resolved_assert_value}'\n"
                            log += f"  - 期望: '{resolved_assert_value}'\n"
                            log += f"  - 实际: '{text}'"
                            step_result['error'] = log
                    elif step_data['assert_type'] == 'isVisible':
                        is_visible = element_obj.is_displayed()
                        step_result['success'] = is_visible
                        if not is_visible:
                            step_result['error'] = f"✗ 断言失败: 元素 '{element_name}' 不可见"
                    elif step_data['assert_type'] == 'exists':
                        # 元素已经找到，说明存在
                        step_result['success'] = True

            else:
                if step_data['action_type'] == 'wait':
                    time.sleep(step_data['wait_time'] / 1000)
                    step_result['success'] = True
                
                elif step_data['action_type'] == 'switchTab':
                    # Selenium 切换标签页逻辑
                    try:
                        # 获取当前所有窗口句柄
                        handles = driver.window_handles
                        
                        # 简单的策略：切换到最后一个窗口（通常是新打开的）
                        # 如果指定了索引，则切换到指定索引
                        target_index = -1
                        if step_data.get('input_value') and str(step_data['input_value']).isdigit():
                            target_index = int(step_data['input_value'])
                        
                        if target_index >= 0 and target_index < len(handles):
                            driver.switch_to.window(handles[target_index])
                        else:
                            driver.switch_to.window(handles[-1])
                        
                        step_result['success'] = True
                        print(f"✓ Selenium 切换标签页成功 (Handle Count: {len(handles)})")
                    except Exception as e:
                        step_result['error'] = f"切换标签页失败: {str(e)}"
                        step_result['success'] = False

        except TimeoutException as e:
            # 格式化为详细的错误信息，与selenium_engine.py保持一致
            execution_time = round(time.time() - start_time, 2)
            element_name = step_data['element'].get('name', '未知元素') if step_data.get('element') else '页面'
            locator_info = f"{step_data['element']['locator_strategy']}={step_data['element']['locator_value']}" if step_data.get('element') else '无'

            # 获取超时设置（从element或step）
            timeout_seconds = 10  # 默认值
            if step_data.get('element') and step_data['element'].get('wait_timeout'):
                timeout_seconds = step_data['element']['wait_timeout']
            elif step_data.get('wait_time'):
                timeout_seconds = step_data['wait_time'] / 1000
            
            # 提取TimeoutException的完整堆栈信息（类似Playwright的显示方式）
            error_parts = []
            
            # 1. 基本错误信息
            base_msg = str(e).strip()
            if base_msg and base_msg not in ['', 'Message:', 'Message: ', 'Message']:
                error_parts.append(base_msg)
            else:
                # 如果str(e)为空，说明是标准的超时异常
                error_parts.append(f"TimeoutException: 等待元素超时")
            
            # 2. 尝试从msg属性获取详细信息
            if hasattr(e, 'msg') and e.msg:
                msg_str = str(e.msg).strip()
                if msg_str and msg_str not in ['', 'Message:', 'Message: ', 'Message']:
                    if msg_str not in error_parts:
                        error_parts.append(msg_str)
            
            # 3. 从args获取
            if hasattr(e, 'args') and len(e.args) > 0 and e.args[0]:
                args_str = str(e.args[0]).strip()
                if args_str and args_str not in ['', 'Message:', 'Message: ', 'Message']:
                    if args_str not in error_parts:
                        error_parts.append(args_str)
            
            # 4. 如果有stacktrace，添加堆栈信息（类似Playwright的格式）
            if hasattr(e, 'stacktrace') and e.stacktrace:
                stacktrace_str = str(e.stacktrace).strip()
                if stacktrace_str:
                    error_parts.append(f"\nSelenium堆栈跟踪:\n{stacktrace_str}")
            
            # 4.5. 添加Python的traceback信息（这个总是可用的）
            try:
                import traceback
                tb_lines = traceback.format_tb(e.__traceback__)
                if tb_lines:
                    # 只取最后2层堆栈（最相关的部分）
                    relevant_tb = tb_lines[-2:] if len(tb_lines) >= 2 else tb_lines
                    tb_str = ''.join(relevant_tb).strip()
                    if tb_str:
                        # 提取等待条件信息（从堆栈中）
                        wait_condition = "未知条件"
                        if 'EC.visibility_of_element_located' in tb_str:
                            wait_condition = "等待元素可见 (visibility_of_element_located)"
                        elif 'EC.element_to_be_clickable' in tb_str:
                            wait_condition = "等待元素可点击 (element_to_be_clickable)"
                        elif 'EC.presence_of_element_located' in tb_str:
                            wait_condition = "等待元素存在 (presence_of_element_located)"
                        
                        error_parts.append(f"\n等待条件: {wait_condition}")
                        error_parts.append(f"\n调用堆栈:\n{tb_str}")
            except Exception:
                pass
            
            # 5. 如果仍然没有有用信息，提供操作类型相关的提示
            if len(error_parts) == 0 or (len(error_parts) == 1 and 'TimeoutException' in error_parts[0]):
                # 添加操作相关的上下文
                action_type_str = step_data.get('action_type') if isinstance(step_data, dict) else None
                if action_type_str == 'click':
                    error_parts.append(f"等待元素可点击失败（超时{timeout_seconds}秒）")
                elif action_type_str == 'fill':
                    error_parts.append(f"等待输入框可用失败（超时{timeout_seconds}秒）")
                elif action_type_str == 'waitFor':
                    error_parts.append(f"等待元素出现失败（超时{timeout_seconds}秒）")
            
            # 合并所有错误信息
            error_msg = '\n'.join(error_parts)

            log = f"✗ 操作超时\n"
            log += f"  - 元素: '{element_name}'\n"
            log += f"  - 定位器: {locator_info}\n"
            log += f"  - 超时设置: {timeout_seconds}秒\n"
            log += f"  - 实际用时: {execution_time}秒\n"
            log += f"  - 错误详情: {error_msg}"
            step_result['error'] = log

        except Exception as e:
            # 格式化为详细的错误信息，与selenium_engine.py保持一致
            execution_time = round(time.time() - start_time, 2)
            element_name = step_data['element'].get('name', '未知元素') if step_data.get('element') else '页面'
            locator_info = f"{step_data['element']['locator_strategy']}={step_data['element']['locator_value']}" if step_data.get('element') else '无'

            # 提取详细的错误信息（改进版 - 添加调试日志）
            error_type = type(e).__name__
            error_msg = ""

            # 🔍 调试：打印异常对象的所有信息
            print(f"=" * 60)
            print(f"🔍 Selenium 异常调试信息 (test_executor):")
            print(f"  异常类型: {error_type}")
            print(f"  str(e): {repr(str(e))}")
            print(f"  hasattr msg: {hasattr(e, 'msg')}")
            if hasattr(e, 'msg'):
                print(f"  e.msg 值: {repr(e.msg)}")
                print(f"  e.msg 类型: {type(e.msg)}")
            print(f"  hasattr args: {hasattr(e, 'args')}")
            if hasattr(e, 'args'):
                print(f"  e.args 长度: {len(e.args)}")
                print(f"  e.args 内容: {e.args}")
            print(f"  hasattr stacktrace: {hasattr(e, 'stacktrace')}")
            if hasattr(e, 'stacktrace'):
                print(f"  e.stacktrace 前200字符: {str(e.stacktrace)[:200]}")
            print(f"  dir(e): {[attr for attr in dir(e) if not attr.startswith('_')]}")
            print(f"=" * 60)

            # 定义无意义的错误信息列表
            meaningless_messages = ['', 'Message', 'Message:', 'Message: ', 'Message:\n']

            # 尝试提取更详细的 Selenium 异常信息（使用优先级策略）
            try:
                # 优先级1: 从 msg 属性获取（Selenium 异常的主要信息源）
                if hasattr(e, 'msg') and e.msg:
                    temp = str(e.msg).strip()
                    if temp not in meaningless_messages:
                        error_msg = temp
                        print(f"✓ 从 e.msg 提取到错误: {error_msg[:100]}")

                # 优先级2: 从 args 获取
                if not error_msg and hasattr(e, 'args') and len(e.args) > 0 and e.args[0]:
                    temp = str(e.args[0]).strip()
                    if temp not in meaningless_messages:
                        error_msg = temp
                        print(f"✓ 从 e.args[0] 提取到错误: {error_msg[:100]}")

                # 优先级3: 使用 str(e)，但排除无意义的值
                if not error_msg:
                    temp = str(e).strip()
                    if temp not in meaningless_messages:
                        error_msg = temp
                        print(f"✓ 从 str(e) 提取到错误: {error_msg[:100]}")

                # 优先级4: 从 stacktrace 提取
                if not error_msg and hasattr(e, 'stacktrace') and e.stacktrace:
                    error_msg = f"详细堆栈:\n{e.stacktrace[:300]}"
                    print(f"✓ 从 e.stacktrace 提取到错误")

                # 优先级5: 从 __dict__ 提取有用信息
                if not error_msg and hasattr(e, '__dict__'):
                    useful_attrs = {k: v for k, v in e.__dict__.items()
                                   if v is not None and not k.startswith('_') and k not in ['msg', 'args', 'stacktrace']}
                    if useful_attrs:
                        error_msg = f"异常属性: {useful_attrs}"
                        print(f"✓ 从 e.__dict__ 提取到错误")

                # 如果还是没有，使用默认信息
                if not error_msg:
                    error_msg = f"未知错误 (异常类型: {error_type})"
                    print(f"⚠️ 无法提取任何有用信息，使用默认错误消息")

            except Exception as extract_error:
                print(f"⚠️  提取错误信息时出错: {extract_error}")
                error_msg = f"无法提取详细错误信息 (异常类型: {error_type})"

            # 添加异常类型前缀（如果还没有）
            if error_type not in error_msg and error_type != 'Exception':
                error_msg = f"{error_type}: {error_msg}"

            log = f"✗ 执行失败\n"
            log += f"  - 元素: '{element_name}'\n"
            log += f"  - 定位器: {locator_info}\n"
            log += f"  - 执行时间: {execution_time}秒\n"
            log += f"  - 错误: {error_msg}"
            step_result['error'] = log

            # 打印详细日志便于调试
            print(f"❌ Selenium 步骤执行失败:")
            print(f"   异常类型: {error_type}")
            print(f"   错误信息: {error_msg[:500]}")  # 限制长度避免刷屏

        return step_result


