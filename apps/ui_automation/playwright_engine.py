"""
Playwright自动化测试执行引擎
用于驱动真实浏览器执行UI自动化测试
"""
import asyncio
import base64
import time
import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from playwright.async_api import async_playwright, Page, Browser, BrowserContext, TimeoutError as PlaywrightTimeout
from django.conf import settings
import logging
from .variable_resolver import resolve_variables

logger = logging.getLogger(__name__)

class PlaywrightTestEngine:
    """Playwright测试执行引擎"""

    def __init__(self, browser_type='chromium', headless=True, environment_id=None, device_name=None):
        """
        初始化测试引擎

        Args:
            browser_type: 浏览器类型 (chromium, firefox, webkit)
            headless: 是否无头模式
            environment_id: 环境配置ID，用于读取设备或视口信息
            device_name: h5模拟设备名称
        """
        self.browser_type = browser_type
        self.headless = headless
        self.environment_id = environment_id
        self.device_name = device_name
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def start(self):
        """启动浏览器"""
        try:
            self.playwright = await async_playwright().start()

            # 根据浏览器类型选择启动方式
            channel = None
            if self.browser_type == 'chromium':
                browser_launcher = self.playwright.chromium
            elif self.browser_type == 'chrome':
                browser_launcher = self.playwright.chromium
                channel = 'chrome'
            elif self.browser_type == 'msedge':
                browser_launcher = self.playwright.chromium
                channel = 'msedge'
            elif self.browser_type == 'firefox':
                browser_launcher = self.playwright.firefox
            elif self.browser_type == 'webkit':
                browser_launcher = self.playwright.webkit
            else:
                browser_launcher = self.playwright.chromium

            # 启动浏览器
            launch_args = {
                'headless': self.headless,
                'args': [
                    '--disable-blink-features=AutomationControlled',
                    '--start-maximized' # 启动时最大化窗口
                ]
            }
            if channel:
                launch_args['channel'] = channel

            try:
                self.browser = await browser_launcher.launch(**launch_args)
            except Exception as e:
                # 如果是 Chrome 启动失败，尝试降级
                if channel == 'chrome':
                    logger.warning(f"Chrome 启动失败，尝试使用 Edge: {e}")
                    # 1. 尝试降级到 Edge
                    launch_args['channel'] = 'msedge'
                    try:
                        self.browser = await browser_launcher.launch(**launch_args)
                        # 更新当前实例的 browser_type 标记，以便日志准确
                        self.browser_type = 'msedge'
                    except Exception as e2:
                        logger.warning(f"Edge 启动也失败，尝试使用 Playwright 自带 Chromium: {e2}")
                        # 2. 尝试降级到 Playwright 自带 Chromium
                        # 移除 channel 参数，使用默认的 bundled chromium
                        if 'channel' in launch_args:
                            del launch_args['channel']
                        try:
                            self.browser = await browser_launcher.launch(**launch_args)
                            self.browser_type = 'chromium'
                        except Exception as e3:
                            logger.error(f"所有浏览器启动尝试均失败: {e3}")
                            raise e # 抛出最初的 Chrome 错误，因为这是用户的首选
                else:
                    raise e

            # 创建浏览器上下文
            # viewport=None 是必须的，配合 --start-maximized 使用，否则窗口会被裁剪
            context_options = {
                'viewport': None,
                'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
            }

            if self.device_name:
                if self.device_name in self.playwright.devices:
                    device_config = self.playwright.devices[self.device_name]
                    context_options.update(device_config)
                    logger.info(f"📱 启用移动设备模拟: {self.device_name}")
                else:
                    logger.warning(f"⚠️ Playwright不支持设备 '{self.device_name}'")
            elif self.environment_id:
                try:
                    # 使用 sync_to_async 来查询数据库
                    from asgiref.sync import sync_to_async
                    from .models import TestEnvironment
                    
                    @sync_to_async
                    def get_env():
                        return TestEnvironment.objects.get(id=self.environment_id)
                        
                    env = await get_env()
                    if getattr(env, 'device_name', None) and env.device_type in ['MOBILE', 'MINI_PROGRAM']:
                        if env.device_name in self.playwright.devices:
                            device_config = self.playwright.devices[env.device_name]
                            context_options.update(device_config)
                            logger.info(f"📱 启用移动设备模拟: {env.device_name}")
                        else:
                            logger.warning(f"⚠️ Playwright不支持设备 '{env.device_name}'")
                    elif getattr(env, 'resolution', None):
                        try:
                            w, h = env.resolution.lower().split('x')
                            context_options['viewport'] = {'width': int(w.strip()), 'height': int(h.strip())}
                        except Exception:
                            pass
                except Exception as e:
                    logger.warning(f"⚠ 读取测试环境配置失败: {e}")

            self.context = await self.browser.new_context(**context_options)
            
            logger.info("浏览器上下文已创建")

            # 创建页面
            self.page = await self.context.new_page()

            logger.info(f"浏览器启动成功: {self.browser_type}, headless={self.headless}")

        except Exception as e:
            logger.error(f"启动浏览器失败: {str(e)}")
            raise

    async def stop(self):
        """关闭浏览器"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("浏览器已关闭")
        except Exception as e:
            logger.error(f"关闭浏览器失败: {str(e)}")

    async def _capture_debug_data(self, step, project_config=None, timing="after"):
        """采集调试数据"""
        try:
            # 1. 检查是否开启全局采集
            if not project_config or not project_config.get('enable_debug_capture', False):
                return None
            
            # 2. 检查步骤是否开启采集
            if not getattr(step, 'enable_debug_capture', False):
                return None

            # 3. 检查时机配置
            debug_config = project_config.get('debug_config', {})
            if not debug_config.get(f'enable_{timing}', False):
                return None

            items = debug_config.get(f'{timing}_items', [])
            if not items:
                return None

            # 创建调试数据目录
            # 结构: media/debug_data/project_id/case_id/
            project_id = step.test_case.project.id
            case_id = step.test_case.id
            step_name = f"step_{step.step_number}"
            
            # 使用 MEDIA_ROOT
            relative_dir = os.path.join('debug_data', str(project_id), str(case_id))
            base_dir = os.path.join(settings.MEDIA_ROOT, relative_dir)
            os.makedirs(base_dir, exist_ok=True)
            
            timestamp = int(time.time() * 1000)
            file_prefix = f"{step_name}_{timing}_{timestamp}"
            
            data = {}
            captured_data = {}
            
            # 采集各项数据
            if "dom" in items:
                try:
                    data["dom"] = await self.page.content()
                except:
                    pass
                    
            if "iframes" in items:
                try:
                    data["iframes"] = [frame.url for frame in self.page.frames]
                except:
                    pass
                    
            if "text_candidates" in items:
                try:
                    data["text_candidates"] = await self.page.evaluate("() => document.body.innerText")
                except:
                    pass

            # 保存JSON数据
            if data:
                json_filename = f"{file_prefix}.json"
                json_path = os.path.join(base_dir, json_filename)
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                captured_data['data_file'] = os.path.join(settings.MEDIA_URL, relative_dir, json_filename).replace('\\', '/')
                    
            # 截图作为额外文件
            if "screenshot" in items:
                screenshot_filename = f"{file_prefix}.png"
                screenshot_path = os.path.join(base_dir, screenshot_filename)
                try:
                    await self.page.screenshot(path=screenshot_path)
                    captured_data['screenshot'] = os.path.join(settings.MEDIA_URL, relative_dir, screenshot_filename).replace('\\', '/')
                except:
                    pass
            
            return captured_data

        except Exception as e:
            logger.error(f"Error capturing debug data: {e}")
            return None

    async def execute_step(self, step, element_data: Dict, project_config: Dict = None) -> Tuple[bool, str, Optional[str], Optional[Dict]]:
        """
        执行单个测试步骤

        Args:
            step: 测试步骤对象
            element_data: 元素数据字典 {locator_strategy, locator_value, name}

        Returns:
            (是否成功, 日志信息, 截图base64, 调试数据)
        """
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
        debug_data = {}

        # 步骤前采集
        debug_data['before'] = await self._capture_debug_data(step, project_config, timing='before')

        try:
            # wait和screenshot操作不需要元素定位器
            if action_type == 'wait':
                wait_seconds = step.wait_time / 1000 if step.wait_time else 1
                await asyncio.sleep(wait_seconds)
                execution_time = round(time.time() - start_time, 2)
                log = f"✓ 固定等待 {wait_seconds} 秒完成 - 耗时 {execution_time}秒"
                # 步骤后采集
                debug_data['after'] = await self._capture_debug_data(step, project_config, timing='after')
                return True, log, None, debug_data

            elif action_type == 'screenshot':
                screenshot = await self.page.screenshot()
                screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                execution_time = round(time.time() - start_time, 2)
                log = f"✓ 截图成功\n"
                log += f"  - 截图范围: 整个页面\n"
                log += f"  - 执行时间: {execution_time}秒"
                # 步骤后采集
                debug_data['after'] = await self._capture_debug_data(step, project_config, timing='after')
                return True, log, screenshot_base64, debug_data

            elif action_type == 'switchTab':
                # 切换标签页
                # 获取超时时间
                if step.wait_time:
                    timeout = step.wait_time / 1000
                else:
                    timeout = 5.0
                
                start_wait = time.time()
                current_page = self.page
                target_index = -1
                
                while True:
                    pages = self.context.pages
                    target_index = -1  # 默认切换到最新标签页
                    should_switch = False
                    
                    if resolved_input_value and str(resolved_input_value).isdigit():
                        # 指定索引的情况
                        idx = int(resolved_input_value)
                        if 0 <= idx < len(pages):
                            target_index = idx
                            should_switch = True
                    else:
                        # 切换到最新的情况
                        target_index = -1
                        # 如果最新的页面不是当前页面，说明有新标签页，或者是切换到其他已存在的标签页
                        if pages[-1] != current_page:
                            should_switch = True
                        # 如果只有一个页面，且就是当前页，可能是在等待新标签页打开
                        elif len(pages) == 1 and pages[0] == current_page:
                            should_switch = False
                        # 如果有多个页面，但最新的就是当前页，可能是想留在当前页，也可能是等待更新的
                        else:
                            should_switch = False

                    if should_switch:
                        break
                    
                    if time.time() - start_wait > timeout:
                        # 超时了，就切换到当前能找到的那个（Best Effort）
                        break
                        
                    await asyncio.sleep(0.5)
                
                # 获取目标页面
                if target_index == -1:
                    target_page = pages[-1]
                    final_target_index = len(pages) - 1
                else:
                    target_page = pages[target_index]
                    final_target_index = target_index

                # 将目标页面设为当前活动页面
                await target_page.bring_to_front()
                # 更新引擎的当前页面引用
                self.page = target_page
                
                execution_time = round(time.time() - start_time, 2)
                log = f"✓ 切换标签页成功\n"
                log += f"  - 目标索引: {final_target_index}\n"
                log += f"  - 页面标题: {await self.page.title()}\n"
                log += f"  - 执行时间: {execution_time}秒"
                # 步骤后采集
                debug_data['after'] = await self._capture_debug_data(step, project_config, timing='after')
                return True, log, None, debug_data

            elif action_type == 'urlJump':
                target_url = resolved_input_value
                if not target_url:
                    return False, "✗ URL跳转失败: URL 不能为空", None, debug_data
                    
                # Support relative paths based on project base_url
                if target_url.startswith('/') and project_config and 'base_url' in project_config:
                    base_url = project_config['base_url'].rstrip('/')
                    target_url = f"{base_url}{target_url}"
                elif not target_url.startswith('http'):
                    target_url = f"http://{target_url}"
                    
                await self.page.goto(target_url, timeout=30000, wait_until='networkidle')
                execution_time = round(time.time() - start_time, 2)
                log = f"✓ URL跳转成功\n"
                log += f"  - 目标地址: {target_url}\n"
                log += f"  - 执行时间: {execution_time}秒"
                debug_data['after'] = await self._capture_debug_data(step, project_config, timing='after')
                return True, log, None, debug_data

            elif action_type == 'urlExtract':
                current_url = self.page.url
                execution_time = round(time.time() - start_time, 2)
                log = f"✓ URL提取成功\n"
                log += f"  - 当前地址: {current_url}\n"
                
                # 如果用户在期望值里写了变量名，可以保存起来(后续可通过环境变量机制传递，此处先打印)
                var_name = resolved_assert_value or "ExtractedURL"
                log += f"  - 提取为变量: {var_name} (待关联变量管理器)\n"
                log += f"  - 执行时间: {execution_time}秒"
                
                debug_data['after'] = await self._capture_debug_data(step, project_config, timing='after')
                return True, log, None, debug_data

            elif action_type == 'ai_act':
                from .services.stagehand_service import StagehandService
                service = StagehandService(self.page)
                
                # Use resolved_input_value as the action description
                action_desc = resolved_input_value or "Interact with element"
                
                success, msg = await service.act(action_desc)
                execution_time = round(time.time() - start_time, 2)
                
                # Capture debug data
                debug_data['after'] = await self._capture_debug_data(step, project_config, timing='after')
                
                if success:
                    return True, f"✓ {msg}\n  - 耗时: {execution_time}秒", None, debug_data
                else:
                    screenshot = await self.page.screenshot()
                    screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                    return False, f"✗ AI操作失败: {msg}\n  - 耗时: {execution_time}秒", screenshot_base64, debug_data

            elif action_type == 'ai_extract':
                from .services.stagehand_service import StagehandService
                service = StagehandService(self.page)
                
                instruction = resolved_input_value or "Extract data"
                # Use assert_value as schema description if available
                schema = resolved_assert_value or "Extract all relevant fields as key-value pairs"
                
                success, data = await service.extract(instruction, schema)
                execution_time = round(time.time() - start_time, 2)
                
                debug_data['after'] = await self._capture_debug_data(step, project_config, timing='after')
                
                if success:
                    formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
                    return True, f"✓ AI提取成功\n  - 数据: {formatted_json}\n  - 耗时: {execution_time}秒", None, debug_data
                else:
                    screenshot = await self.page.screenshot()
                    screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                    return False, f"✗ AI提取失败: {data}\n  - 耗时: {execution_time}秒", screenshot_base64, debug_data

            elif action_type == 'ai_vision':
                from .services.stagehand_service import StagehandService
                service = StagehandService(self.page)
                
                instruction = resolved_input_value or "Click target"
                
                success, msg = await service.vision_act(instruction)
                execution_time = round(time.time() - start_time, 2)
                
                debug_data['after'] = await self._capture_debug_data(step, project_config, timing='after')
                
                if success:
                    return True, f"✓ {msg}\n  - 耗时: {execution_time}秒", None, debug_data
                else:
                    screenshot = await self.page.screenshot()
                    screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                    return False, f"✗ AI视觉操作失败: {msg}\n  - 耗时: {execution_time}秒", screenshot_base64, debug_data

            # 其他操作需要元素定位器
            # 获取元素定位器
            locator_strategy = element_data.get('locator_strategy', 'css')
            locator_value = element_data.get('locator_value', '')
            element_name = element_data.get('name', '未知元素')

            # 获取强制操作选项（用于visibility:hidden的元素）
            force_action = element_data.get('force_action', False)

            # 计算超时时间：优先使用元素的wait_timeout（秒），其次使用步骤的wait_time（毫秒）
            # 如果元素有wait_timeout，转换为毫秒；否则使用步骤的wait_time
            element_wait_timeout = element_data.get('wait_timeout')  # 秒
            if element_wait_timeout is not None and element_wait_timeout > 0:
                timeout_ms = element_wait_timeout * 1000  # 转换为毫秒
            elif step.wait_time:
                timeout_ms = step.wait_time
            else:
                timeout_ms = 5000  # 默认5秒

            # 根据定位策略获取元素
            if locator_strategy.lower() == 'id':
                locator = self.page.locator(f'#{locator_value}')
            elif locator_strategy.lower() in ['css', 'css selector']:
                # CSS 定位器，对于可能匹配多个元素的情况，添加 .first
                # 特别是下拉框选项，可能有多个同名选项
                if any(keyword in locator_value.lower() for keyword in ['dropdown', 'el-select', ':has(', 'li']):
                    # 如果是下拉框选项，强制只查找可见元素
                    if 'visible=true' not in locator_value:
                        locator = self.page.locator(f"{locator_value} >> visible=true").first
                    else:
                        locator = self.page.locator(locator_value).first
                else:
                    locator = self.page.locator(locator_value)
            elif locator_strategy.lower() == 'xpath':
                # XPath 定位器
                # 如果是下拉框选项，强制只查找可见元素
                if any(keyword in locator_value.lower() for keyword in ['dropdown', 'el-select', ':has(', 'li']):
                    if 'visible=true' not in locator_value:
                        locator = self.page.locator(f"xpath={locator_value} >> visible=true").first
                    else:
                        locator = self.page.locator(f"xpath={locator_value}").first
                # 如果 XPath 已经包含索引 [n]，不要添加 .first（会冲突）
                elif '[' in locator_value and ']' in locator_value:
                    locator = self.page.locator(f'xpath={locator_value}')
                else:
                    # 如果没有索引，添加 .first 避免 strict mode violation
                    locator = self.page.locator(f'xpath={locator_value}').first
            elif locator_strategy.lower() == 'text':
                locator = self.page.get_by_text(locator_value)
            elif locator_strategy.lower() == 'name':
                locator = self.page.locator(f'[name="{locator_value}"]')
            elif locator_strategy.lower() == 'placeholder':
                locator = self.page.get_by_placeholder(locator_value)
            elif locator_strategy.lower() == 'role':
                locator = self.page.get_by_role(locator_value)
            elif locator_strategy.lower() == 'label':
                locator = self.page.get_by_label(locator_value)
            elif locator_strategy.lower() == 'title':
                locator = self.page.get_by_title(locator_value)
            elif locator_strategy.lower() == 'test-id':
                locator = self.page.get_by_test_id(locator_value)
            else:
                # 默认使用CSS选择器
                locator = self.page.locator(locator_value)

            # 执行操作
            execution_time = 0

            if action_type == 'click':
                # 对于下拉框选项，需要特殊处理
                # 通过定位器特征自动识别下拉框选项
                is_dropdown_option = (
                    'dropdown' in locator_value.lower() or 
                    'el-select' in locator_value.lower() or 
                    '下拉' in element_name or 
                    '选项' in element_name or
                    'role="option"' in locator_value.lower() or
                    'el-select-dropdown__item' in locator_value.lower() or  # Element Plus 下拉框
                    ('//li' in locator_value and 'span=' in locator_value)  # XPath 下拉框模式
                )
                
                # 检测是否是点击 el-select 容器（下拉框触发器）
                is_select_trigger = ('el-select' in locator_value.lower() and 
                                    'ancestor::' in locator_value.lower() and
                                    'el-select-dropdown' not in locator_value.lower())
                
                if is_select_trigger:
                    # el-select 容器：点击内部的真正触发器，触发完整事件链
                    logger.info(f"检测到 el-select 容器，使用 Playwright 原生点击...")
                    try:
                        # 等待容器出现
                        await locator.wait_for(state='visible', timeout=timeout_ms)
                        # 点击内部的 wrapper 或 input（使用 Playwright 原生点击，会触发完整事件）
                        wrapper_locator = locator.locator('.el-select__wrapper, input').first
                        await wrapper_locator.click(timeout=timeout_ms, no_wait_after=False)
                        # 等待下拉框展开动画
                        await asyncio.sleep(0.5)
                        
                        execution_time = round(time.time() - start_time, 2)
                        log = f"✓ 点击下拉框触发器 '{element_name}' 成功\n"
                        log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                        log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                        log += f"  - 特殊处理: Playwright原生点击内部触发器 + 等待展开\n"
                        log += f"  - 执行时间: {execution_time}秒"
                        # 步骤后采集
                        debug_data['after'] = await self._capture_debug_data(step, project_config, timing='after')
                        return True, log, None, debug_data
                    except Exception as e:
                        logger.warning(f"Playwright 点击失败，尝试其他方法: {e}")
                        
                        # 备用方案：使用完整的事件链
                        try:
                            await locator.locator('.el-select__wrapper, input').first.evaluate("""
                                element => {
                                    const events = [
                                        new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window }),
                                        new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window }),
                                        new MouseEvent('click', { bubbles: true, cancelable: true, view: window })
                                    ];
                                    events.forEach(event => element.dispatchEvent(event));
                                }
                            """)
                            await asyncio.sleep(0.5)
                            execution_time = round(time.time() - start_time, 2)
                            log = f"✓ 点击下拉框触发器 '{element_name}' 成功（事件链）\n"
                            log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                            log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                            log += f"  - 执行时间: {execution_time}秒"
                            # 步骤后采集
                            debug_data['after'] = await self._capture_debug_data(step, project_config, timing='after')
                            return True, log, None, debug_data
                        except Exception as e2:
                            logger.error(f"所有点击方法都失败: {e2}")
                            raise
                
                elif is_dropdown_option:
                    # 下拉框选项：需要特殊处理，确保能正确触发 Vue/Element Plus 的 v-model 更新
                    logger.info(f"检测到下拉框选项，使用 Playwright + Vue 数据更新策略...")
                    
                    # 等待下拉框完全展开并渲染
                    await asyncio.sleep(0.8)
                    
                    try:
                        # 等待元素在 DOM 中（不要求可见）
                        await locator.wait_for(state='attached', timeout=timeout_ms)
                        logger.info(f"元素已在 DOM 中，执行 Vue 数据更新...")
                        
                        # 策略：直接通过 page.evaluate() 操作，绕过 locator 的 actionability 检查
                        # locator.evaluate() 会等待元素可见，但下拉框选项可能是隐藏的
                        # 所以我们使用 page.evaluate() 并传递定位器表达式
                        
                        # 根据定位策略构造 JavaScript 选择器
                        if locator_strategy.lower() == 'xpath':
                            js_selector_code = f"""
                                const xpath = {repr(locator_value)};
                                const result = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                                let element = null;
                                for (let i = 0; i < result.snapshotLength; i++) {{
                                    const node = result.snapshotItem(i);
                                    // 检查可见性: offsetParent 不为 null (且不是 fixed 定位) 或者 getComputedStyle display != none
                                    if (node.offsetParent !== null || window.getComputedStyle(node).display !== 'none') {{
                                        element = node;
                                        break;
                                    }}
                                }}
                            """
                        elif locator_strategy.lower() == 'css selector':
                            js_selector_code = f"""
                                const elements = document.querySelectorAll({repr(locator_value)});
                                let element = null;
                                for (const el of elements) {{
                                    if (el.offsetParent !== null || window.getComputedStyle(el).display !== 'none') {{
                                        element = el;
                                        break;
                                    }}
                                }}
                            """
                        else:
                            # 其他策略：尝试作为 CSS 选择器
                            js_selector_code = f"""
                                const elements = document.querySelectorAll({repr(locator_value)});
                                let element = null;
                                for (const el of elements) {{
                                    if (el.offsetParent !== null || window.getComputedStyle(el).display !== 'none') {{
                                        element = el;
                                        break;
                                    }}
                                }}
                            """
                        
                        # 构造基础定位器（不带 visible=true，因为我们要手动遍历）
                        base_locator_value = locator_value.replace(' >> visible=true', '')
                        
                        if locator_strategy.lower() == 'xpath':
                            if not base_locator_value.startswith('xpath='):
                                candidates = self.page.locator(f"xpath={base_locator_value}")
                            else:
                                candidates = self.page.locator(base_locator_value)
                        elif locator_strategy.lower() == 'css selector':
                            candidates = self.page.locator(base_locator_value)
                        else:
                            # 其他策略暂按 CSS 处理
                            candidates = self.page.locator(base_locator_value)
                        
                        # 获取匹配元素数量
                        count = await candidates.count()
                        logger.info(f"找到 {count} 个匹配元素，开始寻找可见元素...")
                        
                        found_visible = False
                        for i in range(count):
                            candidate = candidates.nth(i)
                            if await candidate.is_visible():
                                logger.info(f"找到第 {i+1} 个元素是可见的，执行点击...")
                                try:
                                    await candidate.click(timeout=timeout_ms)
                                    found_visible = True
                                    method_desc = f"iterative-click(index={i})"
                                    break
                                except Exception as e:
                                    logger.warning(f"点击第 {i+1} 个元素失败: {e}")
                        
                        if not found_visible:
                            logger.warning("未找到可见的下拉框选项元素，尝试点击第一个...")
                            try:
                                await candidates.first.click(force=True, timeout=timeout_ms)
                                method_desc = "fallback-force-click"
                            except Exception as e:
                                logger.error(f"强制点击失败: {e}")
                                raise e

                        # 检查并关闭多选下拉框
                        try:
                            await asyncio.sleep(0.5)
                            dropdown = self.page.locator('.el-select-dropdown').first
                            if await dropdown.is_visible():
                                logger.info(f"多选下拉框未自动关闭，点击空白处关闭...")
                                await self.page.click('body', position={'x': 10, 'y': 10}, timeout=3000)
                                auto_close_msg = " + 自动关闭"
                            else:
                                auto_close_msg = ""
                        except:
                            auto_close_msg = ""
                        
                        execution_time = round(time.time() - start_time, 2)
                        log = f"✓ 点击下拉框选项 '{element_name}' 成功（{method_desc}）\n"
                        log += f"  - 定位器: {locator_strategy}={base_locator_value}\n"
                        log += f"  - 匹配数量: {count}\n"
                        log += f"  - 执行方法: {method_desc}{auto_close_msg}\n"
                        log += f"  - 执行时间: {execution_time}秒"
                        # 步骤后采集
                        debug_data['after'] = await self._capture_debug_data(step, project_config, timing='after')
                        return True, log, None, debug_data
                        
                        logger.info(f"JS执行结果: {js_result}")
                        
                        # 等待 Vue 响应式更新完成
                        await asyncio.sleep(0.8)
                        
                        # 检查并关闭多选下拉框
                        try:
                            dropdown = self.page.locator('.el-select-dropdown').first
                            if await dropdown.is_visible():
                                logger.info(f"多选下拉框未自动关闭，点击空白处关闭...")
                                await self.page.click('body', position={'x': 10, 'y': 10}, timeout=3000)
                                await asyncio.sleep(0.5)
                                auto_close_msg = " + 自动关闭"
                            else:
                                auto_close_msg = ""
                        except:
                            auto_close_msg = ""
                        
                        execution_time = round(time.time() - start_time, 2)
                        method_desc = js_result.get('method', 'unknown') if isinstance(js_result, dict) else 'unknown'
                        log = f"✓ 点击下拉框选项 '{element_name}' 成功（{method_desc})\n"
                        log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                        log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                        log += f"  - 更新方法: {method_desc}{auto_close_msg}\n"
                        if isinstance(js_result, dict) and 'allValues' in js_result:
                            log += f"  - 当前选中值: {js_result['allValues']}\n"
                        log += f"  - 执行时间: {execution_time}秒"
                        # 步骤后采集
                        debug_data['after'] = await self._capture_debug_data(step, project_config, timing='after')
                        return True, log, None, debug_data
                    except Exception as e:
                        logger.error(f"下拉框选项点击失败: {e}")
                        execution_time = round(time.time() - start_time, 2)

                        # 构建详细的错误日志
                        error_log = f"✗ 点击下拉框选项 '{element_name}' 失败\n"
                        error_log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                        error_log += f"  - 执行时间: {execution_time}秒\n"
                        error_log += f"  - 错误: {str(e)}\n\n"
                        error_log += "建议解决方案:\n"
                        error_log += "1. 检查元素是否在下拉框展开后才出现在 DOM 中\n"
                        error_log += "2. 尝试在点击下拉框后增加等待时间（添加 wait 步骤，等待2000ms）\n"
                        error_log += "3. 使用 Playwright get_by_text 定位：文本=无忧行-鸿蒙APP\n"
                        error_log += "4. 检查 Vue DevTools 确认组件结构是否与代码匹配"

                        # 尝试捕获截图
                        screenshot_base64 = None
                        try:
                            screenshot = await self.page.screenshot()
                            screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                        except:
                            pass

                        # 返回: (是否成功, 日志信息, 截图base64)
                        return False, error_log, screenshot_base64, debug_data
                else:
                    # 普通元素：正常点击
                    click_method_note = ""
                    
                    # 如果启用了强制操作，先等待元素在 DOM 中，不要求可见
                    if force_action:
                        try:
                            await locator.wait_for(state='attached', timeout=timeout_ms)
                        except:
                            pass  # 如果已经在 DOM 中，继续
                    
                    # 特殊处理：如果点击的是隐藏的 <select> 元素 (常见于 UI 库如 Element Plus)
                    # 尝试自动重定向点击到其关联的可见 Trigger 元素
                    redirected_click = False
                    
                    try:
                        # 检查是否为 SELECT 标签（不依赖可见性，因为即使被拦截，tag_name 也是 SELECT）
                        tag_name = await locator.evaluate("el => el.tagName", timeout=1000)
                        
                        if tag_name == 'SELECT':
                            logger.info("检测到 SELECT 标签，尝试查找并点击关联的 UI 组件...")
                            # 查找父级容器
                            parent = locator.locator('..')
                            # 查找常见 Trigger 类名
                            trigger = parent.locator('.el-select__wrapper, .el-input, .el-select__input, .ant-select-selector').first
                            
                            if await trigger.count() > 0 and await trigger.is_visible():
                                await trigger.click(timeout=timeout_ms)
                                redirected_click = True
                                click_method_note += "  - 提示: 目标是隐藏Select，已自动点击关联的UI组件\n"
                            else:
                                logger.info("未找到关联的可见 UI 组件，尝试继续点击原元素...")
                    except Exception as e_redirect:
                        logger.warning(f"尝试重定向点击失败: {e_redirect}")

                    if not redirected_click:
                        try:
                            await locator.click(timeout=timeout_ms, force=force_action)
                        except Exception as e:
                            error_msg = str(e)
                            # 如果点击失败（被拦截 或 超时），尝试使用 JavaScript 点击
                            # Timeout 可能是因为元素存在但不满足点击条件（如被遮挡、动画中、disabled等），或者元素根本不存在
                            # 如果是 Timeout，我们尝试 JS 点击，但给一个较短的超时，避免长时间等待不存在的元素
                            if force_action or "intercepts pointer events" in error_msg or "Timeout" in error_msg:
                                logger.warning(f"Playwright 常规点击失败 ({error_msg})，尝试使用 JS 强制点击")
                                
                                # 启发式重试：如果主选择器失败且是超时，尝试查找替代按钮（针对登录等常见场景）
                                heuristic_success = False
                                if "Timeout" in error_msg and await locator.count() == 0:
                                    # 常见登录按钮特征
                                    heuristic_selectors = [
                                        "button:has-text('登录')",
                                        "button:has-text('Login')",
                                        "button:has-text('Sign in')",
                                        "button[type='submit']", # 再次尝试，也许现在加载出来了
                                        "div[role='button']:has-text('登录')"
                                    ]
                                    
                                    logger.info(f"主定位器 {locator_value} 未找到元素，尝试启发式搜索...")
                                    for h_selector in heuristic_selectors:
                                        # 跳过与原选择器完全相同的
                                        if h_selector == locator_value:
                                            continue
                                            
                                        h_locator = self.page.locator(h_selector).first
                                        if await h_locator.count() > 0 and await h_locator.is_visible():
                                            logger.info(f"启发式搜索找到替代元素: {h_selector}")
                                            try:
                                                # 使用 dispatchEvent 模拟更真实的点击
                                                await h_locator.evaluate("""
                                                    element => {
                                                        element.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
                                                        element.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
                                                        element.dispatchEvent(new MouseEvent('click', {bubbles: true}));
                                                    }
                                                """)
                                                click_method_note += f"  - 提示: 原定位器失败，使用替代定位器 '{h_selector}' JS模拟点击成功\n"
                                                heuristic_success = True
                                                break
                                            except:
                                                pass
                                
                                if not heuristic_success:
                                    # 启动 AI Agent 自愈 (Self-Healing)
                                    logger.info("启发式搜索失败，尝试启动 AI Agent 自愈 (Self-Healing)...")
                                    try:
                                        from .services.stagehand_service import StagehandService
                                        service = StagehandService(self.page)
                                        heal_success, healed_selector, heal_reason = await service.auto_heal(
                                            failed_selector=locator_value,
                                            error_msg=error_msg,
                                            target_desc=element_name
                                        )
                                        if heal_success and healed_selector:
                                            logger.info(f"AI 自愈成功! 新选择器: {healed_selector}. 原因: {heal_reason}")
                                            click_method_note += f"  - ⚡ AI自愈: 原选择器失效，动态修正为 '{healed_selector}' (原因: {heal_reason})\n"
                                            healed_locator = self.page.locator(healed_selector).first
                                            await healed_locator.click(timeout=timeout_ms)
                                            heuristic_success = True
                                    except Exception as heal_e:
                                        logger.warning(f"AI 自愈失败: {heal_e}")

                                if not heuristic_success:
                                    try:
                                        # 尝试先 scroll into view
                                        try:
                                            await locator.scroll_into_view_if_needed(timeout=1000)
                                        except:
                                            pass
                                            
                                        # 使用 evaluate 模拟完整点击事件
                                        # 单纯的 element.click() 有时会被 React/Vue 的合成事件系统忽略
                                        await locator.evaluate("""
                                            element => {
                                                // 1. 尝试原生 click
                                                element.click();
                                                
                                                // 2. 如果没反应，手动派发事件
                                                const clickEvent = new MouseEvent('click', {
                                                    bubbles: true,
                                                    cancelable: true,
                                                    view: window
                                                });
                                                element.dispatchEvent(clickEvent);
                                            }
                                        """, timeout=2000)
                                        click_method_note += f"  - 提示: 常规点击失败，已使用 JS 增强型点击成功\n"
                                    except Exception as js_e:
                                        logger.warning(f"JS 点击也失败: {js_e}")
                                        # 如果 JS 点击也失败，抛出原始异常（通常更有意义）
                                        raise e
                            else:
                                raise e
                    
                    # 关键修复：点击后等待页面导航或 URL 变化
                    # 仅针对可能是提交操作的点击（type=submit 或包含 '登录'/'Login'）
                    is_submit_action = (
                        'type=\'submit\'' in locator_value or 
                        'type="submit"' in locator_value or
                        '登录' in element_name or 
                        'Login' in element_name
                    )
                    
                    if is_submit_action:
                         logger.info("检测到可能是提交/登录操作，等待页面加载...")
                         try:
                             # 等待 load 事件，最长 5 秒
                             # 只要发生任何网络空闲或 load 事件即可，不要太严格
                             # 修改为等待 url 变化或网络空闲
                             current_url = self.page.url
                             try:
                                 # 尝试等待 URL 变化
                                 await self.page.wait_for_url(lambda url: url != current_url, timeout=3000)
                                 click_method_note += "  - 提示: 检测到 URL 变化，跳转成功\n"
                             except:
                                 # 如果 URL 没变，尝试等待网络空闲
                                 await self.page.wait_for_load_state('networkidle', timeout=3000)
                                 click_method_note += "  - 提示: 等待网络空闲完成\n"
                         except:
                             pass # 超时也没关系，可能页面已经加载完了或者只是 AJAX 跳转

                    execution_time = round(time.time() - start_time, 2)
                    log = f"✓ 点击元素 '{element_name}' 成功\n"
                    log += click_method_note
                    log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                    log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                    if force_action:
                        log += f"  - 强制操作: 是（跳过可见性检查，等待attached）\n"
                    log += f"  - 执行时间: {execution_time}秒"
                    # 步骤后采集
                    debug_data['after'] = await self._capture_debug_data(step, project_config, timing='after')
                    return True, log, None, debug_data

            elif action_type == 'fill':
                try:
                    await locator.fill(resolved_input_value, timeout=timeout_ms, force=force_action)
                except Exception as e:
                    logger.warning(f"Playwright fill 失败 ({e})，尝试启动 AI Agent 自愈...")
                    try:
                        from .services.stagehand_service import StagehandService
                        service = StagehandService(self.page)
                        heal_success, healed_selector, heal_reason = await service.auto_heal(
                            failed_selector=locator_value,
                            error_msg=str(e),
                            target_desc=element_name
                        )
                        if heal_success and healed_selector:
                            logger.info(f"AI 自愈成功! 新选择器: {healed_selector}")
                            healed_locator = self.page.locator(healed_selector).first
                            await healed_locator.fill(resolved_input_value, timeout=timeout_ms, force=force_action)
                            locator_strategy = 'AI-Healed'
                            locator_value = healed_selector
                        else:
                            raise e
                    except Exception as heal_e:
                        raise e
                execution_time = round(time.time() - start_time, 2)

                # 输入成功后短暂等待，确保表单验证生效
                # 特别是在服务器环境下，需要给Vue/React等框架时间处理
                await asyncio.sleep(0.3)
                
                # 手动触发事件，确保 Vue/React 监听到变化
                try:
                    await locator.evaluate("""
                        element => {
                            element.dispatchEvent(new Event('input', { bubbles: true }));
                            element.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    """)
                except Exception as e_event:
                    logger.warning(f"手动触发事件失败: {e_event}")

                # 尝试触发 blur 事件，确保验证被触发
                try:
                    await locator.blur(timeout=1000)
                except:
                    pass

                log = f"✓ 在元素 '{element_name}' 中输入文本成功\n"
                log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                if resolved_input_value != step.input_value:
                    log += f"  - 变量解析: '{step.input_value}' => '{resolved_input_value}'\n"
                log += f"  - 输入内容: '{resolved_input_value}'\n"
                log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                if force_action:
                    log += f"  - 强制操作: 是（忽略可见性检查）\n"
                log += f"  - 执行时间: {execution_time}秒"
                # 步骤后采集
                debug_data['after'] = await self._capture_debug_data(step, project_config, timing='after')
                return True, log, None, debug_data

            elif action_type == 'getText':
                text = await locator.inner_text(timeout=timeout_ms)
                execution_time = round(time.time() - start_time, 2)
                log = f"✓ 获取元素 '{element_name}' 的文本成功\n"
                log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                log += f"  - 文本内容: '{text}'\n"
                log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                log += f"  - 执行时间: {execution_time}秒"
                # 步骤后采集
                debug_data['after'] = await self._capture_debug_data(step, project_config, timing='after')
                return True, log, None, debug_data

            elif action_type == 'waitFor':
                await locator.wait_for(state='visible', timeout=timeout_ms)
                execution_time = round(time.time() - start_time, 2)
                log = f"✓ 等待元素 '{element_name}' 出现成功\n"
                log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                log += f"  - 等待时间: {execution_time}秒"
                # 步骤后采集
                debug_data['after'] = await self._capture_debug_data(step, project_config, timing='after')
                return True, log, None, debug_data

            elif action_type == 'hover':
                await locator.hover(timeout=timeout_ms, force=force_action)
                execution_time = round(time.time() - start_time, 2)
                log = f"✓ 在元素 '{element_name}' 上悬停成功\n"
                log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                if force_action:
                    log += f"  - 强制操作: 是（忽略可见性检查）\n"
                log += f"  - 执行时间: {execution_time}秒"
                # 步骤后采集
                await self._capture_debug_data(step, project_config, timing='after')
                return True, log, None

            elif action_type == 'scroll':
                await locator.scroll_into_view_if_needed(timeout=timeout_ms)
                execution_time = round(time.time() - start_time, 2)
                log = f"✓ 滚动到元素 '{element_name}' 成功\n"
                log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                log += f"  - 执行时间: {execution_time}秒"
                return True, log, None

            elif action_type == 'selectOption':
                # 尝试选择选项
                try:
                    # 优先尝试 label (因为常见用法)
                    await locator.select_option(label=resolved_input_value, timeout=timeout_ms, force=force_action)
                    method = "label"
                except Exception:
                    try:
                        # 尝试 value
                        await locator.select_option(value=resolved_input_value, timeout=timeout_ms, force=force_action)
                        method = "value"
                    except Exception:
                        try:
                            # 尝试直接传值 (Playwright 自动匹配)
                            await locator.select_option(resolved_input_value, timeout=timeout_ms, force=force_action)
                            method = "auto"
                        except Exception as e3:
                            raise Exception(f"选择选项失败: {str(e3)}")

                execution_time = round(time.time() - start_time, 2)
                log = f"✓ 选择选项 '{resolved_input_value}' 成功 ({method})\n"
                
                # 尝试点击视觉选项 (针对 Element UI 等隐藏 Select 的情况)
                try:
                    # 检查 select 是否隐藏
                    if not await locator.is_visible():
                         # 如果是 label 方式，尝试查找并点击可见的选项元素
                         if method == "label":
                             option_text = resolved_input_value
                             
                             # 尝试查找对应的视觉选项
                             # 1. 尝试 .el-select-dropdown__item (Element Plus)
                             # 尝试多种选择器
                             visual_option = self.page.locator(f".el-select-dropdown__item >> text='{option_text}'").first
                             
                             # 2. 尝试使用 get_by_text (更鲁棒)
                             if await visual_option.count() == 0:
                                 visual_option = self.page.get_by_text(option_text, exact=True).first
                                 if await visual_option.count() == 0:
                                     # 尝试非精确匹配
                                     visual_option = self.page.get_by_text(option_text, exact=False).first

                             # 3. 如果没找到，尝试 role=option (通用 ARIA)
                             if await visual_option.count() == 0:
                                 visual_option = self.page.get_by_role("option", name=option_text).first
                             
                             # 4. 如果还是没找到，尝试 li 包含文本
                             if await visual_option.count() == 0:
                                 visual_option = self.page.locator(f"li:has-text('{option_text}')").first

                             # 尝试点击
                             if await visual_option.count() > 0:
                                 try:
                                     # 强制点击，因为可能在动画中
                                     # 设置较短超时，避免卡住
                                     await visual_option.click(timeout=2000, force=True)
                                     log += "  - 提示: 已同步点击视觉选项 (UI Component)\n"
                                 except Exception as e_v:
                                     log += f"  - 警告: 点击视觉选项失败: {e_v}\n"
                             else:
                                 log += "  - 警告: 未找到匹配文本的视觉选项，表单状态可能未更新\n"
                                 
                                 # 最后的救命稻草：如果找不到选项，可能是下拉框没打开？
                                 # 再次尝试点击下拉框触发器？不，太复杂了。
                                 # 尝试通过键盘操作：Down Arrow + Enter?
                                 # 暂时不实现，风险较高
                except Exception as e_visual:
                    logger.warning(f"点击视觉选项失败: {e_visual}")

                log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                if force_action:
                    log += f"  - 强制操作: 是\n"
                log += f"  - 执行时间: {execution_time}秒"
                # 步骤后采集
                debug_data['after'] = await self._capture_debug_data(step, project_config, timing='after')
                return True, log, None, debug_data

            elif action_type in ['dragAndDrop', 'DRAG_AND_DROP']:
                target_selector = ''
                if hasattr(step, 'action_params') and step.action_params:
                    if isinstance(step.action_params, dict):
                        target_selector = step.action_params.get('target_selector', '')
                    elif isinstance(step.action_params, str):
                        try:
                            import json
                            params_dict = json.loads(step.action_params)
                            target_selector = params_dict.get('target_selector', '')
                        except:
                            pass
                            
                if not target_selector:
                    log = "✕ 拖拽失败: 未配置目标选择器(target_selector，需在操作参数中配置)"
                    screenshot = await self.page.screenshot()
                    return False, log, screenshot, debug_data
                    
                try:
                    target_locator = self.page.locator(target_selector).first
                    await locator.drag_to(target_locator, timeout=timeout_ms)
                    execution_time = round(time.time() - start_time, 2)
                    log = f"✓ 拖拽成功 (目标: {target_selector})\n"
                    log += f"  - 源元素: {locator_strategy}={locator_value}\n"
                    log += f"  - 执行时间: {execution_time}秒"
                    debug_data['after'] = await self._capture_debug_data(step, project_config, timing='after')
                    return True, log, None, debug_data
                except Exception as e:
                    log = f"✕ 拖拽失败: {str(e)}"
                    screenshot = await self.page.screenshot()
                    return False, log, screenshot, debug_data

            elif action_type == 'assert':
                # 根据断言类型执行不同的断言
                if step.assert_type == 'textContains':
                    text = await locator.inner_text(timeout=timeout_ms)
                    if resolved_assert_value in text:
                        log = f"✓ 断言通过: 文本包含 '{resolved_assert_value}'\n"
                        if resolved_assert_value != step.assert_value:
                             log += f"  - 变量解析: '{step.assert_value}' => '{resolved_assert_value}'\n"
                        log += f"  - 实际文本: '{text}'\n"
                        log += f"  - 超时设置: {timeout_ms/1000}秒"
                        return True, log, None
                    else:
                        log = f"✗ 断言失败: 文本不包含 '{resolved_assert_value}'\n"
                        if resolved_assert_value != step.assert_value:
                             log += f"  - 变量解析: '{step.assert_value}' => '{resolved_assert_value}'\n"
                        log += f"  - 实际文本: '{text}'"
                        screenshot = await self.page.screenshot()
                        screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                        return False, log, screenshot_base64

                elif step.assert_type == 'textEquals':
                    text = await locator.inner_text(timeout=timeout_ms)
                    if text == resolved_assert_value:
                        log = f"✓ 断言通过: 文本等于 '{resolved_assert_value}'\n"
                        if resolved_assert_value != step.assert_value:
                             log += f"  - 变量解析: '{step.assert_value}' => '{resolved_assert_value}'\n"
                        log += f"  - 超时设置: {timeout_ms/1000}秒"
                        # 步骤后采集
                        debug_data['after'] = await self._capture_debug_data(step, project_config, timing='after')
                        return True, log, None, debug_data
                    else:
                        log = f"✗ 断言失败: 文本不等于 '{resolved_assert_value}'\n"
                        if resolved_assert_value != step.assert_value:
                             log += f"  - 变量解析: '{step.assert_value}' => '{resolved_assert_value}'\n"
                        log += f"  - 期望: '{resolved_assert_value}'\n"
                        log += f"  - 实际: '{text}'"
                        screenshot = await self.page.screenshot()
                        screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                        return False, log, screenshot_base64

                elif step.assert_type == 'isVisible':
                    is_visible = await locator.is_visible()
                    if is_visible:
                        log = f"✓ 断言通过: 元素 '{element_name}' 可见"
                        # 步骤后采集
                        await self._capture_debug_data(step, project_config, timing='after')
                        return True, log, None
                    else:
                        log = f"✗ 断言失败: 元素 '{element_name}' 不可见"
                        screenshot = await self.page.screenshot()
                        screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                        return False, log, screenshot_base64

                elif step.assert_type == 'exists':
                    count = await locator.count()
                    if count > 0:
                        log = f"✓ 断言通过: 元素 '{element_name}' 存在"
                        # 步骤后采集
                        after_data = await self._capture_debug_data(step, project_config, timing='after')
                        if after_data:
                            debug_data.update(after_data)
                        return True, log, None, debug_data
                    else:
                        log = f"✗ 断言失败: 元素 '{element_name}' 不存在"
                        screenshot = await self.page.screenshot()
                        screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                        return False, log, screenshot_base64, debug_data

                elif step.assert_type == 'isHidden':
                    is_hidden = await locator.is_hidden()
                    if is_hidden:
                        log = f"✓ 断言通过: 元素 '{element_name}' 不可见"
                        debug_data['after'] = await self._capture_debug_data(step, project_config, timing='after')
                        return True, log, None, debug_data
                    else:
                        log = f"✗ 断言失败: 元素 '{element_name}' 仍可见"
                        screenshot = await self.page.screenshot()
                        screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                        return False, log, screenshot_base64, debug_data

                elif step.assert_type == 'valueEquals':
                    value = await locator.input_value(timeout=timeout_ms)
                    if value == resolved_assert_value:
                        log = f"✓ 断言通过: 元素值等于 '{resolved_assert_value}'"
                        debug_data['after'] = await self._capture_debug_data(step, project_config, timing='after')
                        return True, log, None, debug_data
                    else:
                        log = f"✗ 断言失败: 元素值不等于 '{resolved_assert_value}'\n  - 期望: '{resolved_assert_value}'\n  - 实际: '{value}'"
                        screenshot = await self.page.screenshot()
                        screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                        return False, log, screenshot_base64, debug_data

                elif step.assert_type == 'isEnabled':
                    is_enabled = await locator.is_enabled(timeout=timeout_ms)
                    if is_enabled:
                        log = f"✓ 断言通过: 元素 '{element_name}' 可用/启用"
                        debug_data['after'] = await self._capture_debug_data(step, project_config, timing='after')
                        return True, log, None, debug_data
                    else:
                        log = f"✗ 断言失败: 元素 '{element_name}' 被禁用"
                        screenshot = await self.page.screenshot()
                        screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                        return False, log, screenshot_base64, debug_data

                elif step.assert_type == 'aiAssert':
                    from .services.stagehand_service import StagehandService
                    service = StagehandService(self.page)
                    instruction = step.assert_value or "Check if the page state matches expectations."
                    success, data = await service.extract(instruction, '{"is_passed": "boolean", "reason": "string"}')
                    
                    if success and data.get('is_passed', False):
                        log = f"✓ AI智能断言通过: {data.get('reason', '状态符合预期')}"
                        debug_data['after'] = await self._capture_debug_data(step, project_config, timing='after')
                        return True, log, None, debug_data
                    else:
                        reason = data.get('reason', '状态不符合预期') if success else "AI分析异常"
                        log = f"✗ AI智能断言失败: {reason}"
                        screenshot = await self.page.screenshot()
                        screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                        return False, log, screenshot_base64, debug_data



            else:
                log = f"⚠ 未知的操作类型: {action_type}"
                return True, log, None, debug_data

        except PlaywrightTimeout as e:
            execution_time = round(time.time() - start_time, 2)
            log = f"✗ 操作超时\n"
            log += f"  - 元素: '{element_name}'\n"
            log += f"  - 定位器: {locator_strategy}={locator_value}\n"
            log += f"  - 超时时间: {execution_time}秒\n"
            log += f"  - 错误: {str(e)}\n"
            
            # 检查元素状态，提供更详细的诊断信息
            try:
                # 重新获取定位器（避免 stale element）
                check_locator = locator
                if await check_locator.count() > 0:
                    is_visible = await check_locator.is_visible()
                    is_enabled = await check_locator.is_enabled()
                    log += f"  - 元素状态诊断:\n"
                    log += f"    - 存在: 是\n"
                    log += f"    - 可见: {'是' if is_visible else '否'}\n"
                    log += f"    - 可用(Enabled): {'是' if is_enabled else '否 (可能是表单验证未通过)'}\n"
                    
                    if not is_enabled:
                        log += "    -> 提示: 按钮处于禁用状态，通常是因为前序步骤（如输入框填写）未触发页面逻辑更新。\n"
                else:
                    log += f"  - 元素状态诊断: 元素在超时后未找到\n"
            except Exception as diag_e:
                log += f"  - 诊断失败: {diag_e}\n"

            # 捕获失败截图与 AI 自愈合
            try:
                screenshot = await self.page.screenshot()
                screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                
                from .services.stagehand_service import StagehandService
                service = StagehandService(self.page)
                
                # 开始 AI 智能自愈合 (用例修复)
                if action_type in ['click', 'input']:
                    log += "\n  - [AI 自愈合] 尝试启动智能元素定位自愈合..."
                    heal_instruction = f"Attempting to perform action '{action_type}' on target: {element_name}"
                    success, msg = await service.vision_act(heal_instruction)
                    
                    if success:
                        log += f"\n  - [AI 自愈合] 修复成功: 利用视觉多模态大模型找到了变化后的元素 '{element_name}' 并完成了自动操作。\n  - 建议: 测试继续执行，但请更新测试用例库中该元素的定位器 (Locator)。"
                        return True, log, None, debug_data
                    else:
                        log += f"\n  - [AI 自愈合] 修复失败: AI也无法在当前页面视觉化找到该元素或完成操作。"
                
                # 如果依然失败，进入智能失败分析
                analysis_prompt = f"UI automation failed with error: {str(e)}. Locate element {element_name} using {locator_strategy}={locator_value}. Please analyze the attached screenshot and error message to determine the root cause. Explain briefly in Chinese."
                success, analysis = await service.extract(analysis_prompt, '{"root_cause": "string", "suggestion": "string"}')
                if success:
                    log += f"\n  - AI 失败诊断: {analysis.get('root_cause', '未知')}\n  - 建议修复: {analysis.get('suggestion', '请检查选择器')}"
            except Exception as ai_e:
                log += f"\n  - AI 诊断异常/截图失败: {str(ai_e)}"

            return False, log, getattr(locals(), 'screenshot_base64', None), debug_data

        except Exception as e:
            execution_time = round(time.time() - start_time, 2)
            log = f"✗ 执行失败\n"
            log += f"  - 元素: '{element_name}'\n"
            log += f"  - 定位器: {locator_strategy}={locator_value}\n"
            log += f"  - 执行时间: {execution_time}秒\n"
            log += f"  - 错误: {str(e)}"

            # 捕获失败截图
            try:
                screenshot = await self.page.screenshot()
                screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                
                # AI 智能失败分析
                from .services.stagehand_service import StagehandService
                service = StagehandService(self.page)
                analysis_prompt = f"UI automation failed with error: {str(e)}. Element: {element_name}. Please analyze the screen state."
                success, analysis = await service.extract(analysis_prompt, '{"root_cause": "string", "suggestion": "string"}')
                if success:
                    log += f"\n  - AI 失败诊断: {analysis.get('root_cause', '未知')}\n  - 建议修复: {analysis.get('suggestion', '请检查操作流程')}"
            except Exception as ai_e:
                log += f"\n  - AI 诊断异常/截图失败: {str(ai_e)}"

            return False, log, getattr(locals(), 'screenshot_base64', None), debug_data

    async def navigate(self, url: str) -> Tuple[bool, str]:
        """
        导航到指定URL

        Args:
            url: 目标URL

        Returns:
            (是否成功, 日志信息)
        """
        try:
            # 检测是否在Linux服务器环境
            import platform
            is_linux = platform.system() == 'Linux'

            # 使用 networkidle 等待页面加载完成
            await self.page.goto(url, wait_until='networkidle', timeout=30000)

            # 额外等待，确保动态内容加载（Vue/React等SPA应用）
            # 服务器无头模式需要更长的等待时间
            extra_wait = 3 if is_linux else 2
            await asyncio.sleep(extra_wait)

            log = f"✓ 成功导航到: {url}\n"
            log += f"  - 等待页面加载完成（networkidle + 额外{extra_wait}秒）"
            return True, log
        except Exception as e:
            log = f"✗ 导航失败: {url}\n  - 错误: {str(e)}"
            return False, log

    async def capture_screenshot(self) -> str:
        """
        捕获当前页面截图

        Returns:
            截图的base64字符串
        """
        try:
            screenshot = await self.page.screenshot(full_page=True)
            return f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
        except Exception as e:
            logger.error(f"捕获截图失败: {str(e)}")
            return None
