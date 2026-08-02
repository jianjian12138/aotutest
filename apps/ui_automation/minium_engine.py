import time
import base64
import logging

logger = logging.getLogger(__name__)


class MiniumNotAvailableError(RuntimeError):
    """微信小程序测试环境未就绪。

    第六轮批次2整改：此前当 minium 库未安装或微信开发者工具未配置时，
    引擎会静默降级为 "mock_instance"，随后所有步骤一律返回 True 与
    "✓ [Mock] ..." 日志——用户在平台上看到小程序用例"全部通过"，
    实际一个动作都没有执行。这属于伪造执行结果，已按整改要求移除。
    现在环境未就绪时直接抛出本异常，由上层记为执行失败并返回 501。
    """


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
        """启动Minium及微信开发者工具。环境未就绪时抛 MiniumNotAvailableError（不降级为假执行）。"""
        try:
            import minium
        except ImportError:
            raise MiniumNotAvailableError(
                "未安装 minium 库，无法执行真实的微信小程序测试。"
                "请在执行机上安装：pip install minium。"
                "（本平台不会以模拟结果冒充真实执行）"
            )

        logger.info("正在启动微信小程序测试引擎 (Minium)...")
        try:
            self.mini = minium.Minium(
                project_path=self.project_path,
                dev_tool_path=self.dev_tool_path
            )
        except Exception as e:
            logger.error("Minium 启动失败（开发者工具未安装或配置错误）: %s", e)
            raise MiniumNotAvailableError(
                f"微信开发者工具未就绪，无法执行真实的小程序测试：{e}。"
                "请检查 project_path / dev_tool_path 配置及开发者工具的服务端口设置。"
                "（本平台不会以模拟结果冒充真实执行）"
            )
        logger.info("✓ Minium 引擎启动成功")

    def stop(self):
        """关闭小程序工具"""
        if self.mini:
            try:
                self.mini.release()
                logger.info("Minium 引擎已释放")
            except Exception as e:
                logger.error(f"关闭Minium失败: {str(e)}")

    def navigate(self, url):
        """
        小程序页面导航 (对应 urlJump 或者直接配置打开的page)
        """
        try:
            if not url.startswith('/'):
                url = '/' + url
            self.mini.app.redirect_to(url)
            return True, f"✓ 跳转到小程序页面: {url}"
        except Exception as e:
            return False, f"✗ 小程序页面跳转失败: {str(e)}"

    def capture_screenshot(self):
        """捕获错误截图"""
        if not self.mini:
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
        if not self.mini:
            raise MiniumNotAvailableError("Minium 引擎未启动，无法定位小程序元素")
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
                # audit: real-impl wait 动作的真实等待，时长来自用例配置 step.wait_time
                time.sleep(wait_seconds)
                return True, f"✓ 等待 {wait_seconds} 秒 - 耗时 {round(time.time() - start_time, 2)}秒", None
                
            if action_type == 'screenshot':
                screenshot = self.capture_screenshot()
                return True, f"✓ 截图成功 - 耗时 {round(time.time() - start_time, 2)}秒", screenshot

            locator_strategy = element_data.get('locator_strategy', 'css')
            locator_value = element_data.get('locator_value', '')
            element_name = element_data.get('name', '未知元素')

            element = self._get_element(locator_strategy, locator_value)

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
