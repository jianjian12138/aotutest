from rest_framework import serializers
from .models import Project, ProjectMember, ProjectEnvironment
from apps.users.serializers import UserSerializer

class ProjectSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ('id', 'name')

class ProjectEnvironmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectEnvironment
        fields = '__all__'

class ProjectMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = ProjectMember
        fields = ['id', 'user', 'user_id', 'role', 'joined_at']

class ProjectSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    members = ProjectMemberSerializer(source='projectmember_set', many=True, read_only=True)
    environments = ProjectEnvironmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'status', 'owner', 'members', 
                 'environments', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class ProjectCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['name', 'description', 'status']
    
    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)