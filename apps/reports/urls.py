from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TestReportViewSet

router = DefaultRouter()
router.register(r'reports', TestReportViewSet, basename='reports')

urlpatterns = [
    path('', include(router.urls)),
]