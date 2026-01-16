from django.utils.deprecation import MiddlewareMixin

class DisableCSRFMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # 对所有API路径禁用CSRF检查
        if request.path.startswith('/api/'):
            setattr(request, '_dont_enforce_csrf_checks', True)