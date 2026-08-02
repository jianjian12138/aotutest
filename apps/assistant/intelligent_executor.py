import logging
import json
from .models import AIWorkflowConfig
from apps.requirement_analysis.models import AIModelConfig
from .mcp_service import MCPService
from .skills_service import SkillsService
from apps.knowledge_graph.services import KnowledgeGraphService

logger = logging.getLogger(__name__)

import requests

class IntelligentExecutor:
    """
    Intelligent Executor that decides how to handle a natural language command.
    It can route to MCP, Skills, Workflows, or LLM.
    """
    
    @staticmethod
    def execute(command, user, context=None):
        """
        Main entry point for executing a command.
        """
        if context is None:
            context = {}

        # 1. Search knowledge graph for context
        kg_context = KnowledgeGraphService.search(command)
        context["kg_context"] = kg_context.get("context_text", "")
        
        # 获取模式和项目
        context.get('test_mode', 'api')
        context.get('project_id')
        context.get('device_id')

        # 2. Search for active configurations
        configs = AIWorkflowConfig.objects.filter(is_active=True)
        model_configs = AIModelConfig.objects.filter(is_active=True)
        
        # 2. Heuristic or LLM-based routing
        # For now, let's implement a simple routing logic:
        # If the command matches a Skill name, run that Skill.
        # If it matches an MCP tool name, run that MCP tool.
        # Otherwise, use the first active Dify/Coze workflow or AI model.
        
        # Try Skills
        skill_configs = configs.filter(provider='skills')
        for skill in skill_configs:
            if skill.name.lower() in command.lower() or (skill.additional_config.get('original_name') and skill.additional_config.get('original_name').lower() in command.lower()):
                logger.info(f"Matched Skill: {skill.name}")
                
                # Check if it's an instructional skill
                if skill.additional_config.get('type') == 'instructional':
                    return {
                        "type": "instructional",
                        "instructions": skill.additional_config.get('instructions'),
                        "skill_name": skill.name
                    }
                
                # Otherwise, it's a Python functional skill
                return SkillsService.execute_skill(skill.additional_config.get('code'), context)
        
        # Try MCP
        mcp_configs = configs.filter(provider='mcp')
        for mcp in mcp_configs:
            try:
                tools = MCPService.get_tools(mcp.api_url, mcp.api_key)
                if "tools" in tools:
                    for tool in tools["tools"]:
                        if tool['name'].lower() in command.lower():
                            logger.info(f"Routing to MCP Tool: {tool['name']}")
                            return {"type": "mcp", "tool": tool, "mcp_config_id": mcp.id}
            except Exception as e:
                logger.error(f"Error fetching MCP tools: {e}")
                continue

        # Try Workflows (Dify/n8n)
        workflow_configs = configs.filter(provider__in=['dify', 'n8n', 'coze'])
        if workflow_configs.exists():
            config = workflow_configs.first()
            logger.info(f"Routing to Workflow: {config.name}")
            return IntelligentExecutor._call_workflow(config, command, user)
            
        # Try AI Model Configs
        if model_configs.exists():
            config = model_configs.first()
            logger.info(f"Routing to AI Model: {config.name}")
            return {"error": "continue_to_ai", "model_config_id": config.id}
            
        return {"error": "No suitable executor found for the command."}

    @staticmethod
    def _call_workflow(config, command, user):
        """Helper to call Dify/n8n workflows."""
        api_url = config.api_url.rstrip('/')
        headers = {'Content-Type': 'application/json'}
        if config.api_key:
            headers['Authorization'] = f'Bearer {config.api_key}'
            
        payload = {
            "inputs": {"query": command},
            "query": command,
            "user": str(user.id)
        }
        
        try:
            # Simple POST for now, logic varies by provider
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            return {"type": "workflow", "data": response.json()}
        except Exception as e:
            return {"error": str(e)}
