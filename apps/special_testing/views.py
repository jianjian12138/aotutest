from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status


class DashboardTasksView(APIView):
    """专项测试任务看板（真实执行能力本期未交付）。

    返回 200 + 结构化 not_implemented 负载（含 planned 规划项），
    前端据此渲染友好占位，避免 api.js 拦截器把 5xx 当作「服务器错误」弹红条。
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            'status': 'not_implemented',
            'message': '专项测试（MQTT / Monkey / Redis / Kafka）执行能力本期未交付，敬请期待。',
            'planned': [
                {'key': 'MQTT', 'name': 'MQTT 测试', 'desc': 'IoT 设备通信测试'},
                {'key': 'MONKEY', 'name': 'Monkey 压测', 'desc': 'Android 稳定性测试'},
                {'key': 'REDIS', 'name': 'Redis 工具', 'desc': '缓存读写验证'},
                {'key': 'KAFKA', 'name': 'Kafka 工具', 'desc': '消息队列验证'},
            ],
            'eta': '规划中',
        }, status=status.HTTP_200_OK)
