"""阶段1.4 缺陷跟踪 视图。

- 租户隔离（TenantScopedViewSetMixin）；
- 对象级权限：报告人 / 指派人 / 项目成员 / 管理员可写；
- 提供状态流转 action（走 Defect 状态机，非法流转被拒）。
"""
from rest_framework import viewsets, mixins, serializers as drf_serializers
from rest_framework import permissions as drf_permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core_platform.permissions import TenantAwareViewSetMixin
from django.db import transaction
from django.db.models import Q
from .models import Defect
from .serializers import (
    DefectSerializer, DefectCreateSerializer, DefectTransitionSerializer,
)


class DefectPermission(drf_permissions.BasePermission):
    """缺陷对象级权限：只读公开（受租户隔离约束）；写需相关人/管理员。"""
    message = '仅缺陷相关人（报告人/指派人/项目成员）或管理员可修改。'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in drf_permissions.SAFE_METHODS:
            return True
        user = request.user
        if user.is_staff or user.is_superuser:
            return True
        if obj.reporter_id and obj.reporter_id == user.id:
            return True
        if obj.assignee_id and obj.assignee_id == user.id:
            return True
        if obj.project_id:
            return obj.project.members.filter(pk=user.id).exists()
        return False


class DefectViewSet(TenantAwareViewSetMixin,
                   mixins.ListModelMixin,
                   mixins.RetrieveModelMixin,
                   mixins.CreateModelMixin,
                   mixins.UpdateModelMixin,
                   viewsets.GenericViewSet):
    # 第六轮批次2：原基类为 TenantScopedViewSetMixin，自定义 get_queryset 经 super()
    # 调用其隔离实现（组织级过滤实际生效），但收口点是隐式的、改一行 super() 就会静默失效。
    # 现改为统一基类 + 显式收口，并补上"无组织用户"这一原实现的空档（见 reason）。
    tenant_scope_self_managed = True
    tenant_scope_self_managed_reason = (
        'get_queryset 显式实现组织级边界：管理员全量；有组织用户限 organization=本组织（与原 TenantScopedViewSetMixin 等价）；'
        '无组织用户（organization 为空）原实现会退化为 organization IS NULL，使所有无组织用户互相看到对方缺陷，'
        '此处收敛为仅 reporter/assignee/所属项目 owner|members 自己相关的缺陷，只收紧不放宽，'
        '同时避免自动解析在 org 为空时整体 fail-closed 清零、让用户看不到自己上报的缺陷'
    )
    queryset = Defect.objects.select_related(
        'reporter', 'assignee', 'project', 'organization'
    ).prefetch_related('history').all()
    permission_classes = [drf_permissions.IsAuthenticated, DefectPermission]
    filterset_fields = ['status', 'severity', 'priority', 'assignee', 'project', 'related_execution']
    search_fields = ['title', 'description', 'steps']
    ordering_fields = ['created_at', 'severity', 'priority', 'status']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return DefectCreateSerializer
        if self.action == 'transition':
            return DefectTransitionSerializer
        return DefectSerializer

    def get_queryset(self):
        qs = self.queryset.all()
        user = self.request.user
        if not user.is_authenticated:
            return qs.none()
        if not (user.is_staff or user.is_superuser):
            org_id = getattr(user, 'organization_id', None)
            if org_id is not None:
                qs = qs.filter(organization_id=org_id)
            else:
                # 无组织用户：不按 organization IS NULL 匹配（会串号），只看与自己相关的缺陷
                qs = qs.filter(
                    Q(reporter=user) | Q(assignee=user)
                    | Q(project__owner=user) | Q(project__members=user)
                ).distinct()
        params = self.request.query_params
        if params.get('severity'):
            qs = qs.filter(severity=params['severity'])
        if params.get('priority'):
            qs = qs.filter(priority=params['priority'])
        if params.get('assignee'):
            qs = qs.filter(assignee_id=params['assignee'])
        if params.get('project'):
            qs = qs.filter(project_id=params['project'])
        if params.get('related_execution'):
            qs = qs.filter(related_execution_id=params['related_execution'])
        return self._apply_tenant_scope(qs)

    @action(detail=True, methods=['post'])
    def transition(self, request, pk=None):
        """缺陷状态流转：body={to_status, comment}。"""
        defect = self.get_object()
        serializer = DefectTransitionSerializer(
            data=request.data, context={'defect': defect}
        )
        serializer.is_valid(raise_exception=True)
        to_status = serializer.validated_data['to_status']
        comment = serializer.validated_data.get('comment', '')
        try:
            # 状态流转 + 历史写 作为整体事务，避免部分成功导致状态与历史不一致
            with transaction.atomic():
                defect.apply_transition(to_status, user=request.user, comment=comment)
        except ValueError as e:
            raise drf_serializers.ValidationError({'to_status': str(e)})
        return Response(DefectSerializer(defect, context={'request': request}).data)
