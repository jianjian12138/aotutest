import logging
import asyncio
import json
import base64
import time
import re
import os
import io
from datetime import datetime
from typing import Dict, Any, List, Optional
from asgiref.sync import sync_to_async
from PIL import Image

from django.conf import settings
from apps.ui_automation.models import AIExecutionRecord
from apps.requirement_analysis.models import AIModelConfig

logger = logging.getLogger('django')

class VisionWebAgent:
    """
    Web Automation Agent driven by Vision LLM (Screenshot -> Action).
    Inspired by Skyvern and Stagehand.
    """
    def __init__(self, page, case_name: str = "Vision Web Task", model_config_id=None, api_key=None, base_url=None, model_name=None):
        self.page = page
        self.case_name = case_name
        self.execution_record = None
        
        # Priority 1: Direct credentials passed in
        if api_key and base_url:
            self.api_key = api_key
            self.base_url = base_url
            self.model_name = model_name or "gpt-4o"
        else:
            # Priority 2: Load from DB (Warning: Don't call this from async context!)
            config_obj = None
            if model_config_id:
                try:
                    config_obj = AIModelConfig.objects.get(id=model_config_id)
                except AIModelConfig.DoesNotExist:
                    logger.warning(f"Provided model_config_id {model_config_id} not found")
            
            if not config_obj:
                config_obj = AIModelConfig.objects.filter(role='writer', is_active=True).first()
                
            if not config_obj:
                 # Priority 3: Env vars
                 self.api_key = os.getenv("OPENAI_API_KEY", "")
                 self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
                 self.model_name = "gpt-4o"
            else:
                self.api_key = config_obj.api_key
                self.base_url = config_obj.base_url
                self.model_name = config_obj.model_name

        import httpx
        self.client = httpx.AsyncClient(timeout=60.0)

    async def inspect_image(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Inspect a static image using VLM to identify elements.
        Returns structure similar to inspect_page but with estimated bboxes.
        """
        try:
            # 1. Save Image
            rel_dir = "temp/inspection"
            full_dir = os.path.join(settings.MEDIA_ROOT, rel_dir)
            os.makedirs(full_dir, exist_ok=True)
            
            timestamp = int(time.time())
            main_filename = f"inspect_img_{timestamp}.jpg"
            main_path = os.path.join(full_dir, main_filename)
            
            with open(main_path, 'wb') as f:
                f.write(image_bytes)
                
            media_url = getattr(settings, 'MEDIA_URL', '/media/')
            full_screenshot_url = f"{media_url}{rel_dir}/{main_filename}"
            
            image_b64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # 2. Call VLM to find elements
            # We ask for bounding boxes in 0-1000 scale
            system_prompt = """
            You are a UI Element Detector. 
            Identify all interactive UI elements (buttons, inputs, icons, links) in the image.
            Return a JSON list of objects.
            Format:
            [
              {
                "id": 1,
                "name": "Login Button",
                "type": "button",
                "bbox": [ymin, xmin, ymax, xmax]  (0-1000 normalized coordinates)
              }
            ]
            Return ONLY the JSON.
            """
            
            response_text = await self._call_vlm_custom(system_prompt, "Detect elements", image_b64)
            
            # Parse JSON
            elements_data = []
            try:
                # Try to extract JSON if wrapped in markdown
                match = re.search(r'(\[.*\])', response_text, re.DOTALL)
                if match:
                    elements_data = json.loads(match.group(1))
                else:
                    elements_data = json.loads(response_text)
            except Exception as e:
                logger.error(f"Failed to parse VLM response: {e}, Response: {response_text}")
                # Fallback or empty
                return {
                    "screenshot_url": full_screenshot_url,
                    "elements": [],
                    "page_title": "Image Inspection"
                }

            # 3. Process elements (Crop and convert bbox)
            img = Image.open(io.BytesIO(image_bytes))
            width, height = img.size
            
            processed_elements = []
            for el in elements_data:
                # Convert normalized bbox [ymin, xmin, ymax, xmax] to pixels [xmin, ymin, xmax, ymax]
                # Note: VLM usually returns [ymin, xmin, ymax, xmax] or [xmin, ymin, xmax, ymax]. 
                # Let's assume the prompt instruction [ymin, xmin, ymax, xmax] is followed.
                # Actually, standard Object Detection often uses [ymin, xmin, ymax, xmax].
                # Let's double check prompt or enforce specific format.
                # To be safe, let's ask for [xmin, ymin, xmax, ymax] in prompt to match PIL.
                
                # Re-reading prompt above: I wrote "bbox": [ymin, xmin, ymax, xmax]".
                # PIL crop needs (left, top, right, bottom) -> (xmin, ymin, xmax, ymax).
                
                bbox_norm = el.get('bbox', [])
                if len(bbox_norm) != 4:
                    continue
                    
                ymin, xmin, ymax, xmax = bbox_norm
                
                # De-normalize
                abs_xmin = int(xmin / 1000 * width)
                abs_ymin = int(ymin / 1000 * height)
                abs_xmax = int(xmax / 1000 * width)
                abs_ymax = int(ymax / 1000 * height)
                
                # Validate
                abs_xmin = max(0, abs_xmin)
                abs_ymin = max(0, abs_ymin)
                abs_xmax = min(width, abs_xmax)
                abs_ymax = min(height, abs_ymax)
                
                if abs_xmax - abs_xmin < 5 or abs_ymax - abs_ymin < 5:
                    continue
                    
                # Crop
                try:
                    cropped = img.crop((abs_xmin, abs_ymin, abs_xmax, abs_ymax))
                    crop_filename = f"el_img_{timestamp}_{el['id']}.png"
                    crop_path = os.path.join(full_dir, crop_filename)
                    cropped.save(crop_path)
                    
                    el_out = {
                        "id": el['id'],
                        "tagName": el.get('type', 'element'),
                        "text": el.get('name', ''),
                        "crop_url": f"{media_url}{rel_dir}/{crop_filename}",
                        "locators": {
                            "playwright": "N/A (Image Source)",
                            "selenium": "N/A (Image Source)",
                            "appium": f"//attribute[contains(@text, '{el.get('name', '')}')] (Approximate)",
                            "airtest": f"Template(r'{crop_filename}', record_pos=({(abs_xmin+abs_xmax)/2/width}, {(abs_ymin+abs_ymax)/2/height}), resolution=({width}, {height}))"
                        }
                    }
                    processed_elements.append(el_out)
                except Exception as e:
                    logger.warning(f"Failed to crop image element {el['id']}: {e}")

            return {
                "screenshot_url": full_screenshot_url,
                "elements": processed_elements,
                "page_title": "Image Analysis"
            }

        except Exception as e:
            logger.error(f"Image Inspection failed: {e}")
            raise

    async def _call_vlm_custom(self, system_prompt, user_text, image_base64) -> str:
        """Helper for custom VLM calls"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                ]
            }
        ]
        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": 2000,
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

    async def inspect_page(self, url: str) -> Dict[str, Any]:
        """
        Navigate to URL, identify elements, and return structured data for inspection.
        Includes locators for Playwright, Selenium, Appium, and Airtest.
        """
        try:
            logger.info(f"Inspecting page: {url}")
            await self.page.goto(url, wait_until='networkidle')
            await asyncio.sleep(2) # Extra wait for rendering

            # 1. Inject JS to find elements and calculate locators
            # Script inspired by Skyvern's element finding logic (simplified)
            js_script = """
            () => {
                function getXPath(element) {
                    if (element.id !== '')
                        return '//*[@id=\"' + element.id + '\"]';
                    if (element === document.body)
                        return element.tagName;

                    var ix = 0;
                    var siblings = element.parentNode.childNodes;
                    for (var i = 0; i < siblings.length; i++) {
                        var sibling = siblings[i];
                        if (sibling === element)
                            return getXPath(element.parentNode) + '/' + element.tagName + '[' + (ix + 1) + ']';
                        if (sibling.nodeType === 1 && sibling.tagName === element.tagName)
                            ix++;
                    }
                }

                function getCssSelector(element) {
                    if (element.id) return '#' + element.id;
                    if (element.className) {
                        var classes = element.className.split(/\s+/);
                        for (var i = 0; i < classes.length; i++) {
                            if (classes[i].length > 0) {
                                return element.tagName + '.' + classes[i];
                            }
                        }
                    }
                    return element.tagName;
                }

                const elements = [];
                const allElements = document.querySelectorAll('button, a, input, select, textarea, [role="button"]');
                
                let idCounter = 1;
                allElements.forEach(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden') {
                        elements.push({
                            id: idCounter++,
                            tagName: el.tagName.toLowerCase(),
                            text: el.innerText ? el.innerText.slice(0, 50).trim() : '',
                            xpath: getXPath(el),
                            css: getCssSelector(el),
                            bbox: {
                                x: rect.x + window.scrollX,
                                y: rect.y + window.scrollY,
                                width: rect.width,
                                height: rect.height
                            }
                        });
                    }
                });
                return elements;
            }
            """
            
            elements_data = await self.page.evaluate(js_script)
            
            # 2. Take full screenshot
            screenshot_bytes = await self.page.screenshot(full_page=True, type='jpeg')
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            
            # Save main screenshot
            # Use a temp directory for inspection results
            rel_dir = "temp/inspection"
            full_dir = os.path.join(settings.MEDIA_ROOT, rel_dir)
            os.makedirs(full_dir, exist_ok=True)
            
            timestamp = int(time.time())
            main_filename = f"inspect_full_{timestamp}.jpg"
            main_path = os.path.join(full_dir, main_filename)
            
            with open(main_path, 'wb') as f:
                f.write(screenshot_bytes)
                
            media_url = getattr(settings, 'MEDIA_URL', '/media/')
            full_screenshot_url = f"{media_url}{rel_dir}/{main_filename}"

            # 3. Crop images for Airtest (Server-side cropping)
            # We use PIL to crop based on bbox
            img = Image.open(io.BytesIO(screenshot_bytes))
            
            processed_elements = []
            for el in elements_data:
                bbox = el['bbox']
                # Skip tiny elements
                if bbox['width'] < 10 or bbox['height'] < 10:
                    continue
                    
                # Crop
                left = bbox['x']
                top = bbox['y']
                right = left + bbox['width']
                bottom = top + bbox['height']
                
                try:
                    cropped = img.crop((left, top, right, bottom))
                    crop_filename = f"el_{timestamp}_{el['id']}.png"
                    crop_path = os.path.join(full_dir, crop_filename)
                    cropped.save(crop_path)
                    
                    el['crop_url'] = f"{media_url}{rel_dir}/{crop_filename}"
                    
                    # Refine locators for Appium/Airtest
                    el['locators'] = {
                        "playwright": f"page.locator('{el['css']}')" if el['css'] else f"page.locator('xpath={el['xpath']}')",
                        "selenium": f"driver.find_element(By.XPATH, '{el['xpath']}')",
                        "appium": f"driver.find_element(MobileBy.XPATH, '{el['xpath']}')", # Assuming web context
                        "airtest": f"Template(r'{crop_filename}', record_pos=({bbox['x']}, {bbox['y']}), resolution=({img.width}, {img.height}))"
                    }
                    
                    processed_elements.append(el)
                except Exception as e:
                    logger.warning(f"Failed to crop element {el['id']}: {e}")

            return {
                "screenshot_url": full_screenshot_url,
                "elements": processed_elements,
                "page_title": await self.page.title()
            }
            
        except Exception as e:
            logger.error(f"Inspection failed: {e}")
            raise

    async def _get_screenshot_base64(self) -> str:
        """Capture full page or viewport screenshot"""
        try:
            # JPEG quality 70 is usually enough for LLM and saves tokens
            screenshot_bytes = await self.page.screenshot(type='jpeg', quality=70)
            return base64.b64encode(screenshot_bytes).decode('utf-8')
        except Exception as e:
            logger.error(f"Web screenshot failed: {e}")
            return ""

    async def _inject_som_markers(self):
        """
        Inject Set-of-Mark (SoM) markers to help LLM locate elements.
        This is a simplified version.
        """
        # TODO: Implement actual JS injection to draw bounding boxes with IDs
        pass

    async def _call_vlm(self, prompt: str, image_base64: str) -> str:
        """Call Vision LLM"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        system_prompt = """You are a web automation agent. 
