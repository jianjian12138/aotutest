from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from django.contrib.auth import get_user_model

User = get_user_model()

@csrf_exempt
@require_http_methods(["POST"])
def test_register(request):
    try:
        data = json.loads(request.body)
        
        # 检查用户名是否已存在
        if User.objects.filter(username=data.get('username')).exists():
            return JsonResponse({
                'success': False,
                'error': '用户名已存在'
            }, status=400)
        
        # 简单的用户创建
        user = User.objects.create_user(
            username=data.get('username'),
            email=data.get('email', ''),
            password=data.get('password'),
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            department=data.get('department', ''),
            position=data.get('position', '')
        )
        
        # 创建token - 延迟导入以避免应用初始化问题
        try:
            from rest_framework.authtoken.models import Token
            token, created = Token.objects.get_or_create(user=user)
            token_key = token.key
        except ImportError:
            # 如果Token模型不可用，返回一个临时token
            token_key = f"temp_token_{user.id}"
        
        return JsonResponse({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
            },
            'token': token_key
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)