# Trigger reload 1
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

admin.site.site_title = 'Testing 管理后台'
admin.site.site_header = 'Testing 后台系统'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    path('api/', include('apps.core_platform.urls')),

    # 路线三 · Phase 0 权限制高点：租户功能开关（agent 测评 / LLM 测试 等能力按租户开通）
    path('api/tenant-features/', include('apps.tenant_features.urls')),

    path('api/testcases/', include('apps.testcases.urls')),
    path('api/testsuites/', include('apps.testsuites.urls')),
    path('api/executions/', include('apps.executions.urls')),
    path('api/reports/', include('apps.reports.urls')),
    path('api/reviews/', include('apps.reviews.urls')),

    path('api/assistant/', include('apps.assistant.urls')),

    path('api/requirement-analysis/', include('apps.requirement_analysis.urls')),
    path('api/ui-automation/', include('apps.ui_automation.urls')),
    path('api/', include('apps.api_testing.urls')),
    path('api/', include('apps.performance_test.urls')),
    path('api/', include('apps.data_factory.urls')),
    path('api/', include('apps.strix_security.urls')),
    path('api/scheduler/', include('apps.scheduler.urls')),
    path('api/knowledge-graph/', include('apps.knowledge_graph.urls')),

    path('api/special-testing/', include('apps.special_testing.urls')),
    path('api/cicd/', include('apps.cicd.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/defects/', include('apps.defects.urls')),
    
    # API 适配层 - 保持对旧 API 的兼容性
    path('api/', include('apps.adapter.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
