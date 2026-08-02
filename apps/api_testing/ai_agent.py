import logging
import asyncio
import json
import re
import os
import requests
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from apps.requirement_analysis.models import AIModelConfig

logger = logging.getLogger('django')

class ApiAgent:
    def __init__(self, execution_mode='api', case_name=None, model_config_id=None):
        self.execution_mode = execution_mode
        self.case_name = case_name or "API Adhoc Task"
        
        # Load Config
        config_obj = None
        if model_config_id:
            try:
                config_obj = AIModelConfig.objects.get(id=model_config_id)
            except AIModelConfig.DoesNotExist:
                logger.warning(f"Provided model_config_id {model_config_id} not found")
        
        if not config_obj:
            # Fallback
            config_obj = AIModelConfig.objects.filter(is_active=True).first()
            
        self.api_key = config_obj.api_key if config_obj else os.getenv('AUTH_TOKEN')
        self.base_url = config_obj.base_url if config_obj else os.getenv('BASE_URL')
        self.model_name = config_obj.model_name if config_obj else os.getenv('MODEL_NAME')
        
        if not self.api_key:
            raise ValueError("No API Key found for API Agent")

        self.llm = ChatOpenAI(
            model=self.model_name,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=0.0
        )
        
        # Context to store variables across steps (e.g. tokens)
        self.context = {}

    async def analyze_task(self, task_description: str):
        """Analyze task and break it down into steps"""
        steps = []
        try:
            prompt = (
                f"Break down this API test task into sequential executable steps.\n"
                f"Task: {task_description}\n"
                f"Output: A raw JSON list of strings. No markdown. Just the JSON array.\n"
                f"Example: [\"Login to system\", \"Get user profile\", \"Logout\"]\n"
            )
            response = await self.llm.ainvoke(prompt)
            content = response.content.strip()
            
            # Clean Markdown
            content = re.sub(r'^```json\s*', '', content)
            content = re.sub(r'^```\s*', '', content)
            content = re.sub(r'\s*```$', '', content)
            
            try:
                match = re.search(r'\[.*\]', content, re.DOTALL)
                if match:
                    steps = json.loads(match.group(0))
            except Exception as e:
                logger.warning(f"Failed to parse LLM steps: {e}")
                
            if not steps:
                # Fallback splitting
                steps = [s.strip() for s in task_description.split('\n') if s.strip()]
                
        except Exception as e:
            logger.warning(f"LLM analysis failed: {e}")
            steps = [task_description]
            
        # Format steps
        formatted_steps = []
        for i, s in enumerate(steps):
            desc = s
            # Remove numbering
            desc = re.sub(r'^\s*\d+[\.\s、:：]+', '', desc).strip()
            if desc:
                formatted_steps.append({'id': i+1, 'description': desc, 'status': 'pending'})
                
        return formatted_steps

    async def run_task(self, task_description: str, planned_tasks=None, callback=None, should_stop=None):
        if callback:
             await self._send_log(callback, f"Initializing API Agent... (Model: {self.model_name})\n")

        if not planned_tasks:
             planned_tasks = await self.analyze_task(task_description)
             # Note: Caller usually handles analysis callback, but we can't easily update it here 
             # unless we have a specific callback for it.
             # Assuming run_full_process handles the initial analysis update.

        for task in planned_tasks:
            if should_stop and (await should_stop() if asyncio.iscoroutinefunction(should_stop) else should_stop()):
                await self._send_log(callback, "\n[System] Task stopped by user.\n")
                break
                
            task_desc = task['description']
            task_id = task['id']
            
            await self._send_log(callback, f"\n[Step {task_id}] {task_desc}\n")
            await self._update_task_status(callback, task_id, 'in_progress')
            
            try:
                # Generate Request
                req_params = await self._generate_request(task_desc)
                
                if not req_params:
                    await self._send_log(callback, f"⚠️ Skip: Could not generate valid API request parameters.\n")
                    await self._update_task_status(callback, task_id, 'failed')
                    continue
                    
                await self._send_log(callback, f"Request: {req_params.get('method', 'GET')} {req_params.get('url')}\n")
                if req_params.get('body'):
                    await self._send_log(callback, f"Body: {json.dumps(req_params.get('body'), ensure_ascii=False)}\n")
                
                # Execute Request
                response = await self._execute_request(req_params)
                
                await self._send_log(callback, f"Response: {response['status_code']} {response['reason']}\n")
                if response['body']:
                     # Truncate body log
                     body_str = str(response['body'])
                     if len(body_str) > 500:
                         body_str = body_str[:500] + "...(truncated)"
                     await self._send_log(callback, f"Data: {body_str}\n")
                
                # Update Context (Extract variables)
                # Simplified: Save entire response body to context if it's JSON
                if isinstance(response['body'], dict):
                    self.context.update(response['body'])
                    # Flatten context for easier access
                    for k, v in response['body'].items():
                        if isinstance(v, (str, int, float, bool)):
                            self.context[k] = v
                
                await self._update_task_status(callback, task_id, 'completed')
                
            except Exception as e:
                logger.error(f"Task execution failed: {e}")
                await self._send_log(callback, f"❌ Error: {str(e)}\n")
                await self._update_task_status(callback, task_id, 'failed')
                
        return {"status": "finished"}

    async def _generate_request(self, task_desc):
        """Generate API request parameters from task description using LLM"""
        prompt = (
            f"Generate an API request for the following task.\n"
            f"Task: {task_desc}\n"
            f"Current Context (Variables): {json.dumps(self.context, default=str)}\n"
            f"Output: A JSON object with fields: method, url, headers (dict), body (dict/str), params (dict).\n"
            f"Example Output: {{\"method\": \"POST\", \"url\": \"https://api.example.com/login\", \"body\": {{\"username\": \"test\"}}}}\n"
            f"IMPORTANT: If the task implies using a variable from context (like token), include it in headers or body.\n"
            f"IMPORTANT: If URL is not provided in task, guess a reasonable placeholder or use context.\n"
            f"Return ONLY the JSON object."
        )
        
        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content.strip()
            # Clean Markdown
            content = re.sub(r'^```json\s*', '', content)
            content = re.sub(r'^```\s*', '', content)
            content = re.sub(r'\s*```$', '', content)
            
            # Find JSON
            match = re.search(r'(\{[\s\S]*\})', content)
            if match:
                return json.loads(match.group(1))
        except Exception as e:
            logger.warning(f"Failed to generate request: {e}")
        return None

    async def _execute_request(self, params):
        """Execute HTTP request"""
        method = params.get('method', 'GET').upper()
        url = params.get('url')
        headers = params.get('headers', {})
        body = params.get('body')
        query_params = params.get('params')
        
        if not url:
            raise ValueError("URL is missing")
            
        # Handle Body
        json_body = None
        data_body = None
        if isinstance(body, dict):
            json_body = body
        else:
            data_body = body
            
        try:
            # Run in thread pool to avoid blocking asyncio loop
            loop = asyncio.get_running_loop()
            resp = await loop.run_in_executor(
                None, 
                lambda: requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=query_params,
                    json=json_body,
                    data=data_body,
                    timeout=30
                )
            )
            
            # Parse Response
            try:
                resp_body = resp.json()
            except Exception:
                resp_body = resp.text
                
            return {
                'status_code': resp.status_code,
                'reason': resp.reason,
                'body': resp_body,
                'headers': dict(resp.headers)
            }
        except Exception as e:
            raise e

    async def _send_log(self, callback, content):
        if callback:
            data = {'type': 'log', 'content': content}
            if asyncio.iscoroutinefunction(callback): await callback(data)
            else: callback(data)

    async def _update_task_status(self, callback, task_id, status):
        if callback:
            data = {'task_id': task_id, 'status': status}
            if asyncio.iscoroutinefunction(callback): await callback(data)
            else: callback(data)

    async def generate_api_case_data(self, task_description):
        """Generate structured API test case data from description"""
        prompt = (
            f"Convert the following natural language test scenario into a structured API test case JSON.\n"
            f"Scenario: {task_description}\n"
            f"Output Format (JSON List of Steps):\n"
            f"[\n"
            f"  {{\n"
            f"    \"name\": \"Step Name\",\n"
            f"    \"description\": \"Step Description\",\n"
            f"    \"method\": \"GET/POST/PUT/DELETE\",\n"
            f"    \"url\": \"http://...\",\n"
            f"    \"headers\": {{}},\n"
            f"    \"body\": {{}},\n"
            f"    \"params\": {{}},\n"
            f"    \"assertions\": [ {{\"source\": \"status_code\", \"operator\": \"equals\", \"value\": 200}} ],\n"
            f"    \"extract\": [ {{\"name\": \"token\", \"source\": \"body\", \"expression\": \"token\"}} ]\n"
            f"  }}\n"
            f"]\n"
            f"Return ONLY the JSON array."
        )
        
        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content.strip()
            
            # Clean Markdown
            content = re.sub(r'^```json\s*', '', content)
            content = re.sub(r'^```\s*', '', content)
            content = re.sub(r'\s*```$', '', content)
            
            return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to generate API case data: {e}")
            return []

# Exported function
def run_api_task_sync(task_description: str, analysis_callback=None, step_callback=None, should_stop=None, model_config_id=None):
    agent = ApiAgent(execution_mode='api', model_config_id=model_config_id)
    
    # 1. Analyze
    planned_tasks = asyncio.run(agent.analyze_task(task_description))
    
    if analysis_callback:
        # Wrap in async call if needed, or just call if sync
        # Here we assume analysis_callback is async as per views.py usage
        asyncio.run(analysis_callback(planned_tasks))
        
    # 2. Run
    return asyncio.run(agent.run_task(task_description, planned_tasks, step_callback, should_stop))

def generate_api_case_data_sync(task_description: str, model_config_id=None):
    agent = ApiAgent(execution_mode='api', model_config_id=model_config_id)
    return asyncio.run(agent.generate_api_case_data(task_description))
