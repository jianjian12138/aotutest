from rest_framework import serializers
from .models import (
    AssistantSession,
    AssistantMessage,
    DifyConfig,
    ChatMessage,
    KnowledgeDocument,
    KnowledgeEntity,
    KnowledgeRelationship,
    AIWorkflowConfig,
    AgentSkill,
    AgentProfile
)


class DifyConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = DifyConfig
        fields = ['id', 'api_url', 'api_key', 'is_active', 'created_at', 'updated_at']
        extra_kwargs = {
            'api_key': {'write_only': True}  # Don't expose API key in responses
        }


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'content', 'conversation_id', 'message_id', 'created_at']
        read_only_fields = ['conversation_id', 'message_id', 'created_at']


class AssistantMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssistantMessage
        fields = ['id', 'message_type', 'content', 'created_at']


class AssistantSessionSerializer(serializers.ModelSerializer):
    messages = AssistantMessageSerializer(many=True, read_only=True)
    chat_messages = ChatMessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = AssistantSession
        fields = ['id', 'session_id', 'conversation_id', 'title', 'created_at', 'updated_at', 'messages', 'chat_messages']


class AssistantSessionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssistantSession
        fields = ['session_id', 'title']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class AIWorkflowConfigSerializer(serializers.ModelSerializer):
    # 敏感：api_key 只写不读，读侧提供掩码（D2 P0 修复）
    api_key = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    api_key_masked = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AIWorkflowConfig
        fields = [
            'id', 'name', 'provider', 'mcp_type', 'api_url', 'api_key', 'api_key_masked',
            'workflow_id', 'additional_config', 'is_active', 'tools_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', 'tools_count']

    def get_api_key_masked(self, obj):
        key = obj.api_key or ''
        return (key[:4] + '****' + key[-4:]) if len(key) > 8 else ('****' if key else '')


class KnowledgeDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeDocument
        fields = '__all__'


class KnowledgeEntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeEntity
        fields = '__all__'


class KnowledgeRelationshipSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeRelationship
        fields = '__all__'


class AgentSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentSkill
        fields = '__all__'


class AgentProfileSerializer(serializers.ModelSerializer):
    skills_data = AgentSkillSerializer(many=True, read_only=True, source='skills')

    class Meta:
        model = AgentProfile
        # 显式白名单（D2 P0 修复：取代 fields='__all__'）
        fields = [
            'id', 'name', 'display_name', 'description', 'system_prompt',
            'llm_config', 'skills', 'skills_data', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

