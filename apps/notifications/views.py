from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from apps.core_platform.permissions import TenantAwareViewSetMixin
from .models import NotificationConfig, NotificationLog
from .serializers import NotificationConfigSerializer, NotificationLogSerializer

class NotificationConfigViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    queryset = NotificationConfig.objects.all().order_by('-created_at')
    serializer_class = NotificationConfigSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['is_active', 'config_type']
    # 第六轮批次2：接入统一租户隔离——通知配置含 webhook 密钥（钉钉 secret 等）敏感数据，
    # 模型无 organization/project 字段，按创建人严格隔离（宁可收紧）
    org_field = 'created_by'

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

class NotificationLogViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    queryset = NotificationLog.objects.all().order_by('-created_at')
    serializer_class = NotificationLogSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status']
    # 第六轮批次2：接入统一租户隔离——NotificationLog 模型不含任何租户字段
    # （无 organization/project/created_by，task_id 为裸 IntegerField 无外键），
    # 日志含 webhook 机器人地址等敏感信息，不能豁免；按 mixin 设计 fail-closed：
    # 非管理员空集，管理员全量。待模型补充租户外键后再放开（已在报告中登记缺字段模型）。
