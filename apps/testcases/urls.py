from django.urls import path, include
from rest_framework.routers import SimpleRouter
from . import views

router = SimpleRouter()
router.register(r'modules', views.TestCaseModuleViewSet, basename='testcase-module')

urlpatterns = [
    path('', include(router.urls)),
    # 测试用例相关
    path('', views.TestCaseListCreateView.as_view(), name='testcase-list'),
    path('<int:pk>/', views.TestCaseDetailView.as_view(), name='testcase-detail'),
    path('import/', views.ImportTestCaseView.as_view(), name='testcase-import'),
    path('export/', views.ExportTestCaseView.as_view(), name='testcase-export'),
    
    # AI 增强功能端点
    path('ai/generate/', __import__('apps.testcases.ai_views', fromlist=['AITestCaseGenerateView']).AITestCaseGenerateView.as_view(), name='ai-testcase-generate'),
    path('ai/analyze/', __import__('apps.testcases.ai_views', fromlist=['AITestCaseAnalyzeView']).AITestCaseAnalyzeView.as_view(), name='ai-testcase-analyze'),
]