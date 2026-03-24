from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.utils import timezone
from datetime import timedelta

class DashboardTasksView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        
        # Injecting mock infrastructure test cases targeting the platform itself
        mock_tasks = [
            {
                "id": 1,
                "config_name": "AI引擎长链接断线重连拨测",
                "protocol": "MQTT",
                "status": "RUNNING",
                "created_at": (now - timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "id": 2,
                "config_name": "应用层缓存击穿防御演练",
                "protocol": "Redis",
                "status": "SUCCESS",
                "created_at": (now - timedelta(hours=1, minutes=12)).strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "id": 3,
                "config_name": "调度中间件消息积压水位压测",
                "protocol": "Kafka",
                "status": "PENDING",
                "created_at": (now - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")
            },
            {
                "id": 4,
                "config_name": "WebUI Monkey 随机狂暴点击测试",
                "protocol": "Monkey",
                "status": "FAILED",
                "created_at": (now - timedelta(hours=3, minutes=45)).strftime("%Y-%m-%d %H:%M:%S")
            }
        ]
        
        return Response({
            "results": mock_tasks,
            "count": len(mock_tasks)
        })
