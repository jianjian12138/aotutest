from django.utils.deprecation import MiddlewareMixin
import json
import uuid
import logging
from django.http import JsonResponse
from rest_framework.response import Response
from django.core.serializers.json import DjangoJSONEncoder

logger = logging.getLogger(__name__)

class StandardResponseMiddleware(MiddlewareMixin):
    """
    V2.0 统一响应体防腐层中间件
    拦截所有 DRF 或 Django 返回的原生 Response，强制转换为统一企业级标准格式：
    {
        "code": 200,
        "message": "success",
        "data": { ... },
        "trace_id": "req-xxxx..."
    }
    """
    def process_request(self, request):
        request.trace_id = f"req-{uuid.uuid4().hex[:12]}"
        
    def process_response(self, request, response):
        # 排除 Swagger、静态文件、异步流等不需要包装的路由
        path = request.path_info
        if path.startswith('/admin') or path.startswith('/static') or path.startswith('/media') or 'swagger' in path or 'schema' in path:
            return response
            
        # 跳过 SSE 或 文件下载传输
        if response.get('Content-Type') in ['text/event-stream', 'application/octet-stream', 'application/zip']:
            return response

        # 仅针对 API 响应进行防腐包装
        if path.startswith('/api/') or path.startswith('/data-factory/') or path.startswith('/assistant/') or hasattr(response, 'data'):
            trace_id = getattr(request, 'trace_id', f"req-{uuid.uuid4().hex[:12]}")
            
            # 校验是否已被手工包裹 (防止嵌套包装)
            try:
                if hasattr(response, 'content') and response.content:
                    parsed = json.loads(response.content.decode('utf-8'))
                    if isinstance(parsed, dict) and 'code' in parsed and 'trace_id' in parsed:
                        return response
            except Exception:
                pass
            
            # 提取 payload
            data = None
            message = "success"
            code = response.status_code
            
            if hasattr(response, 'data'):
                # 针对 DRF Response
                data = response.data
                if code >= 400:
                    message = "error"
                    if isinstance(data, dict):
                        message = data.get('detail') or data.get('error') or "Request Failed"
            elif isinstance(response, JsonResponse) or getattr(response, 'headers', {}).get('Content-Type') == 'application/json':
                try:
                    data = json.loads(response.content.decode('utf-8'))
                    if code >= 400 and isinstance(data, dict):
                        message = data.get('error') or data.get('detail') or "Request Error"
                except Exception:
                    data = response.content.decode('utf-8', errors='ignore') if hasattr(response, 'content') else None
                    
            if code >= 400 and message == "success":
                message = "request failed"

            # 生成标准包裹
            std_wrapper = {
                "code": code,
                "message": message,
                "data": data,
                "trace_id": trace_id
            }
            
            if isinstance(response, Response):
                response.data = std_wrapper
                response.content = json.dumps(std_wrapper, cls=DjangoJSONEncoder, ensure_ascii=False).encode('utf-8')
                if 'Content-Length' in response:
                    del response['Content-Length']
                return response
            
            new_resp = JsonResponse(std_wrapper, status=code)
            if 'Content-Length' in response:
                del response['Content-Length']
            return new_resp
            
        return response

    def process_exception(self, request, exception):
        """捕获未被视图层处理的严重 Server Error 异常。

        安全要求：异常详情只入日志（可通过 trace_id 关联排查），
        绝不向客户端回传 str(exception)，防止内部路径/SQL/密钥泄露。
        """
        trace_id = getattr(request, 'trace_id', f"req-{uuid.uuid4().hex[:12]}")
        logger.exception(f"[{trace_id}] Unhandled Exception Captured by API Middleware:")

        std_wrapper = {
            "code": 500,
            "message": "服务器内部错误，请联系管理员并提供 trace_id 排查。",
            "data": None,
            "trace_id": trace_id
        }
        return JsonResponse(std_wrapper, status=500)


class AuditLogMiddleware(MiddlewareMixin):
    """
    阶段1.3 操作审计：对平台变更类 API 请求自动留痕。
    - 仅记录写操作（POST/PUT/PATCH/DELETE）；
    - 排除登录/登出、schema/docs、审计自身端点；
    - 仅当用户已认证（匿名写请求不应存在，若存在由其他权限层拦截）；
    - 写入失败被静默吞掉，不影响主流程。
    """
    # 不审计的路径前缀（认证/文档/审计自身）
    EXCLUDE_PREFIXES = (
        '/api/users/login/', '/api/users/logout/', '/api/users/register/',
        '/api/users/token/', '/api/docs/', '/api/schema/', '/api/redoc/',
        '/api/core/audit', '/api/audit',
    )
    METHOD_ACTION = {
        'POST': 'CREATE', 'PUT': 'UPDATE', 'PATCH': 'UPDATE', 'DELETE': 'DELETE',
    }

    def process_response(self, request, response):
        try:
            method = request.method
            if method not in self.METHOD_ACTION:
                return response
            path = request.path_info
            if any(path.startswith(p) for p in self.EXCLUDE_PREFIXES):
                return response
            if not path.startswith('/api/'):
                return response
            user = getattr(request, 'user', None)
            if not (user and user.is_authenticated):
                return response

            action = self.METHOD_ACTION[method]
            resource_type = path.strip('/').split('/')[1] if len(path.strip('/').split('/')) > 1 else path
            if response.status_code >= 500:
                # 服务端错误由 process_exception / 日志处理，这里不重复
                return response

            from apps.core_platform.models import AuditLog
            AuditLog.log(
                request=request,
                action=action,
                resource_type=resource_type,
                response_status=response.status_code,
                body_snippet=self._safe_body(request),
            )
        except Exception:
            logger.exception("AuditLogMiddleware 处理异常（已忽略）")
        return response

    @staticmethod
    def _safe_body(request):
        try:
            body = request.body
            if not body:
                return ''
            text = body.decode('utf-8', errors='ignore')
            # 脱敏常见敏感字段
            import re
            text = re.sub(r'("password"\s*:\s*")[^"]*(")', r'\1***\2', text)
            text = re.sub(r'("api_key"\s*:\s*")[^"]*(")', r'\1***\2', text)
            text = re.sub(r'("token"\s*:\s*")[^"]*(")', r'\1***\2', text)
            return text[:1000]
        except Exception:
            return ''