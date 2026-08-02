from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .workflow_agent import AgenticTestOrchestrator
from apps.core_platform.models import Project

class AgenticWorkflowRunView(APIView):
    async def post(self, request, *args, **kwargs):
        natural_language_command = request.data.get("command", "")
        project_id = request.data.get("project_id")
        
        if not natural_language_command or not project_id:
             return Response({"error": "Missing command or project_id"}, status=status.HTTP_400_BAD_REQUEST)
             
        try:
            from asgiref.sync import sync_to_async
            project = await sync_to_async(Project.objects.get)(id=project_id)
            
            orchestrator = AgenticTestOrchestrator(project, request.user)
            workflow_result = await orchestrator.execute_task(natural_language_command)
            return Response({"success": True, "result": workflow_result}, status=status.HTTP_200_OK)
        except NotImplementedError:
            return Response(
                {'error': '该能力本期未交付', 'status': 'not_implemented'},
                status=status.HTTP_501_NOT_IMPLEMENTED,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
