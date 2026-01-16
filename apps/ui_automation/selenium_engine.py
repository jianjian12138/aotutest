"""
Selenium自动化测试执行引擎
用于驱动真实浏览器执行UI自动化测试
"""
import base64
import time
from .variable_resolver import resolve_variables
import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException
import logging

logger = logging.getLogger(__name__)


class SeleniumTestEngine:
    """Selenium测试执行引擎"""

    def __init__(self, browser_type='chrome', headless=True):
        """
        初始化测试引擎

        Args:
            browser_type: 浏览器类型 (chrome, firefox, safari, edge)
            headless: 是否无头模式
        """
        self.browser_type = browser_type
        self.headless = headless
        self.driver = None

    @staticmethod
    def check_browser_available(browser_type='chrome'):
        """
        检查浏览器是否可用

        Args:
            browser_type: 浏览器类型

        Returns:
            (是否可用, 错误信息)
        """
        try:
            if browser_type == 'chrome':
                # 检查 Chrome 浏览器是否安装
                chrome_paths = [
                    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',  # macOS
                    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',  # Windows
                    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',  # Windows 32-bit
                    '/usr/bin/google-chrome',  # Linux
                    '/usr/bin/chromium-browser',  # Linux (Chromium)
                ]
                if not any(os.path.exists(path) for path in chrome_paths):
                    return False, "Chrome 浏览器未安装。请先安装 Google Chrome 浏览器。"
                return True, None

            elif browser_type == 'firefox':
                # 检查 Firefox 浏览器是否安装
                firefox_paths = [
                    '/Applications/Firefox.app/Contents/MacOS/firefox',  # macOS
                    'C:\\Program Files\\Mozilla Firefox\\firefox.exe',  # Windows
                    'C:\\Program Files (x86)\\Mozilla Firefox\\firefox.exe',  # Windows 32-bit
                    '/usr/bin/firefox',  # Linux
                ]
                if not any(os.path.exists(path) for path in firefox_paths):
                    return False, "Firefox 浏览器未安装。请先安装 Mozilla Firefox 浏览器。"
                return True, None

            elif browser_type == 'edge':
                # 检查 Edge 浏览器是否安装
                edge_paths = [
                    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',  # macOS
                    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',  # Windows
                    'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',  # Windows
                ]
                if not any(os.path.exists(path) for path in edge_paths):
                    return False, "Edge 浏览器未安装。请先安装 Microsoft Edge 浏览器。"
                return True, None

            elif browser_type == 'safari':
                # Safari 只在 macOS 上可用
                import platform
                if platform.system() != 'Darwin':
                    return False, "Safari 浏览器不可用。Safari 仅在 macOS 系统上可用。"

                # 检查 safaridriver 是否存在
                safaridriver_path = '/usr/bin/safaridriver'
                if not os.path.exists(safaridriver_path):
                    return False, "Safari WebDriver 不可用。请在终端执行: sudo safaridriver --enable"

                # Safari 需要手动启用远程自动化
                # 这个只能在实际启动时检查，这里给出提示
                return True, "请确保已在 Safari 设置 -> 高级 -> 显示开发菜单中启用，并在开发菜单中勾选'允许远程自动化'"

            else:
                return True, None  # 未知浏览器类型，跳过检查

        except Exception as e:
            logger.error(f"检查浏览器可用性时出错: {str(e)}")
            return True, None  # 检查出错时跳过，让实际启动时处理

    def start(self):
        """启动浏览器"""
        try:
            import os
            # 配置webdriver_manager使用本地缓存，避免每次下载
            os.environ['WDM_LOG_LEVEL'] = '0'  # 减少日志输出
            os.environ['WDM_PRINT_FIRST_LINE'] = 'False'  # 不打印首行信息
            
            # 先检查浏览器是否可用
            is_available, error_msg = self.check_browser_available(self.browser_type)
            if not is_available:
                logger.error(f"浏览器不可用: {error_msg}")
                # 提供安装建议
                install_tips = {
                    'chrome': 'brew install --cask google-chrome',
                    'firefox': 'brew install --cask firefox',
                    'edge': 'brew install --cask microsoft-edge',
                }
                tip = install_tips.get(self.browser_type, '')
                full_error = f"{error_msg}\n\n💡 安装命令（macOS）：{tip}" if tip else error_msg
                raise Exception(full_error)
            if self.browser_type == 'chrome':
                from selenium.webdriver.chrome.options import Options
                from selenium.webdriver.chrome.service import Service
                from webdriver_manager.chrome import ChromeDriverManager

                options = Options()
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
                    'password_manager_leak_detection': False,  # 禁用密码泄露检测（prefs级别）
                    'safebrowsing.enabled': False,  # 禁用安全浏览（可能触发密码警告）
                }
                options.add_experimental_option('prefs', prefs)
                
                # 禁用密码泄露检查和其他安全警告（更全面的设置）
                options.add_argument('--disable-features=PasswordLeakDetection')  # 禁用密码泄露检测
                options.add_argument('--disable-features=PrivacySandboxSettings4')  # 禁用隐私沙盒
                options.add_argument('--disable-features=TranslateUI')  # 禁用翻译提示
                options.add_argument('--disable-infobars')  # 禁用信息栏
                options.add_argument('--disable-save-password-bubble')  # 禁用保存密码气泡
                options.add_argument('--disable-password-generation')  # 禁用密码生成
                options.add_argument('--disable-password-manager-reauthentication')  # 禁用密码管理器重新认证
                
                # 额外的安全警告抑制
                options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
                options.add_argument('--disable-popup-blocking')  # 禁用弹窗拦截（避免某些警告）
                options.add_argument('--disable-notifications')  # 禁用所有通知

                # 使用缓存优先策略
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)

            elif self.browser_type == 'firefox':
                from selenium.webdriver.firefox.options import Options
                from selenium.webdriver.firefox.service import Service
                from webdriver_manager.firefox import GeckoDriverManager

                options = Options()
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
                service = Service(GeckoDriverManager().install())
                self.driver = webdriver.Firefox(service=service, options=options)

            elif self.browser_type == 'edge':
                from selenium.webdriver.edge.options import Options
                from selenium.webdriver.edge.service import Service
                from webdriver_manager.microsoft import EdgeChromiumDriverManager

                options = Options()
                if self.headless:
                    options.add_argument('--headless')
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_argument('--window-size=1920,1080')

                # 使用缓存优先策略，7天内不重新下载
                service = Service(EdgeChromiumDriverManager().install())
                self.driver = webdriver.Edge(service=service, options=options)

            elif self.browser_type == 'safari':
                # Safari 不支持 headless 模式
                # 需要先启用：sudo safaridriver --enable
                # 并在 Safari 设置 -> 开发菜单中启用"允许远程自动化"
                try:
                    self.driver = webdriver.Safari()
                    self.driver.set_window_size(1920, 1080)
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

            else:
                # 默认使用Chrome
                from selenium.webdriver.chrome.options import Options
                from selenium.webdriver.chrome.service import Service
                from webdriver_manager.chrome import ChromeDriverManager

                options = Options()
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

                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)

            # 设置隐式等待
            self.driver.implicitly_wait(3)

            logger.info(f"浏览器启动成功: {self.browser_type}, headless={self.headless}")

        except Exception as e:
            logger.error(f"启动浏览器失败: {str(e)}")
            raise

    def stop(self):
        """关闭浏览器"""
        try:
            if self.driver:
                self.driver.quit()
            logger.info("浏览器已关闭")
        except Exception as e:
            logger.error(f"关闭浏览器失败: {str(e)}")

    def _get_locator(self, locator_strategy: str, locator_value: str) -> Tuple[str, str]:
        """
        转换定位策略为Selenium的By类型

        Args:
            locator_strategy: 定位策略名称
            locator_value: 定位值

        Returns:
            (By类型, 定位值)
        """
        strategy_map = {
            'id': By.ID,
            'css': By.CSS_SELECTOR,
            'css selector': By.CSS_SELECTOR,
            'xpath': By.XPATH,
            'name': By.NAME,
            'class': By.CLASS_NAME,
            'class name': By.CLASS_NAME,
            'tag': By.TAG_NAME,
            'tag name': By.TAG_NAME,
            'link text': By.LINK_TEXT,
            'partial link text': By.PARTIAL_LINK_TEXT
        }

        by_type = strategy_map.get(locator_strategy.lower(), By.CSS_SELECTOR)

        # 处理特殊情况
        if locator_strategy.lower() == 'text':
            # Selenium不支持直接的text定位，转换为XPath
            return By.XPATH, f"//*[contains(text(), '{locator_value}')]"
            
        elif locator_strategy.lower() == 'id' and not locator_value.startswith('#'):
            # ID定位直接使用值
            return by_type, locator_value
            
        elif locator_strategy.lower() == 'css' and locator_value.startswith('#'):
            # CSS选择器
            return by_type, locator_value
            
        # 自动检测XPath (如果策略不是xpath但值看起来像xpath)
        if locator_strategy.lower() not in ['xpath'] and (locator_value.startswith('//') or locator_value.startswith('(') or locator_value.startswith('xpath=')):
            if locator_value.startswith('xpath='):
                locator_value = locator_value[6:]
            return By.XPATH, locator_value

        return by_type, locator_value

    def execute_step(self, step, element_data: Dict) -> Tuple[bool, str, Optional[str]]:
        """
        执行单个测试步骤

        Args:
            step: 测试步骤对象
            element_data: 元素数据字典 {locator_strategy, locator_value, name}

        Returns:
            (是否成功, 日志信息, 截图base64)
        """
        print(f"\n🔵 开始执行步骤: action_type={step.action_type}")
        action_type = step.action_type
        
        # 预先解析变量
        resolved_input_value = step.input_value
        if step.input_value:
            resolved_input_value = resolve_variables(step.input_value)
            
        resolved_assert_value = step.assert_value
        if step.assert_value:
            resolved_assert_value = resolve_variables(step.assert_value)
            
        start_time = time.time()
        screenshot_base64 = None

        try:
            # wait和screenshot操作不需要元素定位器
            if action_type == 'wait':
                wait_seconds = step.wait_time / 1000 if step.wait_time else 1
                time.sleep(wait_seconds)
                execution_time = round(time.time() - start_time, 2)
                log = f"✓ 固定等待 {wait_seconds} 秒完成 - 耗时 {execution_time}秒"
                return True, log, None

            elif action_type == 'screenshot':
                screenshot = self.driver.get_screenshot_as_png()
                screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                execution_time = round(time.time() - start_time, 2)
                log = f"✓ 截图成功\n"
                log += f"  - 截图范围: 整个页面\n"
                log += f"  - 执行时间: {execution_time}秒"
                return True, log, screenshot_base64

            elif action_type == 'switchTab':
                # 切换标签页
                # 获取超时时间
                if step.wait_time:
                    timeout = step.wait_time / 1000
                else:
                    timeout = 5.0
                
                start_wait = time.time()
                current_handle = self.driver.current_window_handle
                target_index = -1
                
                while True:
                    handles = self.driver.window_handles
                    target_index = -1  # 默认切换到最新标签页
                    should_switch = False
                    
                    if resolved_input_value and str(resolved_input_value).isdigit():
                        # 指定索引的情况
                        idx = int(resolved_input_value)
                        if 0 <= idx < len(handles):
                            target_index = idx
                            should_switch = True
                    else:
                        # 切换到最新的情况
                        target_index = -1
                        # 如果最新的句柄不是当前句柄，说明有新标签页，或者是切换到其他已存在的标签页
                        if handles[-1] != current_handle:
                            should_switch = True
                        # 如果只有一个标签页，且就是当前页，可能是在等待新标签页打开
                        elif len(handles) == 1 and handles[0] == current_handle:
                            should_switch = False
                        # 如果有多个标签页，但最新的就是当前页，可能是想留在当前页，也可能是等待更新的
                        # 这里我们假设用户调用 switchTab 是为了改变，所以如果相同则等待
                        else:
                            should_switch = False

                    if should_switch:
                        break
                    
                    if time.time() - start_wait > timeout:
                        # 超时了，就切换到当前能找到的那个（Best Effort）
                        break
                        
                    time.sleep(0.5)
                
                # 执行切换
                if target_index == -1:
                    self.driver.switch_to.window(handles[-1])
                    final_target_index = len(handles) - 1
                else:
                    self.driver.switch_to.window(handles[target_index])
                    final_target_index = target_index

                execution_time = round(time.time() - start_time, 2)
                log = f"✓ 切换标签页成功\n"
                log += f"  - 目标索引: {final_target_index}\n"
                log += f"  - 当前标题: {self.driver.title}\n"
                log += f"  - 执行时间: {execution_time}秒"
                return True, log, None

            # 其他操作需要元素定位器
            locator_strategy = element_data.get('locator_strategy', 'css')
            locator_value = element_data.get('locator_value', '')
            element_name = element_data.get('name', '未知元素')

            # 获取强制操作选项
            force_action = element_data.get('force_action', False)

            # 计算超时时间
            element_wait_timeout = element_data.get('wait_timeout')
            if element_wait_timeout is not None and element_wait_timeout > 0:
                timeout_seconds = element_wait_timeout
            elif step.wait_time:
                timeout_seconds = step.wait_time / 1000
            else:
                timeout_seconds = 5

            # 获取定位器
            by_type, by_value = self._get_locator(locator_strategy, locator_value)

            # 根据操作类型选择合适的等待条件
            wait = WebDriverWait(self.driver, timeout_seconds)
            from selenium.common.exceptions import StaleElementReferenceException
            
            if action_type == 'click':
                # 点击操作：等待元素可点击（解决 stale element 问题）
                # 对于下拉框选项，需要等待可见性，且必须找到可见的那个（因为可能有多个同名元素，有的隐藏有的显示）
                if 'dropdown' in by_value.lower() or 'el-select' in by_value.lower() or '下拉' in element_name or '选项' in element_name:
                    logger.info(f"检测到下拉框选项，查找可见元素...")
                    
                    def find_visible_element(driver):
                        elements = driver.find_elements(by_type, by_value)
                        for elem in elements:
                            if elem.is_displayed():
                                return elem
                        return False
                    
                    element = wait.until(find_visible_element)
                else:
                    element = wait.until(EC.element_to_be_clickable((by_type, by_value)))
            else:
                # 其他操作：等待元素出现
                element = wait.until(EC.presence_of_element_located((by_type, by_value)))

            # 执行操作（添加 stale element 重试机制）
            execution_time = 0
            max_retries = 3

            if action_type == 'click':
                for attempt in range(max_retries):
                    try:
                        # 如果启用强制操作或元素不可见，使用JavaScript点击
                        if force_action or not element.is_displayed():
                            self.driver.execute_script("arguments[0].click();", element)
                            execution_time = round(time.time() - start_time, 2)
                            log = f"✓ 点击元素 '{element_name}' 成功（使用JavaScript）\n"
                            log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                            log += f"  - 超时设置: {timeout_seconds}秒\n"
                            if force_action:
                                log += f"  - 强制操作: 是（使用JavaScript点击）\n"
                            log += f"  - 执行时间: {execution_time}秒"
                        else:
                            # 对于下拉框选项，滚动到中心位置
                            if 'dropdown' in by_value.lower() or 'el-select' in by_value.lower() or '下拉' in element_name or '选项' in element_name:
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                            else:
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                            time.sleep(0.3)  # 等待滚动完成
                            element.click()
                            execution_time = round(time.time() - start_time, 2)
                            log = f"✓ 点击元素 '{element_name}' 成功\n"
                            log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                            log += f"  - 超时设置: {timeout_seconds}秒\n"
                            log += f"  - 执行时间: {execution_time}秒"
                        return True, log, None
                    except StaleElementReferenceException:
                        if attempt < max_retries - 1:
                            # 重新定位元素
                            logger.warning(f"⚠️ 元素过期（Stale Element），正在重试... (尝试 {attempt + 2}/{max_retries})")
                            # 增加等待时间，让页面 DOM 稳定（对于 Vue/React 应用很重要）
                            wait_time = 1.0 if attempt == 0 else 1.5  # 第一次重试等1秒，第二次重试等1.5秒
                            logger.info(f"等待 {wait_time}秒 让页面稳定...")
                            time.sleep(wait_time)

                            # 根据类型重新定位
                            if 'dropdown' in by_value.lower() or 'el-select' in by_value.lower():
                                def find_visible_element(driver):
                                    elements = driver.find_elements(by_type, by_value)
                                    for elem in elements:
                                        if elem.is_displayed():
                                            return elem
                                    return False
                                element = wait.until(find_visible_element)
                            else:
                                element = wait.until(EC.element_to_be_clickable((by_type, by_value)))

                            # 等待元素状态稳定（确保 DOM 不再变化）
                            time.sleep(0.3)
                            logger.info(f"✓ 元素重新定位成功: '{element_name}'")
                        else:
                            raise
                    except Exception as click_error:
                        # 如果点击失败且是下拉框选项，尝试使用 JavaScript 点击
                        if attempt < max_retries - 1 and ('not visible' in str(click_error).lower() or 'not interactable' in str(click_error).lower()):
                            logger.warning(f"元素不可交互，尝试使用 JavaScript 点击... ({attempt + 1}/{max_retries})")
                            try:
                                self.driver.execute_script("arguments[0].click();", element)
                                execution_time = round(time.time() - start_time, 2)
                                log = f"✓ 点击元素 '{element_name}' 成功（使用JavaScript）\n"
                                log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                                log += f"  - 超时设置: {timeout_seconds}秒\n"
                                log += f"  - 执行时间: {execution_time}秒"
                                return True, log, None
                            except:
                                if attempt < max_retries - 1:
                                    time.sleep(0.5)
                                    if 'dropdown' in by_value.lower() or 'el-select' in by_value.lower():
                                        element = wait.until(EC.visibility_of_element_located((by_type, by_value)))
                                    else:
                                        element = wait.until(EC.element_to_be_clickable((by_type, by_value)))
                                else:
                                    raise
                        else:
                            raise

            elif action_type == 'fill':
                # 清空并输入文本（添加 stale element 重试）
                from selenium.common.exceptions import StaleElementReferenceException
                for attempt in range(max_retries):
                    try:
                        if force_action or not element.is_displayed():
                            # 使用JavaScript设置值
                            self.driver.execute_script(f"arguments[0].value = '{resolved_input_value}';", element)
                            # 触发input和change事件
                            self.driver.execute_script("""
                                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                            """, element)
                            execution_time = round(time.time() - start_time, 2)
                            log = f"✓ 在元素 '{element_name}' 中输入文本成功（使用JavaScript）\n"
                            log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                            if resolved_input_value != step.input_value:
                                log += f"  - 变量解析: '{step.input_value}' => '{resolved_input_value}'\n"
                            log += f"  - 输入内容: '{resolved_input_value}'\n"
                            log += f"  - 超时设置: {timeout_seconds}秒\n"
                            if force_action:
                                log += f"  - 强制操作: 是（使用JavaScript输入）\n"
                            log += f"  - 执行时间: {execution_time}秒"
                        else:
                            element.clear()
                            element.send_keys(resolved_input_value)
                            execution_time = round(time.time() - start_time, 2)
                            log = f"✓ 在元素 '{element_name}' 中输入文本成功\n"
                            log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                            if resolved_input_value != step.input_value:
                                log += f"  - 变量解析: '{step.input_value}' => '{resolved_input_value}'\n"
                            log += f"  - 输入内容: '{resolved_input_value}'\n"
                            log += f"  - 超时设置: {timeout_seconds}秒\n"
                            log += f"  - 执行时间: {execution_time}秒"

                        # 输入成功后短暂等待，确保表单验证生效
                        # 特别是在服务器环境下，需要给Vue/React等框架时间处理
                        time.sleep(0.3)

                        return True, log, None
                    except StaleElementReferenceException:
                        if attempt < max_retries - 1:
                            logger.warning(f"⚠️ 元素过期（Stale Element），正在重试... (尝试 {attempt + 2}/{max_retries})")
                            # 增加等待时间，让页面 DOM 稳定
                            wait_time = 1.0 if attempt == 0 else 1.5
                            logger.info(f"等待 {wait_time}秒 让页面稳定...")
                            time.sleep(wait_time)
                            element = wait.until(EC.presence_of_element_located((by_type, by_value)))
                            time.sleep(0.3)  # 确保元素状态稳定
                            logger.info(f"✓ 元素重新定位成功")
                        else:
                            raise

            elif action_type == 'getText':
                # 获取文本（添加 stale element 重试）
                from selenium.common.exceptions import StaleElementReferenceException
                for attempt in range(max_retries):
                    try:
                        text = element.text
                        execution_time = round(time.time() - start_time, 2)
                        log = f"✓ 获取元素 '{element_name}' 的文本成功\n"
                        log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                        log += f"  - 文本内容: '{text}'\n"
                        log += f"  - 超时设置: {timeout_seconds}秒\n"
                        log += f"  - 执行时间: {execution_time}秒"
                        return True, log, None
                    except StaleElementReferenceException:
                        if attempt < max_retries - 1:
                            logger.warning(f"⚠️ 元素过期（Stale Element），正在重试... (尝试 {attempt + 2}/{max_retries})")
                            # 增加等待时间，让页面 DOM 稳定
                            wait_time = 1.0 if attempt == 0 else 1.5
                            logger.info(f"等待 {wait_time}秒 让页面稳定...")
                            time.sleep(wait_time)
                            element = wait.until(EC.presence_of_element_located((by_type, by_value)))
                            time.sleep(0.3)  # 确保元素状态稳定
                            logger.info(f"✓ 元素重新定位成功")
                        else:
                            raise

            elif action_type == 'waitFor':
                # 等待元素可见
                wait.until(EC.visibility_of_element_located((by_type, by_value)))
                execution_time = round(time.time() - start_time, 2)
                log = f"✓ 等待元素 '{element_name}' 出现成功\n"
                log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                log += f"  - 超时设置: {timeout_seconds}秒\n"
                log += f"  - 等待时间: {execution_time}秒"
                return True, log, None

            elif action_type == 'hover':
                # 悬停操作
                if force_action or not element.is_displayed():
                    # 使用JavaScript模拟悬停
                    self.driver.execute_script("""
                        var event = new MouseEvent('mouseover', {
                            'view': window,
                            'bubbles': true,
                            'cancelable': true
                        });
                        arguments[0].dispatchEvent(event);
                    """, element)
                    execution_time = round(time.time() - start_time, 2)
                    log = f"✓ 在元素 '{element_name}' 上悬停成功（使用JavaScript）\n"
                    log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                    log += f"  - 超时设置: {timeout_seconds}秒\n"
                    if force_action:
                        log += f"  - 强制操作: 是（使用JavaScript悬停）\n"
                    log += f"  - 执行时间: {execution_time}秒"
                else:
                    actions = ActionChains(self.driver)
                    actions.move_to_element(element).perform()
                    execution_time = round(time.time() - start_time, 2)
                    log = f"✓ 在元素 '{element_name}' 上悬停成功\n"
                    log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                    log += f"  - 超时设置: {timeout_seconds}秒\n"
                    log += f"  - 执行时间: {execution_time}秒"
                return True, log, None

            elif action_type == 'scroll':
                # 滚动到元素
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(0.3)  # 等待滚动完成
                execution_time = round(time.time() - start_time, 2)
                log = f"✓ 滚动到元素 '{element_name}' 成功\n"
                log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                log += f"  - 超时设置: {timeout_seconds}秒\n"
                log += f"  - 执行时间: {execution_time}秒"
                return True, log, None

            elif action_type == 'assert':
                # 根据断言类型执行不同的断言
                if step.assert_type == 'textContains':
                    text = element.text
                    if resolved_assert_value in text:
                        log = f"✓ 断言通过: 文本包含 '{resolved_assert_value}'\n"
                        if resolved_assert_value != step.assert_value:
                                log += f"  - 变量解析: '{step.assert_value}' => '{resolved_assert_value}'\n"
                        log += f"  - 实际文本: '{text}'\n"
                        log += f"  - 超时设置: {timeout_seconds}秒"
                        return True, log, None
                    else:
                        log = f"✗ 断言失败: 文本不包含 '{resolved_assert_value}'\n"
                        if resolved_assert_value != step.assert_value:
                                log += f"  - 变量解析: '{step.assert_value}' => '{resolved_assert_value}'\n"
                        log += f"  - 实际文本: '{text}'"
                        screenshot = self.driver.get_screenshot_as_png()
                        screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                        return False, log, screenshot_base64

                elif step.assert_type == 'textEquals':
                    text = element.text
                    if text == resolved_assert_value:
                        log = f"✓ 断言通过: 文本等于 '{resolved_assert_value}'\n"
                        if resolved_assert_value != step.assert_value:
                                log += f"  - 变量解析: '{step.assert_value}' => '{resolved_assert_value}'\n"
                        log += f"  - 超时设置: {timeout_seconds}秒"
                        return True, log, None
                    else:
                        log = f"✗ 断言失败: 文本不等于 '{resolved_assert_value}'\n"
                        if resolved_assert_value != step.assert_value:
                                log += f"  - 变量解析: '{step.assert_value}' => '{resolved_assert_value}'\n"
                        log += f"  - 期望: '{resolved_assert_value}'\n"
                        log += f"  - 实际: '{text}'"
                        screenshot = self.driver.get_screenshot_as_png()
                        screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                        return False, log, screenshot_base64

                elif step.assert_type == 'isVisible':
                    is_visible = element.is_displayed()
                    if is_visible:
                        log = f"✓ 断言通过: 元素 '{element_name}' 可见"
                        return True, log, None
                    else:
                        log = f"✗ 断言失败: 元素 '{element_name}' 不可见"
                        screenshot = self.driver.get_screenshot_as_png()
                        screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                        return False, log, screenshot_base64

                elif step.assert_type == 'exists':
                    # 元素已经找到，说明存在
                    log = f"✓ 断言通过: 元素 '{element_name}' 存在"
                    return True, log, None



            else:
                log = f"⚠ 未知的操作类型: {action_type}"
                return True, log, None

        except TimeoutException as e:
            execution_time = round(time.time() - start_time, 2)
            
            # 🔍 调试：打印TimeoutException的所有属性
            print(f"\n" + "=" * 60)
            print(f"🔍 Selenium TimeoutException 调试信息:")
            print(f"  type(e): {type(e)}")
            print(f"  str(e): {repr(str(e))}")
            print(f"  repr(e): {repr(e)}")
            print(f"  hasattr msg: {hasattr(e, 'msg')}")
            if hasattr(e, 'msg'):
                print(f"    e.msg = {repr(e.msg)}")
            print(f"  hasattr args: {hasattr(e, 'args')}")
            if hasattr(e, 'args'):
                print(f"    e.args = {e.args}")
            print(f"  hasattr stacktrace: {hasattr(e, 'stacktrace')}")
            if hasattr(e, 'stacktrace'):
                print(f"    e.stacktrace = {repr(e.stacktrace)[:200]}")
            print(f"  hasattr screen: {hasattr(e, 'screen')}")
            if hasattr(e, 'screen'):
                print(f"    e.screen = {type(e.screen)}")
            print(f"  e.__dict__ = {e.__dict__}")
            print(f"  dir(e) = {[attr for attr in dir(e) if not attr.startswith('_')]}")
            
            # 尝试获取Python的traceback信息
            import traceback
            tb_str = ''.join(traceback.format_tb(e.__traceback__))
            print(f"  Python traceback:\n{tb_str}")
            print(f"=" * 60 + "\n")
            
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
            except:
                pass
            
            # 5. 如果仍然没有有用信息，提供操作类型相关的提示
            if len(error_parts) == 0 or (len(error_parts) == 1 and 'TimeoutException' in error_parts[0]):
                # 添加操作相关的上下文
                if action_type == 'click':
                    error_parts.append(f"等待元素可点击失败（超时{timeout_seconds}秒）")
                elif action_type == 'fill':
                    error_parts.append(f"等待输入框可用失败（超时{timeout_seconds}秒）")
                elif action_type == 'waitFor':
                    error_parts.append(f"等待元素出现失败（超时{timeout_seconds}秒）")
            
            # 合并所有错误信息
            error_msg = '\n'.join(error_parts)
            
            log = f"✗ 操作超时\n"
            log += f"  - 元素: '{element_name}'\n"
            log += f"  - 定位器: {locator_strategy}={locator_value}\n"
            log += f"  - 超时设置: {timeout_seconds}秒\n"
            log += f"  - 实际用时: {execution_time}秒\n"
            log += f"  - 错误详情: {error_msg}"

            # 捕获失败截图
            screenshot_base64 = None
            try:
                screenshot = self.driver.get_screenshot_as_png()
                screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
            except:
                pass

            return False, log, screenshot_base64

        except Exception as e:
            print(f"\n🚨🚨🚨 捕获到 Selenium 异常！开始调试... 🚨🚨🚨\n")
            execution_time = round(time.time() - start_time, 2)

            # 提取详细的错误信息（改进版 - 添加调试日志）
            error_type = type(e).__name__
            error_msg = ""

            # 🔍 调试：打印异常对象的所有信息（使用 print 确保一定输出到控制台）
            print(f"\n" + "=" * 60)
            print(f"🔍 Selenium 异常调试信息 (selenium_engine.py):")
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
            if hasattr(e, 'stacktrace') and e.stacktrace:
                print(f"  e.stacktrace 前200字符: {str(e.stacktrace)[:200]}")
            print(f"  dir(e): {[attr for attr in dir(e) if not attr.startswith('_')]}")
            print(f"=" * 60 + "\n")

            # 定义无意义的错误信息列表
            meaningless_messages = ['', 'Message', 'Message:', 'Message: ', 'Message:\n']

            # 尝试提取更详细的 Selenium 异常信息
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
                print(f"⚠️ 提取错误信息时出错: {extract_error}")
                error_msg = f"无法提取详细错误信息 (异常类型: {error_type})"

            # 添加异常类型前缀（如果还没有）
            if error_type not in error_msg and error_type != 'Exception':
                error_msg = f"{error_type}: {error_msg}"

            log = f"✗ 执行失败\n"
            log += f"  - 元素: '{element_name}'\n"
            log += f"  - 定位器: {locator_strategy}={locator_value}\n"
            log += f"  - 执行时间: {execution_time}秒\n"
            log += f"  - 错误: {error_msg}"

            # 打印详细日志便于调试
            logger.error(f"Selenium 步骤执行失败:")
            logger.error(f"  异常类型: {error_type}")
            logger.error(f"  错误信息: {error_msg[:500]}")

            # 捕获失败截图
            screenshot_base64 = None
            try:
                screenshot = self.driver.get_screenshot_as_png()
                screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
            except:
                pass

            return False, log, screenshot_base64

    def navigate(self, url: str) -> Tuple[bool, str]:
        """
        导航到指定URL

        Args:
            url: 目标URL

        Returns:
            (是否成功, 日志信息)
        """
        try:
            self.driver.get(url)

            # 等待页面基本加载完成
            # 在服务器环境（特别是无头模式）需要更长的等待时间
            import platform
            is_linux = platform.system() == 'Linux'

            # 等待 document.readyState 为 complete
            try:
                WebDriverWait(self.driver, 15 if is_linux else 10).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
            except:
                # 即使超时也继续执行
                pass

            # 额外等待，确保动态内容加载（Vue/React等SPA应用）
            # 服务器无头模式需要更长的等待时间
            extra_wait = 3 if is_linux else 2
            time.sleep(extra_wait)

            log = f"✓ 成功导航到: {url}\n"
            log += f"  - 等待页面加载完成（基础等待+额外{extra_wait}秒）"
            return True, log
        except Exception as e:
            log = f"✗ 导航失败: {url}\n  - 错误: {str(e)}"
            return False, log

    def capture_screenshot(self) -> str:
        """
        捕获当前页面截图

        Returns:
            截图的base64字符串
        """
        try:
            screenshot = self.driver.get_screenshot_as_png()
            return f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
        except Exception as e:
            logger.error(f"捕获截图失败: {str(e)}")
            return None
