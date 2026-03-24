from django.db import models
from django.utils import timezone
from apps.core_platform.models import User
from .mcp_service import MCPService
from .skills_service import SkillsService
from apps.requirement_analysis.models import AIModelConfig


class DifyConfig(models.Model):
    """Dify API配置"""
    api_url = models.URLField(max_length=500, verbose_name='API URL', help_text='Dify API endpoint URL')
    api_key = models.CharField(max_length=500, verbose_name='API Key', help_text='Dify API密钥')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'dify_configs'
        verbose_name = 'Dify配置'
        verbose_name_plural = 'Dify配置'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Dify Config - {'Active' if self.is_active else 'Inactive'}"
    
    @classmethod
    def get_active_config(cls):
        """获取当前激活的配置"""
        return cls.objects.filter(is_active=True).first()


class AIWorkflowConfig(models.Model):
    """AI工作流配置 (Coze, Dify, n8n, Skills, MCP)"""
    PROVIDER_CHOICES = [
        ('coze', 'Coze'),
        ('dify', 'Dify'),
        ('n8n', 'n8n'),
        ('skills', 'Skills'),
        ('mcp', 'MCP'),
    ]
    
    MCP_TYPE_CHOICES = [
        ('remote', '远程 (HTTP/SSE)'),
        ('local', '本地 (Command Line)'),
    ]

    name = models.CharField(max_length=100, verbose_name='配置名称')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, verbose_name='提供商')
    mcp_type = models.CharField(max_length=20, choices=MCP_TYPE_CHOICES, default='remote', verbose_name='MCP类型')
    api_url = models.CharField(max_length=500, verbose_name='API URL/Command')
    api_key = models.CharField(max_length=500, verbose_name='API Key', blank=True, null=True)
    workflow_id = models.CharField(max_length=200, verbose_name='工作流ID', blank=True, null=True)
    additional_config = models.JSONField(default=dict, verbose_name='额外配置', blank=True)
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    tools_count = models.IntegerField(default=0, verbose_name='工具数量')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'ai_workflow_configs'
        verbose_name = 'AI工作流配置'
        verbose_name_plural = 'AI工作流配置'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_provider_display()})"


class KnowledgeDocument(models.Model):
    """知识库文档"""
    title = models.CharField(max_length=255, verbose_name='文档标题')
    content = models.TextField(verbose_name='文档内容')
    file = models.FileField(upload_to='documents/', blank=True, null=True, verbose_name='文档文件')
    type = models.CharField(max_length=50, default='markdown', verbose_name='文档类型')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='创建人')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'knowledge_documents'
        verbose_name = '知识库文档'
        verbose_name_plural = '知识库文档'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class DocumentChunk(models.Model):
    """文档切片"""
    document = models.ForeignKey(KnowledgeDocument, on_delete=models.CASCADE, related_name='chunks', verbose_name='所属文档')
    content = models.TextField(verbose_name='切片内容')
    chunk_index = models.IntegerField(verbose_name='切片索引')
    vector_id = models.CharField(max_length=255, blank=True, null=True, verbose_name='向量ID')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')

    class Meta:
        db_table = 'document_chunks'
        verbose_name = '文档切片'
        verbose_name_plural = '文档切片'
        ordering = ['chunk_index']

    def __str__(self):
        return f"{self.document.title} - Chunk {self.chunk_index}"


class KnowledgeEntity(models.Model):
    """知识实体 (图谱节点)"""
    name = models.CharField(max_length=255, unique=True, verbose_name='实体名称')
    entity_type = models.CharField(max_length=100, default='concept', verbose_name='实体类型')
    description = models.TextField(blank=True, verbose_name='描述')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')

    class Meta:
        db_table = 'knowledge_entities'
        verbose_name = '知识实体'
        verbose_name_plural = '知识实体'

    def __str__(self):
        return self.name


