from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TenantFeatureViewSet

router = DefaultRouter()
router.register(r'features', TenantFeatureViewSet, basename='tenant-features')

urlpatterns = [
    path('', include(router.urls)),
]
