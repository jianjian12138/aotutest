from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TestCaseReviewViewSet, TestCaseReviewCommentViewSet, ReviewTemplateViewSet

router = DefaultRouter()
router.register(r'reviews', TestCaseReviewViewSet, basename='reviews')
router.register(r'review-comments', TestCaseReviewCommentViewSet, basename='review-comments')
router.register(r'review-templates', ReviewTemplateViewSet, basename='review-templates')

urlpatterns = [
    path('', include(router.urls)),
]