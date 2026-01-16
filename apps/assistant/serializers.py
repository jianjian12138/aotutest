from rest_framework import serializers
from .models import AssistantSession, AssistantMessage, DifyConfig, ChatMessage, AIWorkflowConfig, KnowledgeDocument, KnowledgeEntity, KnowledgeRelationship


class DifyConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = DifyConfig
        fields = ['id', 'api_url', 'api_key', 'is_active', 'created_at', 'updated_at']
        extra_kwargs = {
            'api_key': {'write_only': True}  # Don't expose API key in responses
        }


class AIWorkflowConfigSerializer(serializers.ModelSerializer):
    provider_display = serializers.CharField(source='get_provider_display', read_only=True)
    
    class Meta:
        model = AIWorkflowConfig
        fields = ['id', 'name', 'provider', 'provider_display', 'api_url', 'api_key', 'workflow_id', 'additional_config', 'is_active', 'created_at', 'updated_at']
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


class KnowledgeDocumentSerializer(serializers.ModelSerializer):
    size = serializers.SerializerMethodField()
    
    class Meta:
        model = KnowledgeDocument
        fields = ['id', 'title', 'type', 'created_at', 'updated_at', 'file', 'size', 'content']
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def get_size(self, obj):
        if obj.file:
            try:
                return obj.file.size
            except:
                return 0
        return len(obj.content) if obj.content else 0


class KnowledgeEntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeEntity
        fields = '__all__'


class KnowledgeRelationshipSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source='source.name', read_only=True)
    target_name = serializers.CharField(source='target.name', read_only=True)
    
    class Meta:
        model = KnowledgeRelationship
        fields = '__all__'
