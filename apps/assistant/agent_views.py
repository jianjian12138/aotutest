import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .agent_factory import AgentFactory

logger = logging.getLogger(__name__)

class AgentExecuteView(APIView):
    async def post(self, request, *args, **kwargs):
        agent_type = request.data.get("agent_type", "master")
        prompt = request.data.get("prompt", "")
        project_id = request.data.get("project_id")
        override_llm_id = request.data.get("override_llm_id")
        override_skill_ids = request.data.get("override_skill_ids")
        
        if not prompt:
            return Response({"error": "Prompt is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        from apps.assistant.models import AgentProfile, AgentSkill
        from apps.assistant.agent_framework import BaseAgent, BaseSkill
        
        try:
            profile = AgentProfile.objects.prefetch_related('skills').get(name=agent_type)
        except AgentProfile.DoesNotExist:
            return Response({"error": f"AgentProfile '{agent_type}' not found. Please configure it in the Configuration Center."}, status=status.HTTP_404_NOT_FOUND)

        if not profile.is_active:
            return Response({"error": f"AgentProfile '{agent_type}' is disabled."}, status=status.HTTP_400_BAD_REQUEST)
            
        agent = BaseAgent(
            name=profile.name, 
            system_prompt=profile.system_prompt,
            llm_config_id=override_llm_id if override_llm_id else (profile.llm_config_id if profile.llm_config else None)
        )
        
        # Create dynamic skills
        class DynamicSkill(BaseSkill):
            def __init__(self, s):
                self._name = s.name
                self._description = s.description
                self.code = s.executor_code
                
            @property
            def name(self): return self._name
            
            @property
            def description(self): return self._description
            
            async def run(self, **kwargs):
                from asgiref.sync import sync_to_async
                from apps.assistant.skills_service import SkillsService
                # Execute user-configured python code via SkillsService sandbox
                result = await sync_to_async(SkillsService.execute_skill)(self.code, kwargs)
                return result

        skills_to_use = profile.skills.filter(is_active=True)
        if override_skill_ids:
            skills_to_use = AgentSkill.objects.filter(id__in=override_skill_ids, is_active=True)

        for s in skills_to_use:
            agent.register_skill(DynamicSkill(s))
        
        try:
            from asgiref.sync import sync_to_async
            from apps.core_platform.models import Project
            
            project = None
            if project_id:
                project = await sync_to_async(Project.objects.get)(id=project_id)
                
            result = await agent.execute(prompt, project=project, user=request.user)
            return Response({"success": True, "result": result}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from django.http import StreamingHttpResponse
import json
from asgiref.sync import sync_to_async

class AgentExecuteStreamView(APIView):
    """
    Streaming Endpoint for Agent Executions (Server-Sent Events)
    """
    async def post(self, request, *args, **kwargs):
        agent_type = request.data.get("agent_type", "master")
        prompt = request.data.get("prompt", "")
        project_id = request.data.get("project_id")
        override_llm_id = request.data.get("override_llm_id")
        override_skill_ids = request.data.get("override_skill_ids")
        
        if not prompt:
            return Response({"error": "Prompt is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        from apps.assistant.models import AgentProfile, AgentSkill
        from apps.assistant.agent_framework import BaseAgent, BaseSkill
        
        try:
            profile = await sync_to_async(lambda: AgentProfile.objects.prefetch_related('skills').get(name=agent_type))()
        except AgentProfile.DoesNotExist:
            return Response({"error": f"AgentProfile '{agent_type}' not found."}, status=status.HTTP_404_NOT_FOUND)

        if not profile.is_active:
            return Response({"error": f"AgentProfile '{agent_type}' is disabled."}, status=status.HTTP_400_BAD_REQUEST)
            
        agent = BaseAgent(
            name=profile.name, 
            system_prompt=profile.system_prompt,
            llm_config_id=override_llm_id if override_llm_id else (profile.llm_config_id if profile.llm_config else None)
        )
        
        class DynamicSkill(BaseSkill):
            def __init__(self, s):
                self._name = s.name
                self._description = s.description
                self.code = s.executor_code
                
            @property
            def name(self): return self._name
            @property
            def description(self): return self._description
            
            async def run(self, **kwargs):
                from asgiref.sync import sync_to_async
                from apps.assistant.skills_service import SkillsService
                result = await sync_to_async(SkillsService.execute_skill)(self.code, kwargs)
                return result

        skills_to_use = await sync_to_async(lambda: list(profile.skills.filter(is_active=True)))()
        if override_skill_ids:
            skills_to_use = await sync_to_async(lambda: list(AgentSkill.objects.filter(id__in=override_skill_ids, is_active=True)))()

        for s in skills_to_use:
            agent.register_skill(DynamicSkill(s))
        
        from apps.core_platform.models import Project
        project = None
        if project_id:
            project = await sync_to_async(Project.objects.get)(id=project_id)
            
        async def event_stream():
            try:
                async for chunk in agent.execute_stream(prompt, project=project, user=request.user):
                    yield f"data: {json.dumps(chunk)}\\n\\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\\n\\n"
            finally:
                yield "data: [DONE]\\n\\n"
                
        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        return response