class KnowledgeRelationship(models.Model):
    """知识关系 (图谱边)"""
    source = models.ForeignKey(KnowledgeEntity, on_delete=models.CASCADE, related_name='outgoing_relations', verbose_name='源实体')
    target = models.ForeignKey(KnowledgeEntity, on_delete=models.CASCADE, related_name='incoming_relations', verbose_name='目标实体')
    relation_type = models.CharField(max_length=100, verbose_name='关系类型')
    description = models.TextField(blank=True, verbose_name='关系描述')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')

    class Meta:
        db_table = 'knowledge_relationships'
        verbose_name = '知识关系'
        verbose_name_plural = '知识关系'
        unique_together = ['source', 'target', 'relation_type']

    def __str__(self):
        return f"{self.source.name} -> {self.relation_type} -> {self.target.name}"


class AssistantSession(models.Model):
    """智能助手会话记录"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assistant_sessions', verbose_name='用户')
    session_id = models.CharField(max_length=200, verbose_name='会话ID')
    conversation_id = models.CharField(max_length=200, blank=True, null=True, verbose_name='Dify对话ID')
    title = models.CharField(max_length=500, blank=True, verbose_name='会话标题')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'assistant_sessions'
        verbose_name = '智能助手会话'
        verbose_name_plural = '智能助手会话'
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.title or self.session_id}"


class ChatMessage(models.Model):
    """聊天消息记录"""
    ROLE_CHOICES = [
        ('user', '用户'),
        ('assistant', '助手'),
    ]
    
    session = models.ForeignKey(AssistantSession, on_delete=models.CASCADE, related_name='chat_messages', verbose_name='会话')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name='角色')
    content = models.TextField(verbose_name='消息内容')
    conversation_id = models.CharField(max_length=200, blank=True, null=True, verbose_name='Dify对话ID')
    message_id = models.CharField(max_length=200, blank=True, null=True, verbose_name='Dify消息ID')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    
    class Meta:
        db_table = 'chat_messages'
        verbose_name = '聊天消息'
        verbose_name_plural = '聊天消息'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.get_role_display()}: {self.content[:50]}"


class AssistantMessage(models.Model):
    """智能助手消息记录（保留用于向后兼容）"""
    MESSAGE_TYPE_CHOICES = [
        ('user', '用户消息'),
        ('assistant', '助手回复'),
    ]
    
    session = models.ForeignKey(AssistantSession, on_delete=models.CASCADE, related_name='messages', verbose_name='会话')
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, verbose_name='消息类型')
    content = models.TextField(verbose_name='消息内容')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    
    class Meta:
        db_table = 'assistant_messages'
        verbose_name = '智能助手消息'
        verbose_name_plural = '智能助手消息'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.get_message_type_display()}: {self.content[:50]}"


class AgentSkill(models.Model):
    """动态技能定义"""
    name = models.CharField(max_length=100, unique=True, verbose_name="技能标识(英文)")
    display_name = models.CharField(max_length=100, verbose_name="技能展示名")
    description = models.TextField(verbose_name="技能描述(供大模型理解)")
    executor_code = models.TextField(verbose_name="Python执行代码", blank=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'agent_skills'
        verbose_name = 'Agent 技能'
        verbose_name_plural = 'Agent 技能'

    def __str__(self):
        return self.display_name


class AgentProfile(models.Model):
    """动态专家画像定义"""
    name = models.CharField(max_length=100, verbose_name="Agent标识", unique=True)
    display_name = models.CharField(max_length=100, verbose_name="展示名称")
    description = models.TextField(blank=True, null=True, verbose_name="简单描述")
    system_prompt = models.TextField(verbose_name="System Prompt")
    llm_config = models.ForeignKey(AIModelConfig, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="绑定的专属大模型(可选)")
    skills = models.ManyToManyField(AgentSkill, blank=True, verbose_name="挂载的Skills")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'agent_profiles'
        verbose_name = 'Agent 专家画像'
        verbose_name_plural = 'Agent 专家画像'

    def __str__(self):
        return self.display_name

