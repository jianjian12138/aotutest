import logging
logger = logging.getLogger('django')

import os
# 禁用 browser-use 遥测
os.environ['ANONYMIZED_TELEMETRY'] = 'false'

import asyncio
import functools
import json
import re
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# 加载环境变量
load_dotenv()

# ============================================================================
# PART 1: Common Patches (Pydantic, ActionModel, TokenCost, Basic Connection)
# ============================================================================

# Patch ChatOpenAI to allow setting attributes (required for browser-use token counting)
try:
    from pydantic import ConfigDict
    if hasattr(ChatOpenAI, 'model_config'):
        if isinstance(ChatOpenAI.model_config, dict):
            ChatOpenAI.model_config['extra'] = 'allow'
        else:
            ChatOpenAI.model_config = ConfigDict(extra='allow', arbitrary_types_allowed=True)
    else:
        ChatOpenAI.model_config = ConfigDict(extra='allow', arbitrary_types_allowed=True)
except ImportError:
    if hasattr(ChatOpenAI, 'model_config'):
        ChatOpenAI.model_config['extra'] = 'allow'

# 修改 ActionModel 配置以允许额外字段
try:
    from browser_use.tools.registry.views import ActionModel
    from pydantic import ConfigDict
    ActionModel.model_config = ConfigDict(arbitrary_types_allowed=True, extra='allow')
    logger.info("✅ Modified ActionModel.model_config to allow extra fields")
except Exception as e:
    logger.warning(f"⚠️ Failed to modify ActionModel config: {e}")

# Patch Agent.get_model_output 方法 - 已禁用，使用 browser-use 原生逻辑
# try:
#     from browser_use.agent.service import Agent
#     from browser_use.agent.message_manager.service import AgentOutput
#     import json as json_module
#
#     _original_get_model_output = Agent.get_model_output
#     
#     # ... (此处省略被注释的代码)
#     
#     # Agent.get_model_output = _patched_get_model_output
#     logger.info("ℹ️ Using native Agent.get_model_output")
# except Exception as e:
#     logger.error(f"❌ Failed to patch Agent.get_model_output: {e}")

