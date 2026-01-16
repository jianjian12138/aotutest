from django.db import models
import uuid

class KnowledgeDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=1024)
    file_type = models.CharField(max_length=50)  # pdf, md, txt
    size = models.IntegerField(default=0)
    status = models.CharField(max_length=50, default='pending')  # pending, processing, indexed, failed
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class DocumentChunk(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(KnowledgeDocument, on_delete=models.CASCADE, related_name='chunks')
    content = models.TextField()
    chunk_index = models.IntegerField()
    vector_id = models.CharField(max_length=255, null=True, blank=True)
    
    class Meta:
        ordering = ['chunk_index']

class KnowledgeEntity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    entity_type = models.CharField(max_length=100)  # Person, Organization, Concept
    description = models.TextField(blank=True)
    source_chunks = models.ManyToManyField(DocumentChunk, related_name='entities')

class KnowledgeRelation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey(KnowledgeEntity, on_delete=models.CASCADE, related_name='outgoing_relations')
    target = models.ForeignKey(KnowledgeEntity, on_delete=models.CASCADE, related_name='incoming_relations')
    relation_type = models.CharField(max_length=100)
    description = models.TextField(blank=True)
