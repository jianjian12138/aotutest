import logging
import os
import asyncio
import json
import base64
import time
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from asgiref.sync import sync_to_async

from django.conf import settings
from apps.requirement_analysis.models import AIModelConfig
from apps.ui_automation.utils.device_manager import DeviceManager
from apps.ui_automation.models import AIExecutionRecord

logger = logging.getLogger('django')

class BasePhoneAgent:
    def __init__(self, device_id: str, case_name: str = "Mobile AI Task", model_config_id=None):
        self.device_id = device_id
        self.case_name = case_name
        self.execution_record = None
        self.history = []
        
        # Load Config from DB
        
        config_obj = None
        if model_config_id:
            try:
                config_obj = AIModelConfig.objects.get(id=model_config_id)
            except AIModelConfig.DoesNotExist:
                logger.warning(f"Provided model_config_id {model_config_id} not found")
        
        if not config_obj:
            # Fallback
            role_name = 'autoglm'
            config_obj = AIModelConfig.objects.filter(role=role_name, is_active=True).first()
            
        if not config_obj:
            # Fallback to browser_use_text or other if autoglm not found, but better to warn
            logger.warning("No AutoGLM config found, trying generic writer config")
            config_obj = AIModelConfig.objects.filter(role='writer', is_active=True).first()
            
        if not config_obj:
            raise ValueError("No active AI Model Configuration found for AutoGLM.")

        self.api_key = config_obj.api_key or "sk-placeholder"
        self.base_url = config_obj.base_url
        self.model_name = config_obj.model_name
        self.model_type = config_obj.model_type
        
        # Initialize HTTP client for API calls
        import httpx
        self.client = httpx.AsyncClient(timeout=60.0)

    async def _get_screenshot_base64(self) -> str:
        """Capture screenshot from device and convert to base64"""
        try:
            # Use adb to capture screenshot
            # Since DeviceManager is synchronous or we access adb directly
            # We'll use a shell command for simplicity and reliability here
            
            # 1. Capture to device temp
            adb_cmd_cap = f"adb -s {self.device_id} shell screencap -p /sdcard/autotest_cap.png"
            proc = await asyncio.create_subprocess_shell(adb_cmd_cap)
            await proc.communicate()
            
            # 2. Pull to local temp
            temp_file = f"temp_cap_{self.device_id.replace(':', '_')}.png"
            adb_cmd_pull = f"adb -s {self.device_id} pull /sdcard/autotest_cap.png {temp_file}"
            proc = await asyncio.create_subprocess_shell(adb_cmd_pull)
            await proc.communicate()
            
            # 3. Read and encode
            if os.path.exists(temp_file):
                with open(temp_file, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                
                # Cleanup
                os.remove(temp_file)
                return encoded_string
            else:
                logger.error("Failed to pull screenshot file")
                return ""
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return ""

    async def _execute_adb_command(self, cmd: str):
        """Execute raw ADB shell command"""
        full_cmd = f"adb -s {self.device_id} shell {cmd}"
        logger.info(f"Executing ADB: {full_cmd}")
        proc = await asyncio.create_subprocess_shell(full_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        if stdout:
            logger.debug(f"ADB Output: {stdout.decode()}")
        if stderr:
            logger.warning(f"ADB Error: {stderr.decode()}")

    async def _perform_action(self, action: Dict[str, Any]):
        """Execute action on device using Appium if available, fallback to ADB"""
        action_type = action.get('type')
        
        # Check if we have an appium driver (To be implemented in DeviceManager)
        # For now, we enhance the ADB implementation to be more robust and prepare for Appium
        
        if action_type == 'tap':
            x = action.get('x')
            y = action.get('y')
            if x is not None and y is not None:
                # TODO: If self.driver: use W3C actions
                await self._execute_adb_command(f"input tap {x} {y}")
        
        elif action_type == 'swipe':
            start_x = action.get('start_x')
            start_y = action.get('start_y')
            end_x = action.get('end_x')
            end_y = action.get('end_y')
            duration = action.get('duration', 300)
            if all([start_x, start_y, end_x, end_y]):
                # TODO: If self.driver: use W3C actions
                await self._execute_adb_command(f"input swipe {start_x} {start_y} {end_x} {end_y} {duration}")
                
        elif action_type == 'input':
            text = action.get('text', '')
            # ADB input text doesn't support spaces well, replace with %s
            escaped_text = text.replace(' ', '%s')
            await self._execute_adb_command(f"input text {escaped_text}")
            
        elif action_type == 'key':
            keycode = action.get('keycode')
            if keycode:
                await self._execute_adb_command(f"input keyevent {keycode}")
                
        elif action_type == 'home':
            await self._execute_adb_command("input keyevent 3")
            
        elif action_type == 'back':
            await self._execute_adb_command("input keyevent 4")
            
        elif action_type == 'wait':
            seconds = action.get('seconds', 1)
            await asyncio.sleep(seconds)

    async def _call_vlm(self, prompt: str, image_base64: str) -> str:
        """Call VLM model with prompt and image"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Construct message payload compatible with OpenAI Vision
        messages = [
            {
                "role": "system",
                "content": """You are an intelligent mobile automation agent. 
You will receive a screenshot of a mobile phone and a user instruction.
You need to analyze the UI and output the next action to perform.
Output MUST be a valid JSON object with a 'type' field.
Supported actions:
- {"type": "tap", "x": 100, "y": 200, "description": "Tap the login button"}
- {"type": "swipe", "start_x": 100, "start_y": 500, "end_x": 100, "end_y": 100, "duration": 500, "description": "Scroll down"}
- {"type": "input", "text": "hello", "description": "Type hello"}
- {"type": "key", "keycode": 66, "description": "Press Enter"} (66=Enter, 3=Home, 4=Back)
- {"type": "home", "description": "Go Home"}
- {"type": "back", "description": "Go Back"}
- {"type": "done", "description": "Task completed"}
- {"type": "fail", "reason": "Cannot find element", "description": "Task failed"}

Coordinate System: Assume the screenshot resolution matches the device.
Think step by step. Return ONLY the JSON object.
"""
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Task: {prompt}"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}"
                        }
                    }
                ]
            }
        ]
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.0
        }
        
        url = self.base_url
        if not url.endswith('/chat/completions'):
             url = f"{url.rstrip('/')}/chat/completions"
             
        try:
            response = await self.client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            res_json = response.json()
            return res_json['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"VLM Call failed: {e}")
            raise

    async def _save_screenshot(self, img_b64: str, step: int) -> str:
        """Save base64 screenshot to media folder and return URL"""
        import os
        
        # Ensure directory exists
        rel_path = f"ui_screenshots/mobile_ai/{self.execution_record.id}"
        full_dir = os.path.join(settings.MEDIA_ROOT, rel_path)
        if not os.path.exists(full_dir):
            os.makedirs(full_dir, exist_ok=True)
        
        filename = f"step_{step}_{int(time.time())}.png"
        full_path = os.path.join(full_dir, filename)
        
        # Decode and write
        try:
            img_data = base64.b64decode(img_b64)
            # Run in executor to avoid blocking
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._write_file, full_path, img_data)
            
            # Construct URL (Assuming standard MEDIA_URL setup)
            media_url = getattr(settings, 'MEDIA_URL', '/media/')
            return f"{media_url}{rel_path}/{filename}"
        except Exception as e:
            logger.error(f"Failed to save screenshot: {e}")
            return ""

    def _write_file(self, path, data):
        with open(path, 'wb') as f:
            f.write(data)

    def _add_step_to_record_sync(self, step_data):
        self.execution_record.refresh_from_db()
        steps = self.execution_record.steps_completed or []
        steps.append(step_data)
        self.execution_record.steps_completed = steps
        self.execution_record.save(update_fields=['steps_completed'])

    async def run_task(self, task_description: str, callback=None, should_stop=None):
        """Main execution loop"""
        logger.info(f"Starting Mobile AI Task: {task_description} on {self.device_id}")
        
        # Create execution record
        if not self.execution_record:
            self.execution_record = await sync_to_async(AIExecutionRecord.objects.create)(
                project_id=1, # Default project for now
                case_name=self.case_name,
                task_description=task_description,
                execution_mode='mobile',
                status='running',
                executed_by_id=1 # Default admin
            )
        
        max_steps = 20
        step = 0
        
        try:
            while step < max_steps:
                # Check stop signal
                if should_stop and await should_stop():
                    logger.info("Task stopped by user.")
                    await sync_to_async(self._update_status)('stopped')
                    if callback:
                        await callback({'type': 'log', 'content': '\n[System] 任务已停止'})
                    return "Stopped"

                step += 1
                logger.info(f"Step {step}")
                
                # 1. Capture Screenshot
                img_b64 = await self._get_screenshot_base64()
                if not img_b64:
                    raise Exception("Failed to capture screenshot")
                
                # Save screenshot
                screenshot_url = await self._save_screenshot(img_b64, step)
                
                # 2. Call VLM
                response_text = await self._call_vlm(task_description, img_b64)
                logger.info(f"VLM Response: {response_text}")
                
                # 3. Parse Action
                action = {}
                try:
                    # Try to find JSON in response
                    match = re.search(r'(\{.*\})', response_text, re.DOTALL)
                    if match:
                        action = json.loads(match.group(1))
                    else:
                        action = json.loads(response_text)
                except Exception as e:
                    logger.error(f"Failed to parse JSON: {e}")
                    # Retry logic or fail?
                    # For now, continue to next loop or stop
                    pass
                
                # Log to callback
                if callback:
                    log_entry = {
                        "step": step,
                        "action": action,
                        "response": response_text,
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    }
                    if asyncio.iscoroutinefunction(callback):
                        await callback({'type': 'log', 'content': json.dumps(log_entry, ensure_ascii=False)})
                    else:
                        callback({'type': 'log', 'content': json.dumps(log_entry, ensure_ascii=False)})

                # Save step to DB
                step_data = {
                    "step": step,
                    "action": action,
                    "screenshot": screenshot_url,
                    "description": action.get('description', ''),
                    "timestamp": datetime.now().isoformat(),
                    "response": response_text
                }
                await sync_to_async(self._add_step_to_record_sync)(step_data)

                # 4. Execute Action
                if action:
                    action_type = action.get('type')
                    action.get('description', action_type)
                    
                    if action_type == 'done':
                        logger.info("Task completed by agent.")
                        await sync_to_async(self._update_status)('passed')
                        return "Success"
                    
                    if action_type == 'fail':
                        logger.info(f"Task failed by agent: {action.get('reason')}")
                        await sync_to_async(self._update_status)('failed')
                        return "Failed"
                        
                    await self._perform_action(action)
                    
                    # Wait for UI to settle
                    await asyncio.sleep(2)
                else:
                    logger.warning("No valid action parsed")
            
            await sync_to_async(self._update_status)('failed')
            return "Max steps reached"
            
        except Exception as e:
            logger.error(f"Task execution error: {e}")
            await sync_to_async(self._update_status)('failed')
            raise
        finally:
            await self.client.aclose()

    def _update_status(self, status):
        if self.execution_record:
            self.execution_record.status = status
            self.execution_record.end_time = datetime.now()
            self.execution_record.save()

