import os
import json
import logging
import asyncio
from typing import List, Dict, Any
from playwright.async_api import async_playwright, Page, Browser
from django.conf import settings
from apps.requirement_analysis.models import AIModelConfig, AIModelService
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

class AutonomousCrawler:
    """
    V3.1 Autonomous Crawler Engine
    Decides what to click based on DOM structure and LLM reasoning.
    """
    
    def __init__(self, start_url: str, max_steps: int = 20):
        self.start_url = start_url
        self.max_steps = max_steps
        self.visited_urls = set()
        self.action_history = []
        self.current_step = 0
        
    async def get_page_summary(self, page: Page) -> str:
        """
        Simplifies the DOM into a minimal structure for LLM understanding.
        Extracts interactive elements like buttons, inputs, and links.
        """
        # Execute a script inside the browser to extract clean metadata
        metadata = await page.evaluate('''() => {
            const interactives = [];
            const elements = document.querySelectorAll('button, a, input, [role="button"], .el-button, .el-input__inner');
            
            elements.forEach((el, index) => {
                if (el.offsetParent !== null) { // Only visible elements
                    const rect = el.getBoundingClientRect();
                    interactives.push({
                        id: index,
                        tag: el.tagName.toLowerCase(),
                        text: el.innerText || el.placeholder || el.value || "",
                        xpath: `//${el.tagName.toLowerCase()}[${index}]`, // Simplified XPath for LLM
                        type: el.type || "",
                        description: el.getAttribute('aria-label') || el.title || ""
                    });
                }
            });
            return interactives.slice(0, 50); // Limit to top 50 to save tokens
        }''')
        return json.dumps(metadata, ensure_ascii=False, indent=2)

    async def decide_next_action(self, page_summary: str, current_url: str) -> Dict[str, Any]:
        """
        Calls the LLM to decide the next best action to explore the site.
        """
        # Fetch active AI configuration
        config = await sync_to_async(AIModelConfig.objects.filter(is_active=True).first)()
        if not config:
             logger.warning("No active AI config found. Falling back to mock logic.")
             return {"action": "click", "element_id": 0, "reason": "No AI config found."}

        prompt = f"""
        Current URL: {current_url}
        Step: {self.current_step}/{self.max_steps}
        History: {self.action_history[-3:]}
        
        Available Elements:
        {page_summary}
        
        GOAL: Explore the business logic, find all nav paths, and report errors.
        DECISION: Output ONLY a JSON object with {{"action": "click|input|wait", "element_id": id, "reason": "why"}}
        """
        
        messages = [
            {"role": "system", "content": "You are a professional QA Engineer specialized in exploratory testing."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            # Call AI service
            response_data = await AIModelService.call_openai_compatible_api(config, messages)
            content = response_data['choices'][0]['message']['content']
            
            # Extract JSON from response (handling potential markdown wrapping)
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(content)
        except Exception as e:
            logger.error(f"AI Decision failed: {e}")
            return {"action": "wait", "element_id": 0, "reason": f"AI error: {str(e)}"}

    async def run_exploration(self):
        """
        The main loop: Start browser -> Load URL -> Decide -> Act -> Repeat
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            logger.info(f"🚀 Starting autonomous exploration at {self.start_url}")
            await page.goto(self.start_url)
            
            for step in range(self.max_steps):
                self.current_step = step
                current_url = page.url
                self.visited_urls.add(current_url)
                
                # 1. Sense: Get page structure
                summary = await self.get_page_summary(page)
                
                # 2. Think: Decide next action
                decision = await self.decide_next_action(summary, current_url)
                self.action_history.append(f"Step {step}: {decision['action']} on {decision['reason']}")
                
                # 3. Act: Execute in Playwright
                try:
                    if decision["action"] == "click":
                        # We use a more robust way to click in real logic
                        await page.evaluate(f'''(id) => {{
                            const elements = document.querySelectorAll('button, a, input, [role="button"], .el-button, .el-input__inner');
                            elements[id].click();
                        }}''', decision["element_id"])
                        await page.wait_for_load_state("networkidle", timeout=5000)
                except Exception as e:
                    logger.error(f"❌ Action failed at step {step}: {e}")
                    break
                
                logger.info(f"✅ Executed {decision['action']} at {current_url}")
                
            await browser.close()
            return self.action_history

if __name__ == "__main__":
    # Test execution
    crawler = AutonomousCrawler("http://localhost:5656")
    asyncio.run(crawler.run_exploration())
