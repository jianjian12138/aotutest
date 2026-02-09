from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GlobalParameterViewSet, CommonMethodViewSet

router = DefaultRouter()
router.register(r'parameters', GlobalParameterViewSet)
router.register(r'common-methods', CommonMethodViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
