from django.db import models
import uuid
from apps.core_platform.models import Project

class KnowledgeDocument(models.Model):
    SOURCE_TYPES = (
        ('file', 'Local File'),
        ('aliyun', 'Aliyun Xiao'),
        ('youdao', 'Youdao Note'),
        ('wechat', 'Wechat Article'),
        ('requirement', 'Business Requirement'),
        ('api_spec', 'API Specification'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name='knowledge_documents')
    name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=1024, blank=True, null=True)
    file_type = models.CharField(max_length=50)  # pdf, md, txt, url
    size = models.IntegerField(default=0)
    status = models.CharField(max_length=50, default='pending')  # pending, processing, indexed, failed
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES, default='file')
    external_url = models.CharField(max_length=1024, blank=True, null=True)
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
    relation_type = models.CharField(max_length=100) # related_to, upstream, downstream, calls, dependency
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True) # Store mapping info like resp.id -> req.order_id

class AliyunInterfaceLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project_id = models.CharField(max_length=255)
    url = models.CharField(max_length=1024)
    method = models.CharField(max_length=20)
    request_headers = models.JSONField(default=dict)
    request_body = models.JSONField(default=dict)
    response_headers = models.JSONField(default=dict)
    response_body = models.JSONField(default=dict)
    status_code = models.IntegerField()
    trace_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