# Patch TokenCost
try:
    from browser_use.tokens.service import TokenCost
    from langchain_core.messages import HumanMessage, SystemMessage as LangChainSystemMessage, AIMessage

    def _patched_register_llm(self, llm):
        """修补后的 register_llm，修复 langchain 兼容性"""
        instance_id = str(id(llm))
        if instance_id in self.registered_llms:
            return llm
        
        self.registered_llms[instance_id] = llm
        _original_ainvoke = llm.ainvoke
        _token_service = self
        
        async def _fixed_tracked_ainvoke(messages, output_format=None, **kwargs):
            # Sanitize message contents
            def _content_to_str(content):
                if isinstance(content, str): return content
                if isinstance(content, list):
                    parts = []
                    for item in content:
                        if isinstance(item, str): parts.append(item)
                        elif isinstance(item, dict):
                            if 'text' in item: parts.append(str(item['text']))
                            elif 'image' in item or 'image_url' in item: parts.append("[image]")
                        else: parts.append(str(item))
                    return "\n".join(parts)
                if isinstance(content, dict):
                    if 'text' in content: return str(content['text'])
                    if 'content' in content: return str(content['content'])
                    if 'image' in content or 'image_url' in content: return "[image]"
                return str(content)

            def _sanitize_message(msg):
                msg_type_name = type(msg).__name__
                content = getattr(msg, 'content', msg)
                content_str = _content_to_str(content)
                if msg_type_name == 'SystemMessage': return LangChainSystemMessage(content=content_str)
                if msg_type_name in ('HumanMessage', 'UserMessage'): return HumanMessage(content=content_str)
                if msg_type_name == 'AIMessage': return AIMessage(content=content_str)
                if isinstance(msg, (HumanMessage, LangChainSystemMessage, AIMessage)): return type(msg)(content=content_str)
                return HumanMessage(content=str(content_str))

            sanitized_messages = [_sanitize_message(m) for m in messages]
            
            output_format = kwargs.pop('output_format', None)
            if output_format:
                kwargs['response_format'] = {"type": "json_object"}
                
            # Add retry logic for LLM invocation
            max_retries = 2  # 重试次数为2次
            last_exception = None
            for attempt in range(max_retries):
                try:
                    result = await _original_ainvoke(sanitized_messages, **kwargs)
                    break
                except Exception as e:
                    last_exception = e
                    if "response_format" in str(e):
                        kwargs.pop('response_format', None)
                        # retry immediately without response_format
                        continue

                    logger.warning(f"⚠️ LLM ainvoke failed (attempt {attempt+1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.5)  # 等待0.5秒
            else:
                logger.error(f"❌ LLM ainvoke failed after {max_retries} attempts.")
                raise last_exception

            # Enhance response parsing
            import json as json_module
            clean_content = result.content.strip() if hasattr(result, 'content') else str(result).strip()
            
            # DEBUG LOGGING
            if len(clean_content) > 500:
                logger.warning(f"🔍 Raw LLM Output (first 500 chars): {clean_content[:500]}...")
            else:
                logger.warning(f"🔍 Raw LLM Output: {clean_content}")

            # Remove Markdown
            if '```' in clean_content:
                # 尝试更鲁棒的正则匹配
                match = re.search(r'```(?:json)?\s*(\{[\s\S]*\})\s*```', clean_content)
                if match: 
                    clean_content = match.group(1).strip()
                else:
                    clean_content = re.sub(r'```[a-z]*', '', clean_content).replace('```', '').strip()

            # DEBUG LOGGING TO FILE
            try:
                with open(r'd:\TEST\llm_debug.txt', 'a', encoding='utf-8') as f:
                    from datetime import datetime
                    f.write(f"\n\n--- LLM RESPONSE ({datetime.now()}) ---\n")
                    f.write(clean_content)
                    f.write("\n-----------------------------------\n")
            except: pass

            parsed_data = None
            try:
                parsed_data = json_module.loads(clean_content)
            except:
                try:
                    # 尝试查找最外层 JSON 对象 (贪婪匹配)
                    match = re.search(r'(\{[\s\S]*\})', clean_content)
                    if match: parsed_data = json_module.loads(match.group(1))
                except:
                    pass
            
            # Fallback for parsing failure
            if not parsed_data:
                logger.error("❌ Failed to parse LLM response as JSON")
                # Create a fake 'thinking' action to show the error in UI
                parsed_data = {
                    "thinking": f"Failed to parse JSON. Raw output: {clean_content[:200]}...",
                    "action": []
                }
            
            # 关键修复: 处理 action 为单个字典的情况 (LLM 常见错误)
            if 'action' in parsed_data:
                if isinstance(parsed_data['action'], dict):
                    parsed_data['action'] = [parsed_data['action']]
                elif parsed_data['action'] is None:
                    parsed_data['action'] = []

            # Wrapper classes
            class _ActionWrapper:
                def __init__(self, action_dict):
                    self._dict = {}
                    for k, v in action_dict.items():
                        if isinstance(v, dict):
                            norm = {}
                            for subk, subv in v.items():
                                if subk == 'element_index': norm['index'] = subv
                                else: norm[subk] = subv
                            self._dict[k] = norm
                        else: self._dict[k] = v
                    for k, v in self._dict.items(): setattr(self, k, v)
                def model_dump(self, **kwargs): return self._dict
                def get_index(self):
                    for v in self._dict.values():
                        if isinstance(v, dict) and 'index' in v: return v['index']
                    return None
            
            # Construct AgentOutput manually
            agent_output = None
            if parsed_data and 'action' in parsed_data:
                # Normalize actions
                normalized_actions = []
                for action_dict in parsed_data['action']:
                    normalized_action = {}
                    for action_name, action_params in action_dict.items():
                        if isinstance(action_params, dict):
                            normalized_params = {}
                            for k, v in action_params.items():
                                if k == 'element_index': normalized_params['index'] = v
                                else: normalized_params[k] = v
                            normalized_action[action_name] = normalized_params
                        else:
                            normalized_action[action_name] = action_params
                    normalized_actions.append(normalized_action)
                parsed_data['action'] = normalized_actions

                try:
                    from browser_use.agent.message_manager.service import AgentOutput
                    agent_output = AgentOutput.model_construct(
                        thinking=parsed_data.get('thinking'),
                        evaluation_previous_goal=parsed_data.get('evaluation_previous_goal'),
                        memory=parsed_data.get('memory'),
                        next_goal=parsed_data.get('next_goal'),
                        action=[]
                    )
                    action_list = []
                    for action_dict in parsed_data.get('action', []):
                        action_list.append(_ActionWrapper(action_dict))
                    object.__setattr__(agent_output, 'action', action_list)
                except Exception as e:
                    logger.error(f"🔧 Failed to create AgentOutput: {e}")

            class _ResponseWrapper:
                def __init__(self, orig, completion_obj, clean_content=None):
                    self._orig = orig
                    self.content = clean_content if clean_content is not None else getattr(orig, 'content', '')
                    self.response_metadata = getattr(orig, 'response_metadata', {})
                    self.completion = completion_obj
                    usage = getattr(orig, 'usage', None) or (orig.response_metadata.get('token_usage') if hasattr(orig, 'response_metadata') else None)
                    if not usage: usage = {}
                    # Fix usage
                    usage = dict(usage) if hasattr(usage, '__dict__') else usage
                    usage.setdefault('prompt_tokens', 0)
                    usage.setdefault('completion_tokens', 0)
                    usage.setdefault('total_tokens', 0)
                    self.usage = usage
                def __getattr__(self, name): return getattr(self._orig, name)

            wrapped = _ResponseWrapper(result, agent_output, clean_content=clean_content)
            if hasattr(wrapped, 'usage') and wrapped.usage:
                try: _token_service.add_usage(llm.model, wrapped.usage)
                except: pass
            
            return wrapped
        
        setattr(llm, 'ainvoke', _fixed_tracked_ainvoke)
        return llm
    
    TokenCost.register_llm = _patched_register_llm
    logger.info("✅ Successfully patched TokenCost.register_llm")
except Exception as e:
    logger.error(f"❌ Failed to patch TokenCost: {e}")

# Patch BrowserSession.connect (Windows CDP fix)
try:
    from browser_use.browser.session import BrowserSession
    import httpx
    
    _original_connect = BrowserSession.connect
    
    async def _patched_connect(self, cdp_url=None):
        if cdp_url: return await _original_connect(self, cdp_url=cdp_url)
        
        browser_profile = getattr(self, 'browser_profile', None)
        if hasattr(browser_profile, 'cdp_url') and browser_profile.cdp_url:
            return await _original_connect(self, cdp_url=browser_profile.cdp_url)
        
        port = 9222
        if hasattr(browser_profile, 'extra_chromium_args'):
            for arg in browser_profile.extra_chromium_args:
                if '--remote-debugging-port=' in str(arg):
                    try: port = int(arg.split('=')[1]); break
                    except: pass
        if hasattr(browser_profile, 'remote_debugging_port'):
            port = browser_profile.remote_debugging_port
            
        cdp_endpoint = f"http://localhost:{port}/json/version"
        
        for attempt in range(5):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(cdp_endpoint)
                    if response.status_code == 200 and response.text:
                        version_info = response.json()
                        browser_profile.cdp_url = version_info['webSocketDebuggerUrl']
                        return await _original_connect(self, cdp_url=browser_profile.cdp_url)
            except Exception:
                if attempt < 4: await asyncio.sleep(1.0)
        
        return await _original_connect(self, cdp_url=cdp_url)
    
    BrowserSession.connect = _patched_connect
    logger.info("✅ Successfully patched BrowserSession.connect")
except Exception as e:
    logger.error(f"❌ Failed to patch BrowserSession.connect: {e}")

# Patch ClickElementAction parameters
try:
    from browser_use.tools.views import ClickElementAction
    _original_click_init = ClickElementAction.__init__
    def _patched_click_init(self, **kwargs):
        fixed_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, int) and key not in ['index']:
                fixed_kwargs['index'] = value
            else:
                fixed_kwargs[key] = value
        if len(kwargs) == 1:
            key, value = list(kwargs.items())[0]
            if isinstance(value, int) and key != 'index':
                fixed_kwargs = {'index': value}
        try:
            return _original_click_init(self, **fixed_kwargs)
        except TypeError:
            if fixed_kwargs and isinstance(list(fixed_kwargs.values())[0], int):
                return _original_click_init(self, **{'index': list(fixed_kwargs.values())[0]})
            raise
    ClickElementAction.__init__ = _patched_click_init
