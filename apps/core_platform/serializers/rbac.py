"""阶段1 RBAC / 审计 序列化器。"""
from rest_framework import serializers
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from ..models import Role, AuditLog, User


class ContentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentType
        fields = ('id', 'app_label', 'model')


class PermissionSerializer(serializers.ModelSerializer):
    content_type = ContentTypeSerializer(read_only=True)

    class Meta:
        model = Permission
        fields = ('id', 'name', 'codename', 'content_type')


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Permission.objects.all(), required=False
    )

    class Meta:
        model = Role
        fields = ('id', 'name', 'code', 'description', 'is_system', 'permissions')
        read_only_fields = ('is_system',)

    def create(self, validated_data):
        perms = validated_data.pop('permissions', [])
        role = Role.objects.create(**validated_data)
        role.permissions.set(perms)
        return role

    def update(self, instance, validated_data):
        perms = validated_data.pop('permissions', None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if perms is not None:
            instance.permissions.set(perms)
        return instance


class UserRoleSerializer(serializers.ModelSerializer):
    roles = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Role.objects.all(), required=False
    )
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'roles')

    def update(self, instance, validated_data):
        roles = validated_data.pop('roles', None)
        if roles is not None:
            instance.roles.set(roles)
        return instance


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True, default='')
    organization_name = serializers.CharField(source='organization.name', read_only=True, default='')

    class Meta:
        model = AuditLog
        fields = (
            'id', 'user', 'user_name', 'organization', 'organization_name',
            'action', 'resource_type', 'resource_id', 'method', 'path',
            'ip_address', 'user_agent', 'query_string', 'body_snippet',
            'response_status', 'trace_id', 'created_at',
        )
        read_only_fields = fields
