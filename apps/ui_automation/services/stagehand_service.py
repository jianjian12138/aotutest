import logging
import json
import os
import asyncio
import base64
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from apps.requirement_analysis.models import AIModelConfig

logger = logging.getLogger('django')

class StagehandService:
    """
    Implements Stagehand-like AI capabilities for UI Automation.
    Provides 'act' (atomic AI action) and 'extract' (structured data extraction).
    """
    
    def __init__(self, page, model_config_id=None):
        self.page = page
        self.llm = self._init_llm(model_config_id)

    def _init_llm(self, model_config_id):
        config_obj = None
        if model_config_id:
            try:
                config_obj = AIModelConfig.objects.get(id=model_config_id)
            except AIModelConfig.DoesNotExist:
                pass
        
        if not config_obj:
            # Fallback to default active config
            config_obj = AIModelConfig.objects.filter(is_active=True).first()
            
        # Default env vars
        api_key = os.getenv('OPENAI_API_KEY')
        base_url = os.getenv('OPENAI_API_BASE')
        model_name = 'gpt-4o'
        
        if config_obj:
            api_key = config_obj.api_key or api_key
            base_url = config_obj.base_url or base_url
            model_name = config_obj.model_name or model_name

        if not api_key:
            logger.warning("StagehandService: No API Key found.")

        return ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=0
        )

    async def _get_page_context(self):
        """
        Get a simplified representation of the page for the LLM.
        Focuses on interactive elements to reduce token usage.
        """
        js_script = """
        () => {
            function getInteractiveElements(root) {
                const interactiveTags = ['a', 'button', 'input', 'select', 'textarea', 'details', 'summary'];
                const elements = [];
                const walker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT, {
                    acceptNode: (node) => {
                        if (interactiveTags.includes(node.tagName.toLowerCase()) || 
                            node.getAttribute('role') === 'button' ||
                            node.onclick ||
                            (node.tagName.toLowerCase() === 'div' && (node.className.includes('btn') || node.className.includes('button'))) # Heuristic
                           ) {
                            return NodeFilter.FILTER_ACCEPT;
                        }
                        return NodeFilter.FILTER_SKIP;
                    }
                });
                
                while(walker.nextNode()) {
                    const node = walker.currentNode;
                    const rect = node.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) { // Visible check
                         let attributes = "";
                         for (let i=0; i < node.attributes.length; i++) {
                             const attr = node.attributes[i];
                             if (['id', 'name', 'class', 'placeholder', 'aria-label', 'role', 'type', 'href', 'title'].includes(attr.name)) {
                                 attributes += `${attr.name}="${attr.value}" `;
                             }
                         }
                         // Clean text
                         let text = node.innerText.replace(/\\s+/g, ' ').trim().slice(0, 50);
                         elements.push(`<${node.tagName.toLowerCase()} ${attributes.trim()}>${text}</${node.tagName.toLowerCase()}>`);
                    }
                }
                return elements.join('\\n');
            }
            return getInteractiveElements(document.body);
        }
        """
        try:
            # Try to get simplified context
            context = await self.page.evaluate(js_script)
            if not context or len(context) < 50:
                 # If script returns too little, maybe it's a canvas or strange DOM. Fallback to body text.
                 return await self.page.evaluate("() => document.body.innerText")
            return context
        except Exception as e:
            logger.warning(f"Stagehand context extraction failed: {e}. Falling back to content.")
            return await self.page.content() # Fallback to full HTML

    async def act(self, action_description):
        """
        AI-driven action: Analyzes page, finds element, performs action.
        Returns: (success, log_message)
        """
        if not self.llm:
            return False, "LLM not initialized"

        context = await self._get_page_context()
        
        prompt = f"""
        You are a Playwright automation expert.
        User wants to perform this action: "{action_description}"
        
        Current page interactive elements (simplified):
        {context[:15000]} 
        
        Identify the best element to interact with.
        Return a JSON object with:
        - "selector": The best Playwright selector. PREFER 'text=' or 'id=' or 'placeholder=' or accessible 'role='. Avoid complex CSS classes if possible.
        - "action": The action to perform ("click", "fill", "hover").
        - "value": The value to fill (if action is fill).
        - "reason": Brief reasoning.
        
        Example: {{"selector": "button:has-text('Login')", "action": "click", "reason": "Found login button by text"}}
        """
        
        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            content = response.content.replace('```json', '').replace('```', '').strip()
            
            plan = json.loads(content)
            selector = plan.get('selector')
            action = plan.get('action')
            value = plan.get('value')
            reason = plan.get('reason')
            
            logger.info(f"Stagehand Act Plan: {plan}")
            
            if not selector:
                return False, f"AI failed to identify a selector. Reason: {reason}"

            # Execute Playwright Action
            element = self.page.locator(selector).first
            
            # Wait for element
            await element.wait_for(timeout=5000)
            
            if action == 'click':
                await element.click()
            elif action == 'fill':
                await element.fill(str(value) or "")
            elif action == 'hover':
                await element.hover()
            else:
                await element.click() 
                
            return True, f"AI performed '{action}' on '{selector}'. Reason: {reason}"
            
        except Exception as e:
            logger.error(f"Stagehand Act Error: {e}")
            return False, f"Stagehand Act Failed: {str(e)}"

    async def extract(self, instruction, schema_desc):
        """
        AI-driven extraction.
        Returns: (success, data_json)
        """
        if not self.llm:
            return False, "LLM not initialized"

        # For extraction, get visible text content which is usually better than just interactive elements
        content = await self.page.evaluate("() => document.body.innerText")
        
        prompt = f"""
        Extract data from the following page text based on this instruction: "{instruction}"
        
        Page Text:
        {content[:20000]}
        
        Return the data as a valid JSON object matching this schema description: {schema_desc}
        If extracting a list of items, return them wrapped in an object like {{"items": [...]}}.
        ONLY return the JSON.
        """
        
        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            json_str = response.content.replace('```json', '').replace('```', '').strip()
            data = json.loads(json_str)
            return True, data
        except Exception as e:
            logger.error(f"Stagehand Extract Error: {e}")
            return False, f"Extraction failed: {str(e)}"

    async def vision_act(self, instruction):
        """
        Vision-driven action (Magnitude mode).
        Takes a screenshot, asks LLM for coordinates, clicks.
        """
        if not self.llm:
            return False, "LLM not initialized"

        # Take screenshot
        try:
            screenshot_bytes = await self.page.screenshot()
            base64_image = base64.b64encode(screenshot_bytes).decode('utf-8')
            
            prompt = [
                {"type": "text", "text": f"""
                You are a Vision-based UI Automation Agent.
                User wants to perform this action: "{instruction}"
                
                Look at the screenshot. Identify the element that matches the instruction.
                Return a JSON object with:
                - "x": The x coordinate of the center of the element.
                - "y": The y coordinate of the center of the element.
                - "reason": Brief reasoning.
                
                Example: {{"x": 100, "y": 200, "reason": "Found red button"}}
                ONLY return the JSON.
                """},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
            ]
            
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            content = response.content.replace('```json', '').replace('```', '').strip()
            plan = json.loads(content)
            
            x = plan.get('x')
            y = plan.get('y')
            reason = plan.get('reason')
            
            if x is None or y is None:
                return False, f"Vision AI failed to find coordinates. Reason: {reason}"
                
            # Perform click
            await self.page.mouse.click(x, y)
            
            return True, f"Vision AI clicked at ({x}, {y}). Reason: {reason}"
            
        except Exception as e:
            logger.error(f"Vision Act Error: {e}")
            return False, f"Vision Act Failed: {str(e)}"

    async def auto_heal(self, failed_selector, error_msg, target_desc=""):
        """
        AI-driven Self-Healing: Analyzes page to find a new selector for a failed one.
        Returns: (success, new_selector, reason)
        """
        if not self.llm:
            return False, None, "LLM not initialized"

        context = await self._get_page_context()
        
        prompt = f"""
        You are an expert Test Automation Engineer.
        A Playwright test script failed to interact with an element.
        
        Failed Selector: "{failed_selector}"
        Element Description/Name: "{target_desc}"
        Error Message: "{error_msg}"
        
        Current page interactive elements (simplified):
        {context[:15000]}
        
        Analyze the DOM and provide a robust, resilient Playwright selector that will locate this element successfully.
        PREFER 'text=' or 'placeholder=' or accessible 'role='. Avoid complex CSS paths if possible.
        
        Return a JSON object with:
        - "selector": The corrected Playwright selector.
        - "reason": Brief explanation of why the original failed and why this one works.
        
        ONLY return the JSON object.
        """
        
        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            content = response.content.replace('```json', '').replace('```', '').strip()
            
            plan = json.loads(content)
            new_selector = plan.get('selector')
            reason = plan.get('reason')
            
            if not new_selector:
                return False, None, "AI failed to generate a new selector"
                
            return True, new_selector, reason
            
        except Exception as e:
            logger.error(f"Stagehand Auto-Heal Error: {e}")
            return False, None, f"Auto-Heal Failed: {str(e)}"

