from rest_framework import serializers
from .models import KnowledgeDocument, DocumentChunk, KnowledgeEntity, KnowledgeRelation

class KnowledgeDocumentSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=False)
    
    class Meta:
        model = KnowledgeDocument
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'status', 'size', 'file_type', 'file_path']

class DocumentChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentChunk
        fields = '__all__'

class KnowledgeEntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeEntity
        fields = '__all__'

class KnowledgeRelationSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source='source.name', read_only=True)
    target_name = serializers.CharField(source='target.name', read_only=True)
    
    class Meta:
        model = KnowledgeRelation
        fields = '__all__'