except Exception:
    pass

# Patch ToolRegistry
try:
    from browser_use.tools.registry.service import Registry as ToolRegistry
    # Force patch Registry class
    _original_execute_action = ToolRegistry.execute_action
    
    async def _patched_execute_action(self, action_name: str, params: dict, **kwargs):
        # 自动映射 switch_tab -> switch (强制映射)
        if action_name == 'switch_tab':
            logger.info(f"🔧 Force aliasing: switch_tab -> switch")
            action_name = 'switch'
        
        if isinstance(params, int):
            params = {'index': params}
        elif not isinstance(params, dict) and params is not None:
            # 针对 switch_tab 可能是纯字符串的情况
            if action_name in ['switch_tab', 'switch']:
                params = {'tab_id': params}
            else:
                params = {'value': params} if params else {}
        
        # 针对点击增加延迟，确保 UI 更新 (如弹窗弹出、下拉框展开)
        if action_name in ['click_element', 'click']:
            result = await _original_execute_action(self, action_name, params, **kwargs)
            # 增加延迟到 1.5s，并强制在点击后等待浏览器渲染
            # 尤其是对于 element-plus 等 UI 框架，下拉列表渲染需要时间
            await asyncio.sleep(1.5)
            return result
            
        return await _original_execute_action(self, action_name, params, **kwargs)
        
    ToolRegistry.execute_action = _patched_execute_action
    logger.info("✅ Successfully patched ToolRegistry.execute_action with alias support")
except Exception as e:
    logger.error(f"❌ Failed to patch ToolRegistry: {e}")

# Patch ScreenshotWatchdog GLOBALLY to fix timeouts
try:
    from browser_use.browser.watchdogs.screenshot_watchdog import ScreenshotWatchdog
    
    _original_on_screenshot_event = ScreenshotWatchdog.on_ScreenshotEvent
    
    # Check if already patched to avoid double patching
    if not getattr(_original_on_screenshot_event, '_is_patched_global', False):
        async def on_ScreenshotEvent(self, event):
            """
            Patched screenshot event handler with increased timeout and optimized parameters.
            """
            try:
                # Try original method first with strict timeout
                result = await asyncio.wait_for(
                    _original_on_screenshot_event(self, event),
                    timeout=3.0 # Reduced for fail-fast
                )
                return result
            except asyncio.TimeoutError:
                logger.warning(f"DEBUG: Watchdog timeout (3s), trying optimized approach...")
                try:
                    # Get CDP session
                    cdp_session = await self.browser_session.get_or_create_cdp_session(target_id=None)
                    if not cdp_session: raise Exception("Failed to get CDP session")
                    
                    params = {'format': 'png', 'quality': 50, 'from_surface': True, 'capture_beyond_viewport': False}
                    
                    # One quick retry
                    result = await asyncio.wait_for(
                        cdp_session.cdp_client.send.Page.captureScreenshot(params=params, session_id=cdp_session.session_id),
                        timeout=3.0
                    )
                    return result
                
                except Exception as ex:
                    # In Text Mode especially, we don't want to die on screenshot
                    logger.warning(f"DEBUG: Screenshot failed optimized, returning placeholder: {ex}")
                    import base64
                    # 1x1 transparent pixel
                    placeholder = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==')
                    return {'data': placeholder}
            except Exception as e:
                logger.error(f"DEBUG: Screenshot unexpected error: {e}")
                import base64
                placeholder = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==')
                return {'data': placeholder}
        
        on_ScreenshotEvent._is_patched_global = True
        ScreenshotWatchdog.on_ScreenshotEvent = on_ScreenshotEvent
        logger.info("✅ Applied Global ScreenshotWatchdog Patch")

    # Patch DOMWatchdog
    from browser_use.browser.watchdogs.dom_watchdog import DOMWatchdog
    
    _original_capture_clean_screenshot = DOMWatchdog._capture_clean_screenshot
    
    if not getattr(_original_capture_clean_screenshot, '_is_patched_global', False):
        async def _capture_clean_screenshot(self):
            try:
                # Very short timeout for DOM clean screenshot checks
                return await asyncio.wait_for(_original_capture_clean_screenshot(self), timeout=3.0)
            except Exception as e:
                logger.warning(f"DEBUG: Clean screenshot failed/timed out: {e}, continuing...")
                return None
                
        _capture_clean_screenshot._is_patched_global = True
        DOMWatchdog._capture_clean_screenshot = _capture_clean_screenshot
        logger.info("✅ Applied Global DOMWatchdog Patch")

except Exception as e:
    logger.error(f"❌ Failed to apply Global Watchdog patches: {e}")

