from django.urls import path
from . import views

urlpatterns = [
    path('', views.VersionListCreateView.as_view(), name='version-list'),
    path('<int:pk>/', views.VersionDetailView.as_view(), name='version-detail'),
    path('projects/<int:project_id>/versions/', views.get_project_versions, name='project-versions'),
]
