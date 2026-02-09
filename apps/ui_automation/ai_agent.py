import logging
import asyncio
import json
import re
from .ai_base import BaseBrowserAgent
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger('django')

class BrowserAgent(BaseBrowserAgent):
    """
    Standard Browser Agent for Text Mode.
    Inherits all base functionality without applying dangerous visual patches.
    """
    def __init__(self, execution_mode='text', enable_gif=True, case_name=None, model_config_id=None, browser_type='chrome'):
        self.enable_gif = enable_gif
        self.case_name = case_name or "Adhoc Task"
        super().__init__(execution_mode='text', enable_gif=enable_gif, case_name=case_name, model_config_id=model_config_id, browser_type=browser_type)

    async def generate_script(self, task_description, mode='web'):
        """
        Generate Playwright script from task description using LLM
        """
        try:
            prompt = f"""
            Generate a complete, runnable Python Playwright script for the following test task.
            
            Task: {task_description}
            Mode: {mode}
            
            Requirements:
            1. Use 'playwright.sync_api' or 'playwright.async_api'.
            2. Include necessary imports.
            3. Handle browser launch and context creation.
            4. Include comments explaining steps.
            5. Return ONLY the code, no markdown formatting.
            """
            
            response = await self.llm.ainvoke([
                SystemMessage(content="You are an expert Test Automation Engineer specializing in Playwright."),
                HumanMessage(content=prompt)
            ])
            
            content = response.content.strip()
            # Clean Markdown
            content = re.sub(r'^```python\s*', '', content)
            content = re.sub(r'^```\s*', '', content)
            content = re.sub(r'\s*```$', '', content)
            
            return content
        except Exception as e:
            logger.error(f"Failed to generate script: {e}")
            return f"# Failed to generate script: {str(e)}"

# ============================================================================
# EXPORTED FUNCTIONS (FACTORY)
# ============================================================================

def get_agent_class(execution_mode='text'):
    # 始终返回文本模式实现
    return BrowserAgent

def run_ai_task_sync(task_description: str, planned_tasks=None, callback=None, should_stop=None, execution_mode='text'):
    agent = BrowserAgent(execution_mode='text')
    return asyncio.run(agent.run_task(task_description, planned_tasks, callback, should_stop))
    
def analyze_task_sync(task_description: str, execution_mode='text'):
    agent = BrowserAgent(execution_mode='text')
    return asyncio.run(agent.analyze_task(task_description))

def run_full_process_sync(task_description: str, analysis_callback=None, step_callback=None, should_stop=None, execution_mode='text', enable_gif=True, case_name=None, model_config_id=None, browser_type='chrome'):
    logger.info(f"DEBUG: Entering run_full_process_sync with execution_mode=text, enable_gif={enable_gif}, model_config_id={model_config_id}, browser_type={browser_type}")

    agent = BrowserAgent(execution_mode='text', enable_gif=enable_gif, case_name=case_name, model_config_id=model_config_id, browser_type=browser_type)

    logger.info(f"DEBUG: Agent created successfully ({type(agent).__name__}), starting asyncio.run")
    return asyncio.run(agent.run_full_process(task_description, analysis_callback, step_callback, should_stop))

def generate_script_content_sync(task_description: str, mode='web', model_config_id=None):
    agent = BrowserAgent(execution_mode='text', model_config_id=model_config_id)
    return asyncio.run(agent.generate_script(task_description, mode))
