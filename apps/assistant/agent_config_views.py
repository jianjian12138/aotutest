from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import AgentSkill, AgentProfile
from .serializers import AgentSkillSerializer, AgentProfileSerializer

class AgentSkillViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Dynamic Agent Skills
    """
    queryset = AgentSkill.objects.all().order_by('-created_at')
    serializer_class = AgentSkillSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

class AgentProfileViewSet(viewsets.ModelViewSet):
    """
    CRUD API for Dynamic Agent Profiles
    """
    queryset = AgentProfile.objects.all().order_by('-created_at')
    serializer_class = AgentProfileSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
