from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.core_platform.permissions import IsAdminOrReadOnly
from .models import AgentSkill, AgentProfile
from .serializers import AgentSkillSerializer, AgentProfileSerializer

class AgentSkillViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Dynamic Agent Skills

    安全说明：AgentSkill.executor_code 会被 Agent 在沙箱中执行，
    属于代码注入面，因此写操作仅限管理员（IsAdminOrReadOnly）。
    """
    queryset = AgentSkill.objects.all().order_by('-created_at')
    serializer_class = AgentSkillSerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = None
    # 第六轮批次2：接入统一租户隔离——AgentSkill 无任何租户字段（无 organization/project/created_by），
    # 属平台级公共技能字典，按租户过滤会 fail-closed 清空全部技能、破坏 Agent 功能，故显式豁免留痕。
    tenant_scope_exempt = True
    tenant_scope_exempt_reason = '平台级 Agent 技能字典表，模型无租户字段，全租户共享只读；写操作已由 IsAdminOrReadOnly 限制为管理员'

class AgentProfileViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Dynamic Agent Profiles
    """
    queryset = AgentProfile.objects.all().order_by('-created_at')
    serializer_class = AgentProfileSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    # 第六轮批次2：接入统一租户隔离——AgentProfile 无任何租户字段（name 全局唯一），
    # 属平台级共享专家画像，按租户过滤会 fail-closed 导致所有非管理员用户不可用，故显式豁免留痕。
    tenant_scope_exempt = True
    tenant_scope_exempt_reason = '平台级 Agent 专家画像（name 全局唯一、无租户字段），全租户共享使用；不含密钥类敏感数据'
