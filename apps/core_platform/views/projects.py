from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db import models
from ..models import Project, ProjectMember, ProjectEnvironment
from ..permissions import TenantAwareViewSetMixin
from ..serializers.projects import ProjectSerializer, ProjectCreateSerializer, ProjectMemberSerializer, ProjectEnvironmentSerializer

# Imports for statistics
from apps.testcases.models import TestCase
from apps.testsuites.models import TestSuite
from apps.scheduler.models import ScheduledTask
from apps.reports.models import TestReport

class ProjectListCreateView(TenantAwareViewSetMixin, generics.ListCreateAPIView):
    # 第六轮批次2：自定义 get_queryset 已实现等效且更严的租户边界，显式声明自管，
    # 并在 return 分支统一收口 self._apply_tenant_scope(qs) 作为收口点。
    tenant_scope_self_managed = True
    tenant_scope_self_managed_reason = (
        '自定义 get_queryset 以 Q(owner=user)|Q(members=user) 按项目归属过滤：用户只能看到自己拥有或被邀请加入的项目，'
        '未命中即空集（fail-closed），边界不弱于组织级隔离；Project.organization 可为空且注册用户默认无组织，'
        '叠加自动 org 过滤会把无组织用户的自有项目清零，并把跨组织协作成员误伤为不可见'
    )
    queryset = Project.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'owner']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'name']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProjectCreateSerializer
        return ProjectSerializer
    
    def get_queryset(self):
        # 默认只显示用户参与的项目或自己创建的项目
        user = self.request.user
        qs = self.queryset.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        return self._apply_tenant_scope(qs)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_all_projects(request):
    """获取项目列表（下拉选择用）。第四轮整改：非管理员仅返回自己参与/拥有的项目。"""
    user = request.user
    qs = Project.objects.all()
    if not (user.is_staff or user.is_superuser):
        qs = qs.filter(models.Q(owner=user) | models.Q(members=user)).distinct()
    projects = qs.values('id', 'name', 'description', 'status')
    return Response(list(projects))


class IsProjectOwnerOrAdminOrReadOnly(permissions.BasePermission):
    """读：项目参与者（由 queryset 作用域保证）；写：仅项目 owner 或管理员。"""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        if user.is_staff or user.is_superuser:
            return True
        return getattr(obj, 'owner_id', None) == user.id


