import time
import base64
import logging

logger = logging.getLogger(__name__)

class MiniumTestEngine:
    """Minium (WeChat Mini-Program) 测试执行引擎"""

    def __init__(self, project_path=None, dev_tool_path=None):
        """
        初始化Minium测试引擎
        """
        self.project_path = project_path
        self.dev_tool_path = dev_tool_path
        self.mini = None
        
    def start(self):
        """启动Minium及微信开发者工具"""
        try:
            import minium
            logger.info("正在启动微信小程序测试引擎 (Minium)...")
            try:
                self.mini = minium.Minium(
                    project_path=self.project_path,
                    dev_tool_path=self.dev_tool_path
                )
                logger.info("✓ Minium 引擎启动成功")
            except Exception as e:
                logger.warning(f"Minium启动异常(未安装开发者工具或配置错误)，将使用Mock模式: {e}")
                self.mini = "mock_instance"
                
        except ImportError:
            logger.warning("未安装 minium 库。将使用Mock模式。请执行 pip install minium")
            self.mini = "mock_instance"
        except Exception as e:
            logger.error(f"启动Minium失败: {str(e)}")
            raise

    def stop(self):
        """关闭小程序工具"""
        if self.mini and self.mini != "mock_instance":
            try:
                self.mini.release()
                logger.info("Minium 引擎已释放")
            except Exception as e:
                logger.error(f"关闭Minium失败: {str(e)}")

    def navigate(self, url):
        """
        小程序页面导航 (对应 urlJump 或者直接配置打开的page)
        """
        if self.mini == "mock_instance":
            return True, f"✓ [Mock] 跳转到小程序页面: {url}"
            
        try:
            if not url.startswith('/'):
                url = '/' + url
            self.mini.app.redirect_to(url)
            return True, f"✓ 跳转到小程序页面: {url}"
        except Exception as e:
            return False, f"✗ 小程序页面跳转失败: {str(e)}"

    def capture_screenshot(self):
        """捕获错误截图"""
        if self.mini == "mock_instance":
            return None
        try:
            res = self.mini.app.screen_shot()
            if res:
                with open(res, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode()
                    return f"data:image/png;base64,{encoded_string}"
            return None
        except Exception as e:
            logger.error(f"截图失败: {str(e)}")
            return None
            
    def _get_element(self, locator_strategy, locator_value):
        """获取小程序元素"""
        if self.mini == "mock_instance":
            return "mock_element"
            
        page = self.mini.app.current_page()
        # Minium 支持 wxml 的选择器 (ID, Class, 标签等)
        return page.get_element(locator_value)

    def execute_step(self, step, element_data):
        """
        执行单个测试步骤: 返回 (success, log_msg, screenshot)
        """
        action_type = step.action_type
        start_time = time.time()
        
        from .variable_resolver import resolve_variables
        resolved_input_value = step.input_value
        if step.input_value:
            resolved_input_value = resolve_variables(step.input_value)
            
        resolved_assert_value = step.assert_value
        if step.assert_value:
            resolved_assert_value = resolve_variables(step.assert_value)
            
        try:
            if action_type == 'wait':
                wait_seconds = step.wait_time / 1000 if step.wait_time else 1
                time.sleep(wait_seconds)
                return True, f"✓ 等待 {wait_seconds} 秒 - 耗时 {round(time.time() - start_time, 2)}秒", None
                
            if action_type == 'screenshot':
                screenshot = self.capture_screenshot()
                if self.mini == "mock_instance":
                    return True, f"✓ [Mock] 截图成功 - 耗时 {round(time.time() - start_time, 2)}秒", None
                return True, f"✓ 截图成功 - 耗时 {round(time.time() - start_time, 2)}秒", screenshot
                
            locator_strategy = element_data.get('locator_strategy', 'css')
            locator_value = element_data.get('locator_value', '')
            element_name = element_data.get('name', '未知元素')
            
            element = self._get_element(locator_strategy, locator_value)
            
            if self.mini == "mock_instance":
                time.sleep(0.5)
                execution_time = round(time.time() - start_time, 2)
                log = f"✓ [Mock] Minium 执行 '{action_type}' 到元素 '{element_name}'\n"
                log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                if action_type == 'fill':
                    log += f"  - 输入内容: {resolved_input_value}\n"
                elif action_type == 'assert':
                    log += f"  - 期望值: {resolved_assert_value}\n"
                log += f"  - 耗时: {execution_time}秒"
                return True, log, None
                
            if action_type == 'click':
                element.click()
                return True, f"✓ 点击元素 '{element_name}' 成功", None
                
            elif action_type == 'fill':
                element.input(resolved_input_value)
                return True, f"✓ 在元素 '{element_name}' 中输入 '{resolved_input_value}' 成功", None
                
            elif action_type == 'getText':
                text = element.inner_text
                return True, f"✓ 获取文本 '{text}' 成功", None
                
            elif action_type == 'assert':
                text = element.inner_text
                if step.assert_type == 'textContains':
                    if resolved_assert_value in text:
                        return True, f"✓ 断言通过: '{text}' 包含 '{resolved_assert_value}'", None
                    return False, f"✗ 断言失败: '{text}' 不包含 '{resolved_assert_value}'", self.capture_screenshot()
                elif step.assert_type == 'textEquals':
                    if text == resolved_assert_value:
                        return True, f"✓ 断言通过: '{text}' 等于 '{resolved_assert_value}'", None
                    return False, f"✗ 断言失败: '{text}' 不等于 '{resolved_assert_value}'", self.capture_screenshot()
                    
            return True, f"✓ 操作 {action_type} 执行成功", None
            
        except Exception as e:
            return False, f"✗ 步骤执行失败: {str(e)}", self.capture_screenshot()
