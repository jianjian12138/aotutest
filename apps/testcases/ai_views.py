from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import AITestCaseGenerator, AITestCaseAnalyzer
from apps.core_platform.models import Project

class AITestCaseGenerateView(APIView):
    async def post(self, request, *args, **kwargs):
        requirement_text = request.data.get("requirement", "")
        project_id = request.data.get("project_id")
        
        if not requirement_text or not project_id:
            return Response({"error": "Missing requirement or project_id"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            from asgiref.sync import sync_to_async
            project = await sync_to_async(Project.objects.get)(id=project_id)
            cases = await AITestCaseGenerator.generate_cases_from_requirement(requirement_text, project, request.user)
            return Response({"success": True, "created_count": len(cases), "cases": cases}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AITestCaseAnalyzeView(APIView):
    async def post(self, request, *args, **kwargs):
        cases_data = request.data.get("cases_data", [])
        if not cases_data:
             return Response({"error": "Missing cases_data array"}, status=status.HTTP_400_BAD_REQUEST)
             
        try:
            analysis_result = await AITestCaseAnalyzer.analyze_coverage(cases_data)
            return Response({"success": True, "analysis": analysis_result}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
