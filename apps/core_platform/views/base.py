from rest_framework import viewsets

from ..permissions import TenantAwareViewSetMixin


class BaseProjectViewSet(viewsets.ModelViewSet):
    """
    全局基础 ViewSet：负责统一处理项目级别的数据隔离和自动填充审计字段

    # 第六轮批次2：接入统一租户隔离（方法委托方式）。
    # 不能直接把 TenantAwareViewSetMixin 挂为第一基类：现存 7 个子类
    # （ApiRequestViewSet / AICaseViewSet / AIExecutionRecordViewSet / ElementGroupViewSet /
    #   ui.TestSuiteViewSet / ScriptElementUsageViewSet / ui.TestCaseViewSet）
    # 已按 `class X(TenantAwareViewSetMixin, BaseProjectViewSet)` 声明，
    # 若本类再继承同一 mixin，C3 线性化将产生 MRO 冲突（TypeError），全部子类 import 失败。
    # 因此以类属性委托复用 mixin 全部零件（_apply_tenant_scope / scoped_get / scoped_filter），
    # 所有子类自动获得统一隔离能力；本类 get_queryset 自身已实现等价且更严的隔离：
    # 携带 project_id 时校验 owner/members 归属，未携带时按 created_by 过滤，皆 fail-closed。
    # 不在其上再套 _apply_tenant_scope（organization 过滤）：注册用户 organization 可为空，
    # 叠加 org 过滤会把此类用户可见性清零，属功能倒退；现有归属过滤已不宽于 mixin 语义（无放宽）。
    """

    org_field = None
    owner_field = 'created_by'
    staff_has_full_access = True
    tenant_scope_exempt = False
    tenant_scope_exempt_reason = ''
    # 与 TenantAwareViewSetMixin 对齐的默认值：子类可覆写为 True 声明自管租户过滤。
    # 必须在此给出默认值，否则委托来的 _apply_tenant_scope 读取该属性会 AttributeError。
    tenant_scope_self_managed = False
    tenant_scope_self_managed_reason = ''
    _resolve_tenant_filter = TenantAwareViewSetMixin._resolve_tenant_filter
    _apply_tenant_scope = TenantAwareViewSetMixin._apply_tenant_scope
    scoped_queryset = TenantAwareViewSetMixin.scoped_queryset
    scoped_filter = TenantAwareViewSetMixin.scoped_filter
    scoped_get = TenantAwareViewSetMixin.scoped_get

    def get_queryset(self):
        """
        统一实现数据级别的项目隔离。
        仅当请求中显式携带 project_id 时才返回该项目的全量数据；
        未携带 project_id 时默认 fail-closed：仅返回当前登录用户作为创建者可见的数据，
        杜绝跨租户/跨项目的全量越权泄露。
        要求继承此类的 Model 必须具有 project_id 字段（ForeignKey）及 created_by 字段；
        若两者皆无则直接返回空集（默认拒绝）。
        """
        queryset = super().get_queryset()

        # 处理 schema generation 等无 request 环境
        if getattr(self, 'swagger_fake_view', False) or not hasattr(self, 'request') or self.request is None:
            return queryset

        # 兼容 query_params 和 data (处理 GET/POST)
        project_id = getattr(self.request, 'query_params', {}).get('project_id')
        if not project_id and hasattr(self.request, 'data') and isinstance(self.request.data, dict):
            project_id = self.request.data.get('project_id')

        if project_id:
            # 校验当前用户对该 project 的归属（owner / members），杜绝跨租户越权读取
            # 修复第三轮 P1-新1：原逻辑直接 filter(project_id=project_id)，攻击者可传他人 project_id 读全量
            from apps.core_platform.models import Project
            proj = Project.objects.filter(id=project_id).first()
            if proj is None:
                return queryset.none()
            user = getattr(self.request, 'user', None)
            if user is not None and (user.is_staff or user.is_superuser):
                return queryset.filter(project_id=project_id)
            is_owner = getattr(proj, 'owner_id', None) is not None and proj.owner_id == (user.id if user else None)
            is_member = user is not None and proj.members.filter(id=user.id).exists()
            if user is not None and (is_owner or is_member):
                return queryset.filter(project_id=project_id)
            return queryset.none()

        # 无 project_id：默认仅返回当前用户作为创建者可见的数据，杜绝跨租户全量泄露
        user = getattr(self.request, 'user', None)
        if user is not None and hasattr(queryset.model, 'created_by'):
            return queryset.filter(created_by=user)
        return queryset.none()

    def perform_create(self, serializer):
        """
        统一实现创建记录时自动绑定 created_by 为当前登录用户
        要求继承此类的 Model 必须具有 created_by 字段
        """
        if hasattr(serializer.Meta.model, 'created_by'):
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()

    def perform_update(self, serializer):
        """
        统一实现更新记录时自动绑定 updated_by 为当前登录用户
        要求继承此类的 Model 必须具有 updated_by 字段
        """
        if hasattr(serializer.Meta.model, 'updated_by'):
            serializer.save(updated_by=self.request.user)
        else:
            serializer.save()
