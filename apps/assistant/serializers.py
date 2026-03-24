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
    class Meta:
        model = AIWorkflowConfig
        fields = '__all__'


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
        fields = '__all__'