class ProjectDetailView(TenantAwareViewSetMixin, generics.RetrieveUpdateDestroyAPIView):
    """项目详情。第四轮整改：非管理员仅能访问自己参与/拥有的项目；写操作仅 owner/管理员。

    # 第六轮批次2：显式声明自管租户过滤，并在每个 return 分支收口 _apply_tenant_scope。
    """
    tenant_scope_self_managed = True
    tenant_scope_self_managed_reason = (
        '自定义 get_queryset 以 Q(owner=user)|Q(members=user) 按项目归属过滤，非归属项目直接不可达（fail-closed），'
        '边界不弱于组织级隔离；Project.organization 可为空，叠加自动 org 过滤会清零无组织用户对自有项目的访问，'
        '并阻断跨组织协作成员，属功能倒退。管理员全量可见沿用原有语义'
    )
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated, IsProjectOwnerOrAdminOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        qs = self.queryset.all()
        if user.is_staff or user.is_superuser:
            return self._apply_tenant_scope(qs)
        qs = qs.filter(models.Q(owner=user) | models.Q(members=user)).distinct()
        return self._apply_tenant_scope(qs)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_project_member(request, project_id):
    try:
        project = Project.objects.get(id=project_id)
        if project.owner != request.user:
            return Response({'error': '无权限添加成员'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ProjectMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(project=project)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    except Project.DoesNotExist:
        return Response({'error': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_project_members(request, project_id):
    """获取项目成员列表"""
    try:
        project = Project.objects.get(id=project_id)
        
        # 检查用户是否有权限查看项目成员
        if not (project.owner == request.user or 
                ProjectMember.objects.filter(project=project, user=request.user).exists()):
            return Response({'error': '无权限查看项目成员'}, status=status.HTTP_403_FORBIDDEN)
        
        # 获取项目成员，包括项目所有者
        members = []
        
        # 添加项目所有者
        members.append({
            'id': project.owner.id,
            'username': project.owner.username,
            'email': project.owner.email,
            'first_name': project.owner.first_name,
            'last_name': project.owner.last_name,
            'role': 'owner'
        })
        
        # 添加项目成员
        project_members = ProjectMember.objects.filter(project=project).select_related('user')
        for member in project_members:
            members.append({
                'id': member.user.id,
                'username': member.user.username,
                'email': member.user.email,
                'first_name': member.user.first_name,
                'last_name': member.user.last_name,
                'role': member.role
            })
        
        return Response(members)
    except Project.DoesNotExist:
        return Response({'error': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def remove_project_member(request, project_id, member_id):
    try:
        project = Project.objects.get(id=project_id)
        if project.owner != request.user:
            return Response({'error': '无权限删除成员'}, status=status.HTTP_403_FORBIDDEN)
        
        member = ProjectMember.objects.get(id=member_id, project=project)
        member.delete()
        return Response({'message': '成员删除成功'})
    except (Project.DoesNotExist, ProjectMember.DoesNotExist):
        return Response({'error': '项目或成员不存在'}, status=status.HTTP_404_NOT_FOUND)

class ProjectEnvironmentListCreateView(TenantAwareViewSetMixin, generics.ListCreateAPIView):
    # 第六轮批次2：显式声明自管租户过滤，两个 return 分支均收口 _apply_tenant_scope。
    tenant_scope_self_managed = True
    tenant_scope_self_managed_reason = (
        'get_queryset 先经 _user_can_access_project() 校验 URL 上的 project_id 是否属于当前用户（owner|members，管理员放行），'
        '校验不通过直接返回 none()，用户拿别人的 project_id 也读不到环境配置；该归属校验不弱于 project__organization 过滤，'
        '且 Project.organization 可为空，叠加自动过滤会误伤无组织用户与跨组织协作成员'
    )
    queryset = ProjectEnvironment.objects.all()
    serializer_class = ProjectEnvironmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def _user_can_access_project(self, project_id):
        """第四轮整改：校验当前用户是否为该项目 owner/成员/管理员，否则拒绝。"""
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return Project.objects.filter(id=project_id).exists()
        return Project.objects.filter(id=project_id).filter(
            models.Q(owner=user) | models.Q(members=user)
        ).exists()

    def get_queryset(self):
        project_id = self.kwargs['project_id']
        if not self._user_can_access_project(project_id):
            return self._apply_tenant_scope(self.queryset.none())
        qs = self.queryset.filter(project_id=project_id)
        return self._apply_tenant_scope(qs)

    def perform_create(self, serializer):
        project_id = self.kwargs['project_id']
        if not self._user_can_access_project(project_id):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('无权限操作该项目的环境配置')
        serializer.save(project_id=project_id)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_project_statistics(request, project_id):
    """获取项目各维度数据统计"""
    try:
        project = Project.objects.get(id=project_id)
        
        # 权限检查
        if not (project.owner == request.user or 
                ProjectMember.objects.filter(project=project, user=request.user).exists()):
            return Response({'error': '无权限查看项目统计'}, status=status.HTTP_403_FORBIDDEN)
            
        data = {
            'members_count': ProjectMember.objects.filter(project=project).count() + 1,
            'environments_count': ProjectEnvironment.objects.filter(project=project).count(),
            'testcases_count': TestCase.objects.filter(project=project).count(),
            'testsuites_count': TestSuite.objects.filter(project=project).count(),
            'tasks_count': ScheduledTask.objects.filter(project=project).count(),
            'reports_count': TestReport.objects.filter(project=project).count(),
        }
        return Response(data)
    except Project.DoesNotExist:
        return Response({'error': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)