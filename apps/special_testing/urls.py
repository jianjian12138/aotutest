from django.urls import path
from .views import DashboardTasksView

urlpatterns = [
    path('tasks/', DashboardTasksView.as_view(), name='special-testing-tasks'),
]
