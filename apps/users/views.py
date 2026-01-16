from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import login, logout
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import User, UserProfile
from .serializers import UserSerializer, UserCreateSerializer, LoginSerializer, UserProfileSerializer

# JWT 相关导入
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_current_user(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import login, logout

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_current_user(request):
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(generics.CreateAPIView):
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

    return Response({
        'user': UserSerializer(user).data,
        'access': access_token,       # JWT access token
        'refresh': refresh_token,     # JWT refresh token
        'message': '登录成功'
    })

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
        except:
            pass

        logout(request)

    return Response({'message': '退出成功'})

@api_view(['GET'])
def profile_view(request):
    if not request.user.is_authenticated:
        return Response({'error': '未登录'}, status=status.HTTP_401_UNAUTHORIZED)
    
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

class UserListView(generics.ListCreateAPIView):
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]