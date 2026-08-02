from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationConfigViewSet, NotificationLogViewSet

router = DefaultRouter()
router.register(r'notifications', NotificationConfigViewSet)
router.register(r'logs', NotificationLogViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