# Patch Agent verdict
try:
    from browser_use.agent.service import Agent
    from browser_use.agent.message_manager.service import AgentOutput
    
    _original_judge_and_log = Agent._judge_and_log
    
    def _agent_output_getattr(self, name):
        if name == 'verdict':
            if hasattr(self, 'next_goal') and self.next_goal:
                if any(w in str(self.next_goal).lower() for w in ['complete', 'done', 'finished', 'success']): return True
            if hasattr(self, 'evaluation_previous_goal') and self.evaluation_previous_goal:
                if any(w in str(self.evaluation_previous_goal).lower() for w in ['success', 'complete']): return True
            return False
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
    
    if not hasattr(AgentOutput, '__getattr__'):
        AgentOutput.__getattr__ = _agent_output_getattr
        
    async def _patched_judge_and_log(self):
        try:
            return await _original_judge_and_log(self)
        except AttributeError as e:
            if 'verdict' in str(e):
                return None
            raise
    Agent._judge_and_log = _patched_judge_and_log
except Exception:
    pass


# ============================================================================
# PART 2: Helper Classes
# ============================================================================

from langchain_core.callbacks import BaseCallbackHandler
from typing import Any

class RawResponseLogger(BaseCallbackHandler):
    def on_llm_new_token(self, token: str, **kwargs: Any) -> Any: pass
    def on_llm_end(self, response: Any, **kwargs: Any) -> Any:
        try:
            generation = response.generations[0][0]
            logger.info(f"DEBUG: Raw LLM Response: {generation.text}")
        except: pass


# ============================================================================
# PART 3: Base Browser Agent
# ============================================================================

try:
    from browser_use import Agent, Controller
    from browser_use.browser.profile import BrowserProfile
