from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import AIReportAnalyzer

class AIReportAnalyzeView(APIView):
    async def post(self, request, *args, **kwargs):
        suite_run_results = request.data.get("suite_run_results", [])
        if not suite_run_results:
             return Response({"error": "Missing suite_run_results array"}, status=status.HTTP_400_BAD_REQUEST)
             
        try:
            analysis_result = await AIReportAnalyzer.analyze_execution_report(suite_run_results)
            return Response({"success": True, "analysis": analysis_result}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