You will receive a screenshot of a web page and a user instruction.
You need to analyze the UI and output the next action to perform.
Output MUST be a valid JSON object with a 'type' field.

Supported actions:
- {"type": "click", "x": 123, "y": 456, "description": "Click Login button"} (Preferred: Click coordinates)
- {"type": "type", "text": "hello", "description": "Type hello"} (Types into currently focused element)
- {"type": "scroll", "direction": "down", "amount": 500, "description": "Scroll down"}
- {"type": "wait", "seconds": 2, "description": "Wait for load"}
- {"type": "done", "description": "Task completed"}
- {"type": "fail", "reason": "Element not found", "description": "Task failed"}

Coordinate System: Top-left is (0,0).
Think step by step. Return ONLY the JSON object.
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": f"Task: {prompt}"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
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

    async def _perform_action(self, action: Dict[str, Any]):
        """Execute Playwright action"""
        action_type = action.get('type')
        
        if action_type == 'click':
            x, y = action.get('x'), action.get('y')
            if x is not None and y is not None:
                await self.page.mouse.click(x, y)
                
        elif action_type == 'type':
            text = action.get('text', '')
            await self.page.keyboard.type(text)
            
        elif action_type == 'scroll':
            direction = action.get('direction', 'down')
            amount = action.get('amount', 500)
            if direction == 'down':
                await self.page.mouse.wheel(0, amount)
            else:
                await self.page.mouse.wheel(0, -amount)
                
        elif action_type == 'wait':
            seconds = action.get('seconds', 1)
            await asyncio.sleep(seconds)

    async def _save_screenshot(self, img_b64: str, step: int) -> str:
        # Same as ai_mobile.py, ideally abstract this to a utils/mixin
        rel_path = f"ui_screenshots/web_ai/{self.execution_record.id}"
        full_dir = os.path.join(settings.MEDIA_ROOT, rel_path)
        if not os.path.exists(full_dir):
            os.makedirs(full_dir, exist_ok=True)
        
        filename = f"step_{step}_{int(time.time())}.jpg"
        full_path = os.path.join(full_dir, filename)
        
        try:
            img_data = base64.b64decode(img_b64)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._write_file, full_path, img_data)
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

    def _update_status_sync(self, status):
        if self.execution_record:
            self.execution_record.status = status
            self.execution_record.end_time = datetime.now()
            self.execution_record.save()

    async def run_task(self, task_description: str, callback=None, should_stop=None):
        logger.info(f"Starting Vision Web Task: {task_description}")
        
        # Init DB Record
        if not self.execution_record:
            self.execution_record = await sync_to_async(AIExecutionRecord.objects.create)(
                project_id=1, 
                case_name=self.case_name,
                task_description=task_description,
                execution_mode='vision_web',
                status='running',
                executed_by_id=1
            )
            
        max_steps = 20
        step = 0
        
        try:
            while step < max_steps:
                if should_stop and await should_stop():
                    logger.info("Task stopped by user.")
                    await sync_to_async(self._update_status_sync)('stopped')
                    return "Stopped"
                    
                step += 1
                
                # 1. Capture
                img_b64 = await self._get_screenshot_base64()
                screenshot_url = await self._save_screenshot(img_b64, step)
                
                # 2. Think (VLM)
                response_text = await self._call_vlm(task_description, img_b64)
                
                # 3. Parse
                action = {}
                try:
                    match = re.search(r'(\{.*\})', response_text, re.DOTALL)
                    if match:
                        action = json.loads(match.group(1))
                    else:
                        action = json.loads(response_text)
                except:
                    pass
                    
                # Log & Save
                if callback:
                    log_entry = {"step": step, "action": action, "response": response_text}
                    await callback({'type': 'log', 'content': json.dumps(log_entry, ensure_ascii=False)})
                    
                step_data = {
                    "step": step,
                    "action": action,
                    "screenshot": screenshot_url,
                    "description": action.get('description', ''),
                    "timestamp": datetime.now().isoformat()
                }
                await sync_to_async(self._add_step_to_record_sync)(step_data)
                
                # 4. Act
                if action:
                    if action.get('type') == 'done':
                        await sync_to_async(self._update_status_sync)('passed')
                        return "Success"
                    if action.get('type') == 'fail':
                        await sync_to_async(self._update_status_sync)('failed')
                        return "Failed"
                        
                    await self._perform_action(action)
                    await asyncio.sleep(2) # Wait for UI
                else:
                    logger.warning("No action parsed")
                    
            await sync_to_async(self._update_status_sync)('failed')
            return "Max steps reached"
            
        except Exception as e:
            logger.error(f"Vision Web Task Error: {e}")
            await sync_to_async(self._update_status_sync)('failed')
            raise
        finally:
            await self.client.aclose()
