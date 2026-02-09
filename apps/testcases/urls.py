from django.urls import path
from . import views

urlpatterns = [
    # 测试用例相关
    path('', views.TestCaseListCreateView.as_view(), name='testcase-list'),
    path('<int:pk>/', views.TestCaseDetailView.as_view(), name='testcase-detail'),
    path('import/', views.ImportTestCaseView.as_view(), name='testcase-import'),
    path('export/', views.ExportTestCaseView.as_view(), name='testcase-export'),
]