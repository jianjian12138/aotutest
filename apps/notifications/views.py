from rest_framework import viewsets
from .models import NotificationConfig, NotificationLog
from .serializers import NotificationConfigSerializer, NotificationLogSerializer

class NotificationConfigViewSet(viewsets.ModelViewSet):
    queryset = NotificationConfig.objects.all().order_by('-created_at')
    serializer_class = NotificationConfigSerializer
    filterset_fields = ['is_active', 'config_type']

class NotificationLogViewSet(viewsets.ModelViewSet):
    queryset = NotificationLog.objects.all().order_by('-created_at')
    serializer_class = NotificationLogSerializer
    filterset_fields = ['status']
