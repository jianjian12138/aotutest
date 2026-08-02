from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.conf import settings
from django.contrib.auth import login, logout
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from ..models import User, UserProfile
from ..permissions import IsAdminOrReadOnly, TenantAwareViewSetMixin
from ..serializers.users import UserSerializer, UserCreateSerializer, LoginSerializer, UserProfileSerializer

# JWT 相关导入
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken


def _set_refresh_cookie(response, refresh_token):
    """统一签发 httpOnly Refresh Cookie（login 与 refresh 共用）。"""
    response.set_cookie(
        'refresh_token',
        refresh_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite='Strict',
        max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
    )


class CookieTokenRefreshView(TokenRefreshView):
    """第四轮整改（P0-新D）：支持从 httpOnly Cookie 读取 refresh token 的续期视图。

    - 请求体缺少 refresh 时，回退读取 Cookie（restoreSession 静默续期链路）；
    - ROTATE_REFRESH_TOKENS=True 时，把轮换后的新 refresh 回写 Cookie。
    """

    def post(self, request, *args, **kwargs):
        data = dict(request.data.items()) if hasattr(request.data, 'items') else {}
        if not data.get('refresh'):
            cookie_token = request.COOKIES.get('refresh_token')
            if cookie_token:
                data['refresh'] = cookie_token
        serializer = self.get_serializer(data=data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0]) from e
        response = Response(serializer.validated_data, status=status.HTTP_200_OK)
        new_refresh = serializer.validated_data.get('refresh')
        if new_refresh:
            _set_refresh_cookie(response, new_refresh)
        return response

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_current_user(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(generics.CreateAPIView):
    # 第六轮批次2：平台级资源显式豁免。注册端点 AllowAny、匿名访问，此时不存在租户
    # 上下文可供过滤；且 CreateAPIView 只写不读（queryset 仅为 DRF 框架要求的占位），
    # 不向外输出任何用户列表数据，无跨租户读取面。
    tenant_scope_exempt = True
    tenant_scope_exempt_reason = '公开注册端点（AllowAny），匿名请求无租户上下文；CreateAPIView 仅创建不列举，queryset 为框架占位，无跨租户数据读取面'
    queryset = User.objects.all().order_by('username')
    serializer_class = UserCreateSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # 安全地创建token
        try:
            from rest_framework.authtoken.models import Token
            token, created = Token.objects.get_or_create(user=user)
            token_key = token.key
        except ImportError:
            token_key = f"temp_token_{user.id}"
        
        return Response({
            'user': UserSerializer(user).data,
            'token': token_key
        }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@csrf_exempt
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.validated_data['user']
    login(request, user)

    # JWT Token (优先使用JWT)
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)

    response = Response({
        'user': UserSerializer(user).data,
        'access': access_token,       # JWT access token
        'refresh': refresh_token,     # JWT refresh token
        'message': '登录成功'
    })
    # 签发 httpOnly Refresh Cookie：供前端 restoreSession() 在刷新/401 时静默续期
    # （修复第三轮发现的 P0-新D：此前后端从不签发 Cookie，导致续期链路整体失效）
    _set_refresh_cookie(response, refresh_token)
    return response

@api_view(['POST'])
@csrf_exempt
def logout_view(request):
    """用户退出登录，将refresh token加入黑名单"""
    if request.user.is_authenticated:
        try:
            # 尝试将refresh token加入黑名单
            refresh_token = request.data.get('refresh')
            if refresh_token:
                from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
                from rest_framework_simplejwt.tokens import RefreshToken as JWTRefreshToken
                try:
                    token = JWTRefreshToken(refresh_token)
                    token.blacklist()
                except Exception as e:
                    print(f"Blacklist error: {e}")
        except Exception as e:
            print(f"Logout error: {e}")

        # 清除旧的auth token（向后兼容）
        try:
            request.user.auth_token.delete()
        except Exception:
            pass

        logout(request)

    return Response({'message': '退出成功'})

@api_view(['GET'])
def profile_view(request):
    if not request.user.is_authenticated:
        return Response({'error': '未登录'}, status=status.HTTP_401_UNAUTHORIZED)
    
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

class UserListView(TenantAwareViewSetMixin, generics.ListCreateAPIView):
    """用户列表（第四轮整改 P0-新A：管理员可见全量；普通用户仅可见自己，防 PII 泄露）。

    # 第六轮批次2：显式声明自管租户过滤，每个 return 分支收口 _apply_tenant_scope。
    """
    tenant_scope_self_managed = True
    tenant_scope_self_managed_reason = (
        '自定义 get_queryset 对非管理员只返回 id=自己这一行（管理员全量，沿用原语义），是最严的用户级边界；'
        'User 模型会被自动解析为 organization 过滤，一旦叠加，同组织用户即可互相列出对方的邮箱等 PII，'
        '相对原"仅可见自己"是可见性放宽；且注册用户默认无组织，org 过滤还会让其连自己都看不到'
    )
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        qs = self.queryset.all()
        if user.is_staff or user.is_superuser:
            return self._apply_tenant_scope(qs)
        return self._apply_tenant_scope(qs.filter(id=user.id))

class UserDetailView(TenantAwareViewSetMixin, generics.RetrieveUpdateDestroyAPIView):
    """用户详情（第四轮整改 P0-新A：普通用户仅能访问自己；写操作仅管理员）。

    # 第六轮批次2：显式声明自管租户过滤，每个 return 分支收口 _apply_tenant_scope。
    """
    tenant_scope_self_managed = True
    tenant_scope_self_managed_reason = (
        '同 UserListView：非管理员仅能取到 id=自己的对象，他人 id 一律 404（fail-closed），严于组织级隔离；'
        '叠加自动 organization 过滤会让同组织用户互相读取详情 PII（放宽），并使无组织用户读不到自己'
    )
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        qs = self.queryset.all()
        if user.is_staff or user.is_superuser:
            return self._apply_tenant_scope(qs)
        return self._apply_tenant_scope(qs.filter(id=user.id))