except ImportError:
    # Define placeholder classes if browser_use is not installed
    # This prevents ModuleNotFoundError when importing BaseBrowserAgent for mobile tests
    class Agent:
        def __init__(self, *args, **kwargs):
            pass
        async def run(self, *args, **kwargs):
            import sys
            py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
            
            if sys.version_info < (3, 11):
                error_msg = (
                    f"❌ Python {py_version} detected. 'browser-use' requires Python 3.11+.\n"
                    "Please upgrade Python to use Web AI Testing features.\n"
                    "Download: https://www.python.org/downloads/"
                )
            else:
                error_msg = (
                    "❌ 'browser-use' dependency is missing.\n"
                    "Please install it: pip install browser-use playwright\n"
                    "Then run: playwright install"
                )
            
            logger.error(error_msg)
            
            # Try to send error to UI via callback
            callback = kwargs.get('on_step_end') or kwargs.get('callback')
            if callback:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback({'type': 'log', 'content': f"\n{error_msg}\n"})
                    else:
                        callback({'type': 'log', 'content': f"\n{error_msg}\n"})
                except:
                    pass
                    
            # Return a structure that resembles history but indicates failure
            class FakeHistory:
                def __init__(self):
                    self.steps = []
            return FakeHistory()

    class Controller:
        def action(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator

    class BrowserProfile:
        def __init__(self, *args, **kwargs):
            pass
    import logging
    logger = logging.getLogger('django')
    logger.warning("⚠️ 'browser_use' module not found. Web AI features will not work.")

class BaseBrowserAgent:
    def __init__(self, execution_mode='text', enable_gif=True, case_name=None, model_config_id=None, browser_type='chrome'):
        self.execution_mode = 'text'
        self.enable_gif = enable_gif  # GIF录制开关
        self.case_name = case_name or "Adhoc Task"  # 用例名称
        self.browser_type = browser_type
        
        # Load Config from DB
        from apps.requirement_analysis.models import AIModelConfig
        
        config_obj = None
        if model_config_id:
            try:
                config_obj = AIModelConfig.objects.get(id=model_config_id)
            except AIModelConfig.DoesNotExist:
                logger.warning(f"Provided model_config_id {model_config_id} not found")
        
        if not config_obj:
            # Fallback to default
            role_name = 'browser_use_text'
            config_obj = AIModelConfig.objects.filter(role=role_name, is_active=True).first()
        
        model_config = {}
        if config_obj:
            model_config = {
                'api_key': config_obj.api_key,
                'base_url': config_obj.base_url,
                'model_name': config_obj.model_name,
                'provider': config_obj.model_type
            }
        
        self.api_key = model_config.get('api_key') or os.getenv('AUTH_TOKEN')
        self.base_url = model_config.get('base_url') or os.getenv('BASE_URL')
        self.model_name = model_config.get('model_name') or os.getenv('MODEL_NAME')
        self.provider = model_config.get('provider', 'openai')
        
        if not self.api_key:
            raise ValueError(f"No API Key found for mode: {execution_mode}")

        self.llm = ChatOpenAI(
            model=self.model_name,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=0.0,
            callbacks=[RawResponseLogger()]
        )
        
        # browser-use requirement
        try:
            object.__setattr__(self.llm, 'provider', self.provider)
            object.__setattr__(self.llm, 'model', self.model_name)
        except:
            if not hasattr(self.llm, '__pydantic_extra__') or self.llm.__pydantic_extra__ is None:
                self.llm.__pydantic_extra__ = {}
            self.llm.__pydantic_extra__['provider'] = self.provider
            self.llm.__pydantic_extra__['model'] = self.model_name
            
    def _format_action(self, action):
        try:
            # 尝试多种方式获取字典
            action_dict = {}
            if hasattr(action, 'model_dump'): 
                # Pydantic v2
                action_dict = action.model_dump(exclude_none=True)
            elif hasattr(action, 'dict'): 
                # Pydantic v1
                action_dict = action.dict(exclude_none=True)
            elif hasattr(action, '_action_dict'): 
                action_dict = action._action_dict
            elif hasattr(action, '_dict'): 
                action_dict = action._dict
            elif isinstance(action, dict): 
                action_dict = action
            else: 
                return str(action)

            if not action_dict: return "待机"

            descriptions = []
            for name, params in action_dict.items():
                if params is None and name not in ['scroll_down', 'scroll_up', 'done']: continue
                
                # 兼容 params 为空字典的情况
                if isinstance(params, dict) and not params and name not in ['scroll_down', 'scroll_up', 'done']: continue

                if name in ['go_to_url', 'navigate']:
                    url = params.get('url') if isinstance(params, dict) else params
                    descriptions.append(f"访问: {url}")
                elif name in ['click_element', 'click']:
                    index = params.get('index') if isinstance(params, dict) else params
                    descriptions.append(f"点击[{index}]")
                elif name in ['input_text', 'input']:
                    text = params.get('text') if isinstance(params, dict) else None
                    descriptions.append(f"输入: '{text}'")
                elif name == 'switch_tab':
                    index = params.get('index', params)
                    descriptions.append(f"切换标签 {index}")
                elif name == 'open_new_tab':
                    url = params.get('url', params)
                    descriptions.append(f"新标签打开: {url}")
                elif name == 'done':
                    text = params.get('text') if isinstance(params, dict) else ""
                    descriptions.append(f"任务完成: {text}")
                elif name == 'mark_task_complete':
                    task_id = params.get('task_id') if isinstance(params, dict) else params
                    descriptions.append(f"标记完成: 任务{task_id}")
                else:
                    # 格式化其他操作
                    param_str = ""
                    if isinstance(params, dict):
                        param_str = ", ".join([f"{k}={v}" for k, v in params.items()])
                    elif params:
                        param_str = str(params)
                    
                    if param_str:
                        descriptions.append(f"{name}({param_str})")
                    else:
                        descriptions.append(f"{name}")
            
            if not descriptions:
                return "操作(解析为空)"
                
            return " | ".join(descriptions)
        except Exception as e:
            logger.error(f"Error formatting action: {e}")
            return f"执行操作(格式化错误)"

    async def analyze_task(self, task_description: str):
        steps = []
        try:
            # 1. 尝试使用 LLM 进行智能拆解
            prompt = (
                f"Break down this test task into sequential executable steps.\n"
                f"Task: {task_description}\n"
                f"Output: A raw JSON list of strings. No markdown, no code blocks. Just the JSON array.\n"
                f"Example: [\"Open https://example.com\", \"Click 'Login'\", \"Enter username\"]\n"
                f"Note: If the input already has numbered steps (like '1. xxx 2. xxx'), preserve them as separate items."
            )
            response = await self.llm.ainvoke(prompt)
            content = response.content.strip() if hasattr(response, 'content') else str(response)
            
            # 清理 Markdown
            content = re.sub(r'^```json\s*', '', content)
            content = re.sub(r'^```\s*', '', content)
            content = re.sub(r'\s*```$', '', content)
            
            try:
                import json
                # 尝试查找 JSON 数组
                match = re.search(r'\[.*\]', content, re.DOTALL)
                if match:
                    steps = json.loads(match.group(0))
            except Exception as e:
                logger.warning(f"Failed to parse LLM steps: {e}")
        except Exception as e:
            logger.warning(f"LLM analysis failed: {e}")
            
        # 2. 如果 LLM 失败或只返回了 1 个步骤（可能是解析错了），尝试基于文本特征的启发式拆解
        if not steps or len(steps) <= 1:
            raw_steps = steps[0] if steps else task_description
            
            # 尝试按换行符分割
            lines = [s.strip() for s in raw_steps.split('\n') if s.strip()]
            
            # 如果按换行符分割后仍只有 1 行，尝试按数字编号分割
            if len(lines) <= 1:
                text = lines[0] if lines else task_description
                # 匹配 "1. ", "2. ", "3. " 或 "1、", "2、" 等
                # 使用正向预查 split
                import re as regex_module
                # 正则解释：匹配 (行首或空白) + 数字 + (点/顿号/冒号)
                parts = regex_module.split(r'(?:^|\s+)\d+[.、:：]\s*', text)
                lines = [p.strip() for p in parts if p.strip()]
            
            if len(lines) > 0:
                steps = lines
            
        # 兜底：如果还是空的，直接用原文本
        if not steps:
            steps = [task_description]
            
        # 彻底清理生成的步骤描述中的重复编号
        cleaned_steps = []
        for s in steps:
            desc = s
            # 移除开头可能的编号 (支持 1. 1、 1: 等)
            while True:
                match = re.match(r'^\s*\d+[\.\s、:：]+(.*)', desc)
                if not match: break
                desc = match.group(1).strip()
            if desc:
                cleaned_steps.append(desc)
        
        # 强制步骤拆分：确保步骤是列表格式
        if isinstance(cleaned_steps, str):
            cleaned_steps = [cleaned_steps]
            
        return [{'id': i+1, 'description': s, 'status': 'pending'} for i, s in enumerate(cleaned_steps)]

    def _create_browser_profile(self):
        # Default implementation, can be overridden
        chrome_path = None
        import platform

        system = platform.system()
        
        # 定义不同浏览器的路径查找逻辑
        browser_paths = {
            'chrome': {
                'Windows': [
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                    os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
                ],
                'Linux': [
                    '/usr/bin/google-chrome',
                    '/usr/bin/google-chrome-stable',
                    '/opt/google/chrome/chrome',
                ],
                'Darwin': [ # macOS
                     '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
                ]
            },
            'edge': {
                 'Windows': [
                    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                    os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\Application\msedge.exe")
                 ],
                 'Linux': [
                     '/usr/bin/microsoft-edge',
                     '/usr/bin/microsoft-edge-stable'
                 ],
                 'Darwin': [
                     '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge'
                 ]
            }
        }
        
        # 默认回退到 Chromium
        browser_paths['chromium'] = {
            'Linux': ['/usr/bin/chromium', '/usr/bin/chromium-browser', '/snap/bin/chromium']
        }

        # 根据 browser_type 查找路径
        target_browser = self.browser_type if self.browser_type in browser_paths else 'chrome'
        paths = browser_paths.get(target_browser, {}).get(system, [])
        
        # 如果是 Linux 且没找到 Chrome，尝试 Chromium
        if system == 'Linux' and target_browser == 'chrome' and not any(os.path.exists(p) for p in paths):
             paths.extend(browser_paths['chromium']['Linux'])

        for p in paths:
            if os.path.exists(p):
                chrome_path = p
                break
        
        logger.info(f"Using browser: {target_browser}, path: {chrome_path}")

        # 基础性能优化参数
        extra_args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-infobars', '--disable-notifications',
            '--disable-background-networking',
            '--disable-background-timer-throttling',
            '--disable-renderer-backgrounding',
            '--disable-backgrounding-occluded-windows',
            '--disable-extensions',
            '--disable-web-security',  # 允许跨域请求
        ]

        # 根据操作系统添加特定参数
        if system == 'Linux':
            # Linux 服务器环境（特别是无头环境）必需的参数
            extra_args.extend([
                '--no-sandbox',                    # Linux 必需：禁用沙箱
                '--disable-setuid-sandbox',        # Linux 必需：禁用 setuid 沙箱
                '--disable-dev-shm-usage',         # Linux 必需：使用 /tmp 而不是 /dev/shm
                '--disable-gpu',                   # 禁用 GPU 加速（服务器通常无 GPU）
                '--headless=new',                  # Linux 服务器使用无头模式
                '--disable-software-rasterizer',   # 禁用软件光栅化器
                '--remote-debugging-port=0',       # 使用随机可用端口
            ])
        else:
            # macOS 和 Windows 使用显示模式
            extra_args.extend([
                '--no-sandbox',                    # 兼容性
                '--disable-gpu',
                '--remote-debugging-port=9222',
            ])

        return BrowserProfile(
            headless=(system == 'Linux'),  # Linux 使用无头模式，其他系统使用显示模式
            disable_security=True,
            executable_path=chrome_path,
            args=extra_args,
            wait_for_network_idle_page_load_time=0.2,
            minimum_wait_page_load_time=0.05,
            wait_between_actions=0.1,
            enable_default_extensions=False
        )

    async def run_task(self, task_description: str, planned_tasks=None, callback=None, should_stop=None):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
            
        # 强制发送一条测试日志
        if callback:
            init_msg = {'type': 'log', 'content': f"\n正在初始化浏览器... (Browser: {self.browser_type})\n"}
            if asyncio.iscoroutinefunction(callback):
                await callback(init_msg)
            else:
                callback(init_msg)

        controller = Controller()
        _task_was_done = False
        
        # Shared state for task tracking
        state = {'last_marked_task_id': 0}

        @controller.action('Done')
        async def done(success: bool = True, text: str = ""):
            nonlocal _task_was_done
            
            # Smart check: If there are planned tasks, verify if all are marked complete
            if planned_tasks and state['last_marked_task_id'] < len(planned_tasks):
                pending_count = len(planned_tasks) - state['last_marked_task_id']
                logger.warning(f"🚫 Agent tried to call Done() but {pending_count} tasks are pending. Rejecting.")
                return f"⚠️ REJECTED: You have {pending_count} pending tasks to complete. You MUST execute task {state['last_marked_task_id'] + 1} now. Do not call Done() until all tasks are marked complete."

            _task_was_done = True
            return f"Finished: {text}"

        @controller.action('mark_task_complete')
        async def mark_task_complete(task_id: int):
            logger.info(f"✅ Explicitly marking task {task_id} as completed")
            if callback:
                try:
                    data = {'task_id': int(task_id), 'status': 'completed'}
                    if asyncio.iscoroutinefunction(callback):
                        await callback(data)
                    else:
                        callback(data)
                    
                    # Update state
                    if int(task_id) > state['last_marked_task_id']:
                        state['last_marked_task_id'] = int(task_id)
                        
                except Exception as e:
                    logger.warning(f"Failed to execute mark_task_complete callback: {e}")
            return f"Task {task_id} marked completed"

        # 构建强化版 Prompt
        final_task = task_description
        if planned_tasks:
            final_task += "\n\nIMPORTANT INSTRUCTION:\n"
            final_task += "You have a list of sub-tasks. Execute strictly in order.\n"
            final_task += "CRITICAL: Call 'mark_task_complete(task_id=...)' when you confirm a sub-task is done.\n"
            final_task += "IMPORTANT: If a sub-task (like opening a URL) is already fulfilled by the initial state, YOU MUST mark it complete in your VERY FIRST STEP.\n"
            final_task += "CRITICAL RULE: DO NOT STOP until ALL sub-tasks are marked as complete. You must execute them one by one.\n"
            final_task += "Sub-tasks (Execute in order):\n"
            cleaned_tasks = []
            for t in planned_tasks:
                desc = t['description']
                # 递归去除所有层级的重复序号，例如 "1. 1. xxx" -> "xxx"
                while True:
                    match = re.match(r'^\s*\d+[\.\s、:]+(.*)', desc)
                    if not match: break
                    desc = match.group(1).strip()
                cleaned_tasks.append(f"{t['id']}. {desc}")
            final_task += "\n".join(cleaned_tasks)
            
            # 强制将 planned_tasks 注入到 System Message 或 Prompt 的开头，确保 Agent 无法忽略
            final_task = f"GOAL: Execute the following {len(planned_tasks)} tasks one by one:\n" + "\n".join(cleaned_tasks) + "\n\n" + final_task

        # 极限效率版标记指令
        from datetime import datetime
        final_task += f"\n\nCURRENT TIME: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        final_task += "\nCRITICAL PERFORMANCE & SYNC RULES:\n"
        final_task += "1. ACTION-TASK MAPPING: Mark tasks as complete as you finish them. Don't forget.\n"
        final_task += "2. NO JAVASCRIPT IN INPUT: When a task asks for a timestamp, YOU MUST compute the final string yourself (e.g., 'V8.01734892400').\n"
        final_task += "   - DO NOT output 'Date.now()' or '{{...}}' strings. Use the CURRENT TIME provided above to estimate a timestamp.\n"
        final_task += "3. DROPDOWN & MODAL ISOLATION: If an action (clicking a button/dropdown) triggers a UI change (modal opens/dropdown expands), YOU MUST STOP and WAIT for the next step to see the new elements. DO NOT attempt to interact with newly appeared elements (like dropdown options) in the same step as the click that opened them.\n"
        final_task += "4. ULTRALIGHT THINKING: Keep 'thinking' under 10 words. Just list next actions. Merge multiple INPUTS if they are on the same form, but NEVER merge a UI-opening click with its subsequent interaction. SPEED IS CRITICAL - respond as quickly as possible.\n"
        final_task += "5. RETRY LOGIC: If a previous 'save' or 'submit' failed (e.g., error toast), RE-VERIFY all fields. Re-select dropdowns and re-input text to ensure the form is complete. Often errors are caused by missing project selection.\n"
        final_task += "6. DO NOT REPEAT: If a task is complete, mark it and MOVE ON. Don't re-confirm unless the system requires it.\n"
        final_task += "7. VERIFICATION: Task 15/16 usually require checking the list. Ensure you are on the correct page and the new data is visible before marking complete.\n"
        final_task += "8. PERSISTENCE: Continue executing until the entire list of sub-tasks is completed. Do not stop early.\n"
        
        if 'qwen' in self.model_name.lower() or 'deepseek' in self.model_name.lower() or 'glm' in self.model_name.lower():
            final_task += "8. EXTREMELY MINIMIZE output tokens for speed. Keep responses as short as possible while maintaining accuracy. RETURN ONLY RAW JSON. NO MARKDOWN.\n"

        # 核心修复: 清理 task 长文本中的 URL，防止中文标点紧贴 URL 导致 browser-use 解析错误
        # 例如 "http://localhost:3000，" -> "http://localhost:3000 "
        try:
             # 在中文标点前加空格，避免它们成为 URL 的一部分
             final_task = re.sub(r'(https?://[^\s\u4e00-\u9fa5]+?)(?=[，；。、！])', r'\1 ', final_task)
             logger.info(f"🔧 Optimized task description for URL extraction")
        except:
             pass

        browser_profile = self._create_browser_profile()
        
        agent = Agent(
            task=final_task,
            llm=self.llm,
            controller=controller,
            browser_profile=browser_profile,
            use_vision=False,
            max_actions_per_step=10, # 增加步进密度，减少总步骤数，降低超时风险
            max_retries=1, # 减少重试次数以提高速度 (从2改为1)
            max_failures=2, # 减少最大失败次数，避免过长等待 (从默认3改为2)
            llm_timeout=45, # 设置LLM调用超时为45秒
            step_timeout=90, # 设置每步超时为90秒
            generate_gif=self.enable_gif, # 根据开关决定是否生成GIF
        )
        agent._task_was_done = False

        # Callback helper - 添加任务标记跟踪
        last_processed_step = 0
        # REMOVED: last_marked_task_id = 0  <-- Now using state['last_marked_task_id']
        
        async def on_step_end(agent_instance):
            nonlocal last_processed_step
            # Use state['last_marked_task_id'] instead of nonlocal

            if should_stop:
                do_stop = await should_stop() if asyncio.iscoroutinefunction(should_stop) else should_stop()
                if do_stop: raise KeyboardInterrupt("User requested stop")

            if _task_was_done:
                raise KeyboardInterrupt("Done")

            history = getattr(agent_instance, 'history', [])
            if hasattr(history, 'history'): history = history.history

            if len(history) > last_processed_step:
                for i in range(last_processed_step, len(history)):
                    step = history[i]
                    # Log logic here
                    try:
                        actions = []
                        if hasattr(step, 'model_output') and hasattr(step.model_output, 'action'):
                            raw = step.model_output.action
                            actions = raw if isinstance(raw, list) else [raw]

                        # 检查这一步是否调用了mark_task_complete
                        step_has_task_complete = False
                        step_marked_task_id = None
                        for action in actions:
                            action_dict = action.model_dump() if hasattr(action, 'model_dump') else getattr(action, '_action_dict', {})
                            if 'mark_task_complete' in action_dict:
                                step_has_task_complete = True
                                step_marked_task_id = action_dict['mark_task_complete'].get('task_id')
                                # Update shared state if valid
                                if step_marked_task_id and int(step_marked_task_id) > state['last_marked_task_id']:
                                    state['last_marked_task_id'] = int(step_marked_task_id)
                                break

                        # 检查这一步是否有实际操作（非mark_task_complete的操作）
                        has_real_action = False
                        for action in actions:
                            action_dict = {}
                            if hasattr(action, 'model_dump'):
                                action_dict = action.model_dump(exclude_none=True)
                            elif hasattr(action, '__dict__'):
                                action_dict = action.__dict__
                                
                            for key in action_dict.keys():
                                if key not in ['mark_task_complete', 'done', '_action_dict', '_dict']:
                                    has_real_action = True
                                    break
                            if has_real_action:
                                break

                        action_str = " | ".join([self._format_action(a) for a in actions])
                        
                        # 获取 thinking
                        thinking = ""
                        if hasattr(step, 'model_output') and hasattr(step.model_output, 'thinking'):
                            thinking = step.model_output.thinking
                            
                        log_content = f"\n[Step {i+1}]\n"
                        if thinking:
                            log_content += f"思考: {thinking}\n"
                        log_content += f"执行: {action_str}\n"

                        if callback:
                            if asyncio.iscoroutinefunction(callback): await callback({'type': 'log', 'content': log_content})
                            else: callback({'type': 'log', 'content': log_content})

                        # 关键修复：如果这一步有实际操作但没有调用mark_task_complete，
                        # 且planned_tasks中下一个未标记的任务ID应该被标记
                        if has_real_action and not step_has_task_complete and planned_tasks:
                            # 找出下一个应该标记的任务ID
                            next_expected_task_id = state['last_marked_task_id'] + 1
                            if next_expected_task_id <= len(planned_tasks):
                                # 检查这个任务是否还没有被标记
                                task_already_marked = False
                                # 在回调之外我们无法直接访问任务状态，所以只能根据 last_marked_task_id 推断
                                # 假设之前的任务都已经标记完成了
                                
                                # 自动补充标记这个任务
                                logger.warning(f"⚠️ Auto-fixing: Step {i+1} had actions but no mark_task_complete. Auto-marking task {next_expected_task_id} as completed.")
                                data = {'task_id': int(next_expected_task_id), 'status': 'completed'}
                                if asyncio.iscoroutinefunction(callback):
                                    await callback(data)
                                else:
                                    callback(data)
                                state['last_marked_task_id'] = next_expected_task_id
                        
                        # 特殊修复：如果Agent在Thinking中说任务完成了，但没有调用mark_task_complete，强制标记所有剩余任务
                        if thinking and any(w in thinking.lower() for w in ['complete', 'done', 'finished', 'success']) and not has_real_action:
                             if planned_tasks and state['last_marked_task_id'] < len(planned_tasks):
                                 logger.warning(f"⚠️ Auto-fixing: Agent thinks it's done. Marking remaining tasks as completed.")
                                 for task_id in range(state['last_marked_task_id'] + 1, len(planned_tasks) + 1):
                                     data = {'task_id': int(task_id), 'status': 'completed'}
                                     if asyncio.iscoroutinefunction(callback):
                                         await callback(data)
                                     else:
                                         callback(data)
                                 state['last_marked_task_id'] = len(planned_tasks)

                    except Exception as e:
                        logger.warning(f"⚠️ Error in on_step_end processing: {e}")
                last_processed_step = len(history)

        # Monkey Patch agent.step to ensure callback is called
        if hasattr(agent, 'step'):
            _original_step = agent.step
            async def _patched_step(*args, **kwargs):
                result = await _original_step(*args, **kwargs)
                try:
                    await on_step_end(agent)
                except Exception as e:
                    logger.warning(f"Callback error in patched step: {e}")
                return result
            agent.step = _patched_step
            logger.info("✅ Monkey patched agent.step for real-time logging")

        try:
            # Try to pass callback just in case
            import inspect
            sig = inspect.signature(agent.run)
            if 'on_step_end' in sig.parameters:
                await agent.run(max_steps=100, on_step_end=on_step_end)
            else:
                await agent.run(max_steps=100)
        except KeyboardInterrupt:
            pass
        except Exception as e:
            logger.error(f"Agent execution error: {e}")
            raise
        finally:
            # Ensure final logs are flushed
            try:
                await on_step_end(agent)
            except:
                pass

        # 在任务结束时检查不一致的任务状态
        history = getattr(agent, 'history', [])
        if history:
            logger.info("🔍 Performing final task status consistency check")
            # 检查是否有任务执行了但未标记完成
            executed_tasks_info = self._find_executed_tasks(history)
            if executed_tasks_info and executed_tasks_info.get('unmarked_actions'):
                logger.warning(f"⚠️ Found {executed_tasks_info['executed_actions']} executed actions, but only {len(executed_tasks_info['marked_tasks'])} tasks were explicitly marked complete")
                logger.warning(f"⚠️ Unmarked actions: {executed_tasks_info['unmarked_actions']}")
                logger.warning("⚠️ This indicates the AI agent did not follow the 'mark_task_complete' rule properly.")

        return history

    def _find_executed_tasks(self, history):
        """
        通过分析执行历史找出已执行但未标记完成的任务
        """
        if not history or not hasattr(history, 'steps'):
            return []

        executed_actions = {}  # 已执行的操作类型和索引，以及对应的步骤
        marked_tasks = set()   # 已标记完成的任务ID

        # 分析执行历史
        for step_idx, step in enumerate(getattr(history, 'steps', [])):
            # 检查每一步中的actions
            actions = getattr(step, 'actions', [])
            for action in actions:
                # 记录已执行的操作
                if hasattr(action, 'input'):
                    action_key = f"input_{action.input.index}"
                    executed_actions[action_key] = {
                        'step': step_idx,
                        'action': 'input',
                        'index': action.input.index
                    }
                elif hasattr(action, 'click'):
                    action_key = f"click_{action.click.index}"
                    executed_actions[action_key] = {
                        'step': step_idx,
                        'action': 'click',
                        'index': action.click.index
                    }
                elif hasattr(action, 'switch_tab'):
                    action_key = f"switch_tab_{action.switch_tab.tab_id}"
                    executed_actions[action_key] = {
                        'step': step_idx,
                        'action': 'switch_tab',
                        'tab_id': action.switch_tab.tab_id
                    }

                # 记录已标记完成的任务
                if hasattr(action, 'mark_task_complete'):
                    marked_tasks.add(action.mark_task_complete.task_id)

        # 理想情况下应该有一个映射机制来关联操作和任务，但由于我们没有这个映射，
        # 我们只能记录未标记完成的执行操作作为调试信息
        unmarked_actions = []
        for action_key, action_info in executed_actions.items():
            unmarked_actions.append({
                'action': action_info['action'],
                'step': action_info['step'],
                'details': action_key
            })

        return {
            'marked_tasks': list(marked_tasks),
            'executed_actions': len(executed_actions),
            'unmarked_actions': unmarked_actions
        }

    async def run_full_process(self, task_description: str, analysis_callback=None, step_callback=None, should_stop=None):
        planned_tasks = await self.analyze_task(task_description)
        if analysis_callback:
            if asyncio.iscoroutinefunction(analysis_callback): await analysis_callback(planned_tasks)
            else: analysis_callback(planned_tasks)
            
        return await self.run_task(task_description, planned_tasks, step_callback, should_stop)
