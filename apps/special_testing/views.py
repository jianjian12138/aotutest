from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status


class DashboardTasksView(APIView):
    """专项测试任务看板（真实执行能力本期未交付，统一返回 501）"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(
            {'error': '该能力本期未交付', 'status': 'not_implemented'},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )
