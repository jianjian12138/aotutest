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




class PlaywrightRunnerMixin:
    def run_with_playwright(self):
        """使用 Playwright 执行测试（同步版本）"""
        start_time = time.time()
        passed = 0
        failed = 0
        skipped = 0
        
        # 检查 Playwright 是否可用
        try:
            from playwright.sync_api import sync_playwright as test_import
        except ImportError as e:
            error_msg = (
                "Playwright 模块未正确安装或 Django 服务器未在虚拟环境中运行。\n\n"
                "请确保：\n"
                "1. 已在虚拟环境中安装: pip install playwright\n"
                "2. 已安装浏览器: playwright install\n"
                "3. Django 服务器在虚拟环境中运行\n\n"
                f"详细错误: {str(e)}"
            )
            print(f"❌ {error_msg}")
            
            # 更新套件执行状态
            if self.execution:
                self.update_execution_result(
                    status='FAILED',
                    failed=len(self.test_cases),
                    error_msg=error_msg
                )
            
            # 更新所有用例状态为失败
            for test_case in self.test_cases:
                TestCaseExecution.objects.filter(
                    test_case=test_case,
                    test_suite=self.test_suite,
                    status='pending'
                ).update(
                    status='failed',
                    error_message=error_msg,
                    finished_at=timezone.now()
                )
            
            return

        # 预先获取所有测试用例的步骤数据，避免在Playwright上下文中访问ORM
        test_cases_data = []
        for test_case in self.test_cases:
            case_data = {
                'id': test_case.id,
                'name': test_case.name,
                'project_id': self.test_suite.project.id,
                'project_config': self.test_suite.project.debug_config,  # 添加项目配置
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
                    'enable_debug_capture': getattr(step, 'enable_debug_capture', False),  # 添加调试采集开关
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

        # 执行每个测试用例，为每个用例单独启动和关闭浏览器
        print(f"准备执行 {len(test_cases_data)} 个测试用例")

        with sync_playwright() as p:
            for i, case_data in enumerate(test_cases_data, 1):
                print(f"\n{'='*60}")
                print(f"正在执行第 {i}/{len(test_cases_data)} 个用例: {case_data['name']}")
                print(f"{'='*60}")
                
                # 记录用例实际开始执行时间
                case_execution = case_executions[case_data['id']]
                case_execution.started_at = timezone.now()
                case_execution.status = 'running'
                case_execution.save()

                # 为每个测试用例启动新的浏览器实例
                try:
                    # 选择浏览器
                    if self.browser == 'firefox':
                        browser = p.firefox.launch(headless=self.headless)
                    elif self.browser == 'safari':
                        browser = p.webkit.launch(headless=self.headless)
                    else:  # chrome or edge
                        # 添加防检测参数
                        browser = p.chromium.launch(
                            headless=self.headless,
                            args=['--disable-blink-features=AutomationControlled']
                        )

                    print(f"✓ 浏览器已启动")
                    
                    # 设备模拟与上下文配置
                    context_kwargs = {
                        'viewport': {'width': 1920, 'height': 1080},
                        'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
                    }
                    
                    # 解析环境配置中的设备类型
                    dev_name_to_use = self.device_name or (self.environment.device_name if self.environment else None)
                    dev_type_to_use = self.environment.device_type if self.environment else None
                    if dev_name_to_use:
                        # 对于 Playwright 提供的内置设备配置
                        try:
                            # 尝试获取 Playwright 中的设备模拟数据
                            device_config = p.devices.get(dev_name_to_use)
                            if device_config:
                                print(f"✓ 启用 Playwright 设备模拟: {dev_name_to_use}")
                                # 合并设备配置字典
                                context_kwargs.update(device_config)
                            else:
                                print(f"⚠️ Playwright 未找到设备: {dev_name_to_use}，将回退到默认设置")
                        except Exception as e:
                            print(f"⚠️ 应用设备模拟失败: {e}")
                    elif dev_type_to_use == 'MOBILE':
                        # 对通用移动端使用默认 iPhone 12 设置
                        device_config = p.devices.get('iPhone 12')
                        if device_config:
                            print("✓ 启用默认移动端模拟 (iPhone 12)")
                            context_kwargs.update(device_config)
                    
                    # 创建上下文
                    self.context = browser.new_context(**context_kwargs)
                    self.current_page = self.context.new_page()

                    # 导航到项目基础URL
                    if self.test_suite.project.base_url:
                        try:
                            print(f"正在导航到: {self.test_suite.project.base_url}")

                            # 检测是否在Linux服务器环境
                            import platform
                            is_linux = platform.system() == 'Linux'

                            # 使用 networkidle 等待页面加载完成
                            self.current_page.goto(self.test_suite.project.base_url, wait_until='networkidle', timeout=30000)

                            # 额外等待，确保动态内容加载（Vue/React等SPA应用）
                            # 服务器无头模式需要更长的等待时间
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
                            browser.close()
                            print(f"✓ 浏览器已关闭")
                            continue

                    # 执行测试用例（不再传递page参数，使用self.current_page）
                    case_result = self.execute_test_case_playwright_no_db(case_data)
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
                    # 确保每个用例执行后都关闭浏览器
                    try:
                        browser.close()
                        print(f"✓ 浏览器已关闭\n")
                    except:
                        pass

        # 注意：每个用例的执行记录已在执行过程中实时更新，不需要在这里统一更新

        duration = time.time() - start_time
        status = 'SUCCESS' if failed == 0 else 'FAILED'
        self.update_execution_result(status, passed, failed, skipped, duration)


    def execute_test_case_playwright_no_db(self, case_data):
        """使用 Playwright 执行单个测试用例（不访问数据库）

        Args:
            case_data: 预先准备的用例数据字典，包含id, name, project_id, steps等
            
        Note:
            使用 self.current_page 作为当前活动页面，switchTab会更新这个实例变量
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
            just_switched_tab = False  # 跟踪是否刚切换了标签页
            for step_data in case_data['steps']:
                # 如果刚切换了标签页，传递这个信息
                step_data['_just_switched_tab'] = just_switched_tab
                just_switched_tab = False  # 重置标志
                
                step_result = self.execute_step_playwright(
                    step_data, 
                    project_config=case_data.get('project_config'),
                    context_variables=self.context_variables
                )
                
                # Debug: Log which page we're using
                print(f"📄 步骤 {step_data['step_number']} 执行完成")
                print(f"   使用的page URL: {self.current_page.url}")
                print(f"   使用的page 标题: {self.current_page.title()}")
                
                result['steps'].append(step_result)
                
                # 显式更新self.current_page，确保引用正确
                if step_result.get('switched_page'):
                    self.current_page = step_result['switched_page']
                    print(f"🔄 页面切换确认: {self.current_page.title()}")
                    print(f"   当前页面URL: {self.current_page.url}")
                    print(f"   Page ID: {id(self.current_page)}")
                    del step_result['switched_page']
                    just_switched_tab = True
                
                # 步骤执行完后添加短暂延迟，确保页面状态稳定
                # 特别是点击操作后，可能触发动画、下拉框展开等
                if step_result['success'] and step_data['action_type'] in ['click', 'fill', 'hover']:
                    import asyncio
                    import time as sync_time
                    # 点击操作后等待更长时间（下拉框展开动画）
                    if step_data['action_type'] == 'click':
                        self.current_page.wait_for_timeout(800)  # 等待800ms，确保下拉框完全展开
                    else:
                        self.current_page.wait_for_timeout(300)  # 其他操作等待300ms

                # 如果步骤失败，捕获失败截图
                if not step_result['success']:
                    result['status'] = 'failed'
                    # 使用step的error信息作为case的error
                    result['error'] = step_result.get('error', f"步骤 {step_data['step_number']} 执行失败")

                    # 捕获失败截图（改进版）
                    try:
                        import base64
                        # 增加超时设置，避免截图等待时间过长
                        print(f"🔍 开始捕获失败截图 (步骤 {step_data['step_number']})...")
                        print(f"   当前page对象URL: {self.current_page.url}")
                        print(f"   当前page对象标题: {self.current_page.title()}")
                        screenshot_bytes = self.current_page.screenshot(timeout=5000)  # 5秒超时
                        print(f"   截图字节大小: {len(screenshot_bytes)} bytes")

                        screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                        print(f"   Base64 编码大小: {len(screenshot_base64)} characters")

                        # 验证 base64 编码是否有效
                        if len(screenshot_base64) < 100:
                            raise Exception(f"Base64 编码异常短 ({len(screenshot_base64)} chars)，可能截图失败")

                        screenshot_url = f'data:image/png;base64,{screenshot_base64}'
                        result['screenshots'].append({
                            'url': screenshot_url,
                            'description': f'步骤 {step_data["step_number"]} 失败截图: {step_data.get("description", "")}',
                            'step_number': step_data['step_number'],
                            'timestamp': datetime.now().isoformat()
                        })
                        print(f"✓ 失败截图已捕获 (步骤 {step_data['step_number']})")
                        print(f"   截图 URL 长度: {len(screenshot_url)} characters")
                    except Exception as screenshot_error:
                        error_msg = f"捕获失败截图失败: {str(screenshot_error)}"
                        print(f"⚠️  {error_msg}")
                        import traceback
                        print(f"   详细错误:\n{traceback.format_exc()}")
                        # 记录截图失败的详细信息到结果中
                        result['screenshots'].append({
                            'url': None,
                            'description': f'步骤 {step_data["step_number"]} 截图失败: {str(screenshot_error)}',
                            'step_number': step_data['step_number'],
                            'timestamp': datetime.now().isoformat(),
                            'error': str(screenshot_error)
                        })

                    break

        except Exception as e:
            result['status'] = 'failed'
            result['error'] = str(e)

            # 捕获异常截图（改进版）
            try:
                import base64
                # 增加超时设置，避免截图等待时间过长
                print(f"🔍 开始捕获异常截图...")
                screenshot_bytes = self.current_page.screenshot(timeout=5000)  # 5秒超时
                print(f"   截图字节大小: {len(screenshot_bytes)} bytes")

                screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                print(f"   Base64 编码大小: {len(screenshot_base64)} characters")

                # 验证 base64 编码是否有效
                if len(screenshot_base64) < 100:
                    raise Exception(f"Base64 编码异常短 ({len(screenshot_base64)} chars)，可能截图失败")

                screenshot_url = f'data:image/png;base64,{screenshot_base64}'
                result['screenshots'].append({
                    'url': screenshot_url,
                    'description': f'异常截图: {str(e)}',
                    'step_number': None,
                    'timestamp': datetime.now().isoformat()
                })
                print(f"✓ 异常截图已捕获")
                print(f"   截图 URL 长度: {len(screenshot_url)} characters")
            except Exception as screenshot_error:
                error_msg = f"捕获异常截图失败: {str(screenshot_error)}"
                print(f"⚠️  {error_msg}")
                import traceback
                print(f"   详细错误:\n{traceback.format_exc()}")
                # 记录截图失败的详细信息到结果中
                result['screenshots'].append({
                    'url': None,
                    'description': f'异常截图失败: {str(screenshot_error)}',
                    'step_number': None,
                    'timestamp': datetime.now().isoformat(),
                    'error': str(screenshot_error)
                })

        result['end_time'] = datetime.now().isoformat()
        return result


    def execute_test_case_playwright(self, page, case_data):
        self.current_page = page
        """使用 Playwright 执行单个测试用例（同步版本） - 已弃用，保留用于向后兼容

        Args:
            page: Playwright page对象
            case_data: 预先准备的用例数据字典，包含id, name, project_id, steps等
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

        # 创建用例执行记录
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
                step_result = self.execute_step_playwright(step_data)
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


    def execute_step_playwright(self, step_data, project_config=None, context_variables=None):
        """使用 Playwright 执行单个步骤（同步版本）
        
        Args:
            step_data: 预先准备的步骤数据字典
            project_config: 项目配置，用于调试采集
            context_variables: 跨测试套件传递的数据池
            
        Note:
            使用 self.current_page 作为当前活动页面
        """
        import time
        start_time = time.time()

        step_result = {
            'id': step_data['id'],
            'step_number': step_data['step_number'],
            'action_type': step_data['action_type'],
            'description': step_data['description'],
            'success': False,
            'error': None
        }
        
        # 步骤前采集
        self._capture_debug_data(self.current_page, step_data, project_config, timing='before')

        try:
            # 获取元素定位器
            if step_data['element']:
                element = step_data['element']
                locator_value = element['locator_value']
                locator_strategy = element['locator_strategy'].lower()
                element_name = element.get('name', '未知元素')

                # 根据定位策略构造 Playwright 选择器
                if locator_strategy in ['css', 'css selector']:
                    selector = locator_value
                elif locator_strategy == 'xpath':
                    selector = f'xpath={locator_value}'
                elif locator_strategy == 'id':
                    selector = f'#{locator_value}'
                elif locator_strategy == 'name':
                    selector = f'[name="{locator_value}"]'
                elif locator_strategy == 'text':
                    selector = f'text={locator_value}'
                else:
                    selector = locator_value

                # 根据操作类型执行动作
                if step_data['action_type'] == 'click':
                    # 检测是否是下拉框选项（需要特殊处理）
                    # 简化逻辑：只要是 XPath 的 //li 元素，或包含特定关键词，就认为是下拉框选项
                    is_dropdown_option = (
                        # 条件1: XPath 定位的 li 元素（最常见的下拉框选项）
                        (locator_strategy.lower() == 'xpath' and '//li' in locator_value) or
                        # 条件2: CSS 或 XPath 包含 el-select-dropdown
                        'el-select-dropdown' in locator_value.lower() or
                        # 条件3: 包含 role="option"
                        'role="option"' in locator_value.lower() or
                        # 条件4: 包含 li 标签且看起来像列表项
                        ('li' in locator_value.lower() and ('ul' in locator_value.lower() or 'ol' in locator_value.lower()))
                    )
                    
                    # 检测是否是 el-select 容器（下拉框触发器）
                    is_select_trigger = (
                        'el-select' in locator_value.lower() and 
                        'ancestor::' in locator_value and 
                        '//li' not in locator_value
                    )
                    
                    if is_select_trigger:
                        # el-select 容器：需要点击内部的真正触发器
                        import time as sync_time
                        
                        # 使用 JavaScript 查找并点击内部的可点击元素
                        if locator_strategy.lower() == 'xpath':
                            js_code = f"""
                                (() => {{
                                    const xpath = {repr(locator_value)};
                                    const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                                    const selectEl = result.singleNodeValue;
                                    
                                    if (!selectEl) return {{ success: false, error: '未找到 el-select 容器' }};
                                    
                                    // 查找内部的触发器（按优先级）
                                    let trigger = selectEl.querySelector('.el-select__wrapper') ||
                                                 selectEl.querySelector('input') ||
                                                 selectEl.querySelector('.el-input__inner');
                                    
                                    if (trigger) {{
                                        trigger.click();
                                        return {{ success: true, method: 'inner-trigger', element: trigger.className }};
                                    }} else {{
                                        // 如果找不到内部触发器，直接点击容器
                                        selectEl.click();
                                        return {{ success: true, method: 'container', element: selectEl.className }};
                                    }}
                                }})()
                            """
                        else:
                            js_code = f"""
                                (() => {{
                                    const selectEl = document.querySelector({repr(locator_value)});
                                    
                                    if (!selectEl) return {{ success: false, error: '未找到 el-select 容器' }};
                                    
                                    let trigger = selectEl.querySelector('.el-select__wrapper') ||
                                                 selectEl.querySelector('input') ||
                                                 selectEl.querySelector('.el-input__inner');
                                    
                                    if (trigger) {{
                                        trigger.click();
                                        return {{ success: true, method: 'inner-trigger', element: trigger.className }};
                                    }} else {{
                                        selectEl.click();
                                        return {{ success: true, method: 'container', element: selectEl.className }};
                                    }}
                                }})()
                            """
                        
                        js_result = self.current_page.evaluate(js_code)
                        
                        if js_result.get('success'):
                            self.current_page.wait_for_timeout(800)  # 等待下拉框展开
                            step_result['success'] = True
                        else:
                            step_result['error'] = f"✗ 下拉框触发器点击失败: {js_result.get('error')}"
                    
                    elif is_dropdown_option:
                        # 下拉框选项：使用 Playwright 原生方法（更可靠）
                        # 之前使用 JS click() 可能无法触发 Element Plus 的事件监听
                        self.current_page.wait_for_timeout(800)  # 等待下拉框展开
                        
                        print(f"[Playwright-调试] 下拉框选项处理: {locator_strategy}={locator_value}")
                        
                        # 构造基础定位器（移除 Playwright 特有的伪类，因为我们要手动遍历）
                        base_locator_value = locator_value.replace(' >> visible=true', '')
                        
                        try:
                            if locator_strategy.lower() == 'xpath':
                                if not base_locator_value.startswith('xpath='):
                                    candidates = self.current_page.locator(f"xpath={base_locator_value}")
                                else:
                                    candidates = self.current_page.locator(base_locator_value)
                            elif locator_strategy.lower() in ['css', 'css selector']:
                                candidates = self.current_page.locator(base_locator_value)
                            else:
                                # 其他策略暂按 CSS 处理
                                candidates = self.current_page.locator(base_locator_value)
                            
                            # 获取匹配元素数量
                            count = candidates.count()
                            print(f"[Playwright-调试] 找到 {count} 个匹配元素")
                            
                            found_visible = False
                            last_error = None
                            
                            for i in range(count):
                                try:
                                    candidate = candidates.nth(i)
                                    if candidate.is_visible():
                                        print(f"[Playwright-调试] 第 {i} 个元素可见，尝试点击...")
                                        # 使用 Playwright 的 click，它会触发完整的鼠标事件链
                                        candidate.click(timeout=2000)
                                        found_visible = True
                                        step_result['success'] = True
                                        print(f"[Playwright-调试] 点击成功")
                                        break
                                except Exception as e:
                                    print(f"[Playwright-调试] 点击第 {i} 个元素失败: {e}")
                                    last_error = e
                            
                            if not found_visible:
                                error_msg = f"未找到可见的下拉框选项 (匹配到 {count} 个元素)"
                                if last_error:
                                    error_msg += f", 最后一次错误: {str(last_error)}"
                                step_result['error'] = error_msg
                                step_result['success'] = False
                                
                        except Exception as e:
                            step_result['error'] = f"下拉框选项处理异常: {str(e)}"
                            step_result['success'] = False
                        
                        # 检查并关闭多选下拉框（如果还在显示）
                        if step_result['success']:
                            try:
                                if self.current_page.locator('.el-select-dropdown').first.is_visible():
                                    # 点击空白处关闭
                                    self.current_page.click('body', position={'x': 10, 'y': 10}, timeout=3000)
                                    self.current_page.wait_for_timeout(500)
                            except:
                                pass
                        
                        # 已移除调试面板代码
                    else:
                        # 普通元素：正常点击
                        # 如果刚切换了标签页，增加超时时间并滚动到元素
                        if step_data.get('_just_switched_tab'):
                            print(f"  ⚠️  刚切换标签页，增加元素等待时间和滚动")
                            
                            # 关键修复：确保页面保持在前台！
                            self.current_page.bring_to_front()
                            print(f"  ✓ 页面已置于前台")
                            
                            # 先尝试滚动到元素（确保元素在视口内）
                            try:
                                self.current_page.locator(selector).scroll_into_view_if_needed(timeout=5000)
                                print(f"  ✓ 元素已滚动到视口")
                            except Exception as e:
                                print(f"  ⚠️  滚动失败: {str(e)[:50]}")
                            
                            # 使用更长的超时时间（至少10秒）
                            extended_timeout = max(step_data['wait_time'], 10000)
                            self.current_page.click(selector, timeout=extended_timeout)
                            print(f"  ✓ 点击成功（超时: {extended_timeout}ms）")
                        else:
                            self.current_page.click(selector, timeout=step_data['wait_time'])
                        step_result['success'] = True

                elif step_data['action_type'] == 'fill':
                    # 解析输入值中的变量表达式
                    from .variable_resolver import resolve_variables
                    resolved_value = resolve_variables(step_data['input_value'], context_vars=context_variables)
                    
                    # 如果刚切换了标签页，增加超时时间
                    if step_data.get('_just_switched_tab'):
                        # 确保页面保持在前台
                        self.current_page.bring_to_front()
                        extended_timeout = max(step_data['wait_time'], 10000)
                        self.current_page.fill(selector, resolved_value, timeout=extended_timeout)
                    else:
                        self.current_page.fill(selector, resolved_value, timeout=step_data['wait_time'])
                    
                    step_result['success'] = True
                    # 记录解析后的值（用于调试）
                    if resolved_value != step_data['input_value']:
                        step_result['resolved_value'] = resolved_value
                        print(f"  ✓ 变量解析: {step_data['input_value']} -> {resolved_value}")


                elif step_data['action_type'] == 'upload':
                    import os
                    # 解析输入值（包含文件路径）
                    from .variable_resolver import resolve_variables
                    file_path = resolve_variables(step_data['input_value'], context_vars=context_variables)
                    
                    if not os.path.exists(file_path):
                        step_result['success'] = False
                        step_result['error'] = f"✗ 文件不存在: '{file_path}'"
                    else:
                        if step_data.get('_just_switched_tab'):
                            self.current_page.bring_to_front()
                            extended_timeout = max(step_data['wait_time'], 10000)
                            self.current_page.locator(selector).set_input_files(file_path, timeout=extended_timeout)
                        else:
                            self.current_page.locator(selector).set_input_files(file_path, timeout=step_data['wait_time'])
                        
                        step_result['success'] = True
                        if file_path != step_data['input_value']:
                            step_result['resolved_value'] = file_path
                            print(f"  ✓ 文件路径解析: {step_data['input_value']} -> {file_path}")

                elif step_data['action_type'] == 'getText':
                    text = self.current_page.text_content(selector, timeout=step_data['wait_time'])
                    step_result['result'] = text
                    step_result['success'] = True
                    
                    # 提取变量到上下文池
                    extract_key = step_data.get('extract_key')
                    if extract_key and context_variables is not None:
                        context_variables[extract_key] = text
                        print(f"  ✓ 提取变量至上下文: {extract_key} = {text}")

                elif step_data['action_type'] == 'waitFor':
                    # 检测是否是下拉框选项（下拉框选项可能是隐藏的）
                    is_dropdown_option_wait = (
                        (locator_strategy.lower() == 'xpath' and '//li' in locator_value) or
                        'el-select-dropdown' in locator_value.lower() or
                        'role="option"' in locator_value.lower() or
                        ('li' in locator_value.lower() and ('ul' in locator_value.lower() or 'ol' in locator_value.lower()))
                    )
                    
                    if is_dropdown_option_wait:
                        # 对于下拉框选项，只等待元素在DOM中（attached），不要求可见
                        self.current_page.wait_for_selector(selector, state='attached', timeout=step_data['wait_time'])
                    else:
                        # 普通元素：等待可见
                        self.current_page.wait_for_selector(selector, timeout=step_data['wait_time'])
                    
                    step_result['success'] = True

                elif step_data['action_type'] == 'hover':
                    self.current_page.hover(selector, timeout=step_data['wait_time'])
                    step_result['success'] = True

                elif step_data['action_type'] == 'scroll':
                    self.current_page.locator(selector).scroll_into_view_if_needed()
                    step_result['success'] = True

                elif step_data['action_type'] == 'screenshot':
                    screenshot_path = f'screenshots/step_{step_data["step_number"]}.png'
                    self.current_page.screenshot(path=screenshot_path)
                    step_result['screenshot'] = screenshot_path
                    step_result['success'] = True

                elif step_data['action_type'] == 'assert':
                    # 解析断言值中的变量
                    from .variable_resolver import resolve_variables
                    resolved_assert_value = resolve_variables(step_data['assert_value'], context_vars=context_variables)
                    if resolved_assert_value != step_data['assert_value']:
                         print(f"  ✓ 断言变量解析: {step_data['assert_value']} -> {resolved_assert_value}")

                    # 执行断言
                    if step_data['assert_type'] == 'textContains':
                        text = self.current_page.text_content(selector, timeout=step_data['wait_time'])
                        if resolved_assert_value in text:
                            step_result['success'] = True
                        else:
                            # 格式化为详细的错误信息，与playwright_engine.py保持一致
                            log = f"✗ 断言失败: 文本不包含 '{resolved_assert_value}'\n"
                            log += f"  - 实际文本: '{text}'"
                            step_result['error'] = log
                    elif step_data['assert_type'] == 'textEquals':
                        text = self.current_page.text_content(selector, timeout=step_data['wait_time'])
                        if text == resolved_assert_value:
                            step_result['success'] = True
                        else:
                            # 格式化为详细的错误信息
                            log = f"✗ 断言失败: 文本不等于 '{resolved_assert_value}'\n"
                            log += f"  - 期望: '{resolved_assert_value}'\n"
                            log += f"  - 实际: '{text}'"
                            step_result['error'] = log
                    elif step_data['assert_type'] == 'isVisible':
                        is_visible = self.current_page.is_visible(selector)
                        step_result['success'] = is_visible
                        if not is_visible:
                            step_result['error'] = f"✗ 断言失败: 元素 '{element_name}' 不可见"
                    elif step_data['assert_type'] == 'exists':
                        count = self.current_page.locator(selector).count()
                        step_result['success'] = count > 0
                        if count == 0:
                            step_result['error'] = f"✗ 断言失败: 元素 '{element_name}' 不存在"

                elif step_data['action_type'] == 'wait':
                    self.current_page.wait_for_timeout(step_data['wait_time'])
                    step_result['success'] = True

                elif step_data['action_type'] == 'switchTab':
                    # 切换标签页 - 同步版本
                    import time as sync_time
                    
                    # 获取超时时间
                    # 强制使用至少5秒的超时时间，确保有足够时间等待新标签页打开
                    user_wait = step_data.get('wait_time', 0) or 0
                    if user_wait > 0:
                        timeout = max(user_wait / 1000, 5.0)
                    else:
                        timeout = 5.0
                    
                    print(f"🔄 开始执行切换标签页 (超时: {timeout}s)...")
                    start_wait = sync_time.time()
                    current_page = self.current_page
                    target_index = -1
                    
                    # 轮询等待新标签页
                    # 轮询等待新标签页
                    while True:
                        pages = self.current_page.context.pages
                        target_index = -1  # 默认切换到最新标签页
                        should_switch = False
                        
                        # 调试日志：打印当前页面状态
                        print(f"  [Debug] 当前页面列表 (数量: {len(pages)}):")
                        for idx, p in enumerate(pages):
                            is_current = " (Current)" if p == current_page else ""
                            try:
                                print(f"    {idx}: {p.url} - {p.title()}{is_current}")
                            except Exception as e:
                                print(f"    {idx}: [Error getting info] {str(e)}")
                        
                        if step_data['input_value'] and str(step_data['input_value']).isdigit():
                            # 指定索引的情况
                            idx = int(step_data['input_value'])
                            if 0 <= idx < len(pages):
                                target_index = idx
                                should_switch = True
                        else:
                            # 自动模式：寻找一个不是当前页面的新页面
                            # 优先找列表末尾的（通常是新的）
                            candidates = [p for p in pages if p != current_page]
                            if candidates:
                                should_switch = True
                            elif len(pages) > 1:
                                # 如果有多个页面但都是 current_page (理论上不可能)，或者 current_page 不在 pages 里
                                # 只要页面数量增加，就应该切换
                                should_switch = True

                        if should_switch:
                            break
                        
                        if sync_time.time() - start_wait > timeout:
                            # 超时了
                            break
                        
                        # 关键修改：使用 wait_for_timeout 代替 time.sleep
                        # time.sleep 会阻塞线程，导致 Playwright 无法接收新页面事件
                        self.current_page.wait_for_timeout(500)
                    
                    # 获取目标页面
                    pages = self.current_page.context.pages
                    if target_index == -1:
                        # 自动模式
                        candidates = [p for p in pages if p != current_page]
                        if candidates:
                            # 切换到最新的一个非当前页面
                            target_page = candidates[-1]
                            final_target_index = pages.index(target_page)
                        else:
                            # 如果没有找到新页面
                            if len(pages) > 1:
                                # 备选：如果有多个页面，切换到最后一个
                                target_page = pages[-1]
                                final_target_index = len(pages) - 1
                            else:
                                raise Exception(f"切换标签页失败: 在 {timeout} 秒内未检测到新标签页打开 (当前页面数: {len(pages)})")
                    else:
                        target_page = pages[target_index]
                        final_target_index = target_index

                    # 将目标页面设为当前活动页面
                    target_page.bring_to_front()
                    
                    # 等待页面稳定
                    # 新标签页可能需要时间加载和渲染
                    try:
                        # 等待网络空闲状态（页面加载完成）
                        target_page.wait_for_load_state('networkidle', timeout=10000)  # 增加到10秒
                        print(f"  - 页面加载状态: networkidle")
                    except Exception as e:
                        # 如果networkidle超时，至少等待domcontentloaded
                        try:
                            target_page.wait_for_load_state('domcontentloaded', timeout=5000)  # 增加到5秒
                            print(f"  - 页面加载状态: domcontentloaded")
                        except Exception as e2:
                            print(f"  - 页面加载状态: 超时，继续执行 ({str(e2)[:50]})")
                    
                    # 额外等待一小段时间，确保页面完全稳定
                    target_page.wait_for_timeout(1500)  # 使用 wait_for_timeout 代替 sleep
                    
                    # 验证页面确实已切换
                    print(f"  - 当前活动页面URL: {target_page.url}")
                    print(f"  - 页面是否可见: {target_page.is_visible('body') if target_page else 'Unknown'}")
                    
                    # 关键修复：直接更新实例变量！
                    self.current_page = target_page
                    step_result['switched_page'] = target_page
                    step_result['success'] = True
                    
                    print(f"✓ 切换标签页成功")
                    print(f"  - 目标索引: {final_target_index}")
                    print(f"  - 页面标题: {self.current_page.title()}")
                    print(f"  - self.current_page已更新为新页面")

                else:
                    step_result['error'] = f'⚠ 未知的操作类型: {step_data["action_type"]}'

            else:
                # 没有元素的步骤（如等待、切换标签页）
                if step_data['action_type'] == 'wait':
                    self.current_page.wait_for_timeout(step_data['wait_time'])
                    step_result['success'] = True
                
                elif step_data['action_type'] == 'switchTab':
                    # 切换标签页 - 同步版本（无需元素）
                    import time as sync_time
                    
                    # 获取超时时间
                    # 强制使用至少5秒的超时时间，确保有足够时间等待新标签页打开
                    user_wait = step_data.get('wait_time', 0) or 0
                    if user_wait > 0:
                        timeout = max(user_wait / 1000, 5.0)
                    else:
                        timeout = 5.0
                    
                    print(f"🔄 开始执行切换标签页 (超时: {timeout}s)...")
                    start_wait = sync_time.time()
                    current_page = self.current_page
                    target_index = -1
                    
                    # 轮询等待新标签页
                    # 轮询等待新标签页
                    while True:
                        pages = self.current_page.context.pages
                        target_index = -1  # 默认切换到最新标签页
                        should_switch = False
                        
                        # 调试日志：打印当前页面状态
                        print(f"  [Debug] 当前页面列表 (数量: {len(pages)}):")
                        for idx, p in enumerate(pages):
                            is_current = " (Current)" if p == current_page else ""
                            try:
                                print(f"    {idx}: {p.url} - {p.title()}{is_current}")
                            except Exception as e:
                                print(f"    {idx}: [Error getting info] {str(e)}")
                        
                        if step_data['input_value'] and str(step_data['input_value']).isdigit():
                            # 指定索引的情况
                            idx = int(step_data['input_value'])
                            if 0 <= idx < len(pages):
                                target_index = idx
                                should_switch = True
                        else:
                            # 自动模式：寻找一个不是当前页面的新页面
                            # 优先找列表末尾的（通常是新的）
                            candidates = [p for p in pages if p != current_page]
                            if candidates:
                                should_switch = True
                            elif len(pages) > 1:
                                # 如果有多个页面但都是 current_page (理论上不可能)，或者 current_page 不在 pages 里
                                # 只要页面数量增加，就应该切换
                                should_switch = True

                        if should_switch:
                            break
                        
                        if sync_time.time() - start_wait > timeout:
                            # 超时了
                            break
                        
                        # 关键修改：使用 wait_for_timeout 代替 time.sleep
                        self.current_page.wait_for_timeout(500)
                    
                    # 获取目标页面
                    pages = self.current_page.context.pages
                    if target_index == -1:
                        # 自动模式
                        candidates = [p for p in pages if p != current_page]
                        if candidates:
                            # 切换到最新的一个非当前页面
                            target_page = candidates[-1]
                            final_target_index = pages.index(target_page)
                        else:
                            # 如果没有找到新页面
                            if len(pages) > 1:
                                # 备选：如果有多个页面，切换到最后一个
                                target_page = pages[-1]
                                final_target_index = len(pages) - 1
                            else:
                                raise Exception(f"切换标签页失败: 在 {timeout} 秒内未检测到新标签页打开 (当前页面数: {len(pages)})")
                    else:
                        target_page = pages[target_index]
                        final_target_index = target_index

                    # 将目标页面设为当前活动页面
                    target_page.bring_to_front()
                    
                    # 等待页面稳定
                    try:
                        # 等待网络空闲状态（页面加载完成）
                        target_page.wait_for_load_state('networkidle', timeout=10000)  # 增加到10秒
                        print(f"  - 页面加载状态: networkidle")
                    except Exception as e:
                        # 如果networkidle超时，至少等待domcontentloaded
                        try:
                            target_page.wait_for_load_state('domcontentloaded', timeout=5000)  # 增加到5秒
                            print(f"  - 页面加载状态: domcontentloaded")
                        except Exception as e2:
                            print(f"  - 页面加载状态: 超时，继续执行 ({str(e2)[:50]})")
                    
                    # 额外等待一小段时间，确保页面完全稳定
                    target_page.wait_for_timeout(1500)  # 使用 wait_for_timeout 代替 sleep
                    
                    # 验证页面确实已切换
                    print(f"  - 当前活动页面URL: {target_page.url}")
                    print(f"  - 页面是否可见: {target_page.is_visible('body') if target_page else 'Unknown'}")
                    
                    # 关键修复：直接更新实例变量！
                    self.current_page = target_page
                    step_result['switched_page'] = target_page
                    step_result['success'] = True
                    
                    print(f"✓ 切换标签页成功")
                    print(f"  - 目标索引: {final_target_index}")
                    print(f"  - 页面标题: {self.current_page.title()}")
                    print(f"  - self.current_page已更新为新页面")

        except Exception as e:
            # 格式化为详细的错误信息，与playwright_engine.py保持一致
            execution_time = round(time.time() - start_time, 2)

            # 提取详细的错误信息（改进版）
            error_str = str(e)
            error_type = type(e).__name__

            # 尝试提取更详细的 Playwright 异常信息
            try:
                # Playwright 异常可能包含更详细的信息
                if hasattr(e, 'message') and e.message:
                    error_str = e.message
                # TimeoutError 通常有更详细的描述
                elif hasattr(e, 'args') and e.args:
                    error_str = str(e.args[0]) if len(e.args) > 0 else error_str
            except:
                pass  # 如果提取失败，使用原始 error_str

            # 添加异常类型信息（如果还没有）
            if error_type not in error_str and error_type != 'Exception':
                error_str = f"{error_type}: {error_str}"

            # 判断是否是超时错误
            if 'Timeout' in error_str or 'timeout' in error_str:
                element_name = step_data['element'].get('name', '未知元素') if step_data.get('element') else '页面'
                locator_info = f"{step_data['element']['locator_strategy']}={step_data['element']['locator_value']}" if step_data.get('element') else '无'

                log = f"✗ 操作超时\n"
                log += f"  - 元素: '{element_name}'\n"
                log += f"  - 定位器: {locator_info}\n"
                log += f"  - 超时时间: {execution_time}秒\n"
                log += f"  - 错误: {error_str}"
                step_result['error'] = log
            else:
                element_name = step_data['element'].get('name', '未知元素') if step_data.get('element') else '页面'
                locator_info = f"{step_data['element']['locator_strategy']}={step_data['element']['locator_value']}" if step_data.get('element') else '无'

                log = f"✗ 执行失败\n"
                log += f"  - 元素: '{element_name}'\n"
                log += f"  - 定位器: {locator_info}\n"
                log += f"  - 执行时间: {execution_time}秒\n"
                log += f"  - 错误: {error_str}"
                step_result['error'] = log

            # 打印详细日志便于调试
            print(f"❌ Playwright 步骤执行失败:")
            print(f"   异常类型: {error_type}")
            print(f"   错误信息: {error_str[:500]}")  # 限制长度避免刷屏

        # 步骤后采集
        after_data = self._capture_debug_data(self.current_page, step_data, project_config, timing='after')
        if after_data:
            if 'debug_data' not in step_result:
                step_result['debug_data'] = {}
            step_result['debug_data']['after'] = after_data

        return step_result


