from rest_framework import serializers
from django.contrib.auth import authenticate
from ..models import User, UserProfile, Organization, Role
from ..masking import PIIMaskMixin

class OrganizationSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ('id', 'name', 'code')

class RoleSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ('id', 'name', 'code')

class UserSimpleSerializer(PIIMaskMixin, serializers.ModelSerializer):
    # 第六轮批次2：email 属 PII，非本人/非管理员输出掩码
    pii_masked_fields = ('email',)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'avatar')

class UserSerializer(PIIMaskMixin, serializers.ModelSerializer):
    organization = OrganizationSimpleSerializer(read_only=True)
    roles = RoleSimpleSerializer(many=True, read_only=True)
    # 第六轮批次2：email/phone 属 PII，非本人/非管理员输出掩码
    pii_masked_fields = ('email', 'phone')

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                 'avatar', 'phone', 'department', 'position', 'is_active',
                 'is_staff', 'is_superuser', 'organization', 'roles',
                 'date_joined', 'created_at', 'updated_at']
        read_only_fields = ['id', 'date_joined', 'created_at', 'updated_at']

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm',
                 'first_name', 'last_name', 'phone', 'department', 'position']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("密码不一致")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('用户名或密码错误')
            if not user.is_active:
                raise serializers.ValidationError('用户已被禁用')
        else:
            raise serializers.ValidationError('用户名和密码不能为空')
        
        attrs['user'] = user
        return attrs

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        # 显式白名单（D2 P0 修复：取代 fields='__all__'，不暴露 user 外键之外的隐式字段）
        fields = ['id', 'theme', 'language', 'timezone', 'notifications']