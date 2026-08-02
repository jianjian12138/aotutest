"""
平台通用 DRF 权限类（阶段0安全加固引入，阶段1 RBAC 将在此基础上扩展）。
"""
from rest_framework import permissions
import logging
logger = logging.getLogger(__name__)


class IsOwnerOrAdminOrReadOnly(permissions.BasePermission):
    """
    读操作：任何已认证用户；
    写操作：仅资源创建者（created_by）或管理员（is_staff/is_superuser）。
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        if user.is_staff or user.is_superuser:
            return True
        owner = getattr(obj, 'created_by', None)
        return owner is not None and owner == user


class IsAdminOrOwner(permissions.BasePermission):
    """读写均限创建者本人或管理员。"""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_staff or user.is_superuser:
            return True
        owner = getattr(obj, 'created_by', None)
        return owner is not None and owner == user


class IsAdminOrReadOnly(permissions.BasePermission):
    """读操作：任何已认证用户；写操作：仅管理员（is_staff/is_superuser）。"""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(user.is_staff or user.is_superuser)


class IsAdminUserStrict(permissions.BasePermission):
    """仅平台管理员（is_staff）可访问——用于代码执行/危险调试类端点。"""

    message = '该操作涉及代码执行，仅平台管理员可用。'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class OwnedQuerySetMixin:
    """
    ViewSet mixin：非管理员默认只能看到自己创建的数据。
    要求模型具有 created_by 字段；管理员可见全部。
    """

    owner_field = 'created_by'

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return qs.none()
        if user.is_staff or user.is_superuser:
            return qs
        return qs.filter(**{self.owner_field: user})


# ============================================================
# 阶段1 RBAC / 租户隔离 扩展
# ============================================================
def user_has_perm(user, codename):
    """
    聚合判断用户是否拥有某权限（codename）。
    优先级：超级管理员 > 用户直接权限(user_permissions) > 角色权限(roles.permissions)。
    """
    if not (user and user.is_authenticated):
        return False
    if user.is_superuser:
        return True
    if user.user_permissions.filter(codename=codename).exists():
        return True
    from .models import Role
    return Role.objects.filter(
        users=user, permissions__codename=codename
    ).exists()


class HasRolePermission(permissions.BasePermission):
    """
    要求用户具备指定权限（codename）。
    用法：class MyView(...): permission_classes = [IsAuthenticated, HasRolePermission]
          required_perm = 'core_platform.add_project'
    """
    message = '权限不足，需要相应角色授权。'
    required_perm = None

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_superuser:
            return True
        if not self.required_perm:
            return True
        return user_has_perm(request.user, self.required_perm)


def is_tenant_admin(user):
    """
    判定用户是否为“租户管理员”。
    采用自包含判定（不依赖未被播种的 auth.Permission 行）：
      - 超级管理员 / 平台管理员（is_staff/is_superuser）；
      - 或拥有 code='tenant_admin' 的角色。
    避免在缺少 tenant_admin 权限种子时，租户管理员永远无法写角色/审计的死链。
    """
    if not (user and user.is_authenticated):
        return False
    if user.is_staff or user.is_superuser:
        return True
    if getattr(user, 'roles', None) is None:
        return False
    return user.roles.filter(code='tenant_admin').exists()


class IsTenantAdminOrReadOnly(permissions.BasePermission):
    """
    读：任何已认证用户；
    写：仅平台管理员（is_staff/is_superuser）或具备 tenant_admin 角色的用户。
    用于租户级资源（组织、角色、审计等）的写保护。
    """
    message = '仅租户管理员可执行该操作。'

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return is_tenant_admin(user)


class TenantScopedViewSetMixin:
    """
    租户隔离 mixin：自动按 request.user.organization 过滤查询集。
    模型需具备：
      - 直接 organization 字段（TenantScopedModel），或
      - project 外键且 project 具 organization（大多数业务模型）。
    管理员（is_staff/is_superuser）默认可见全量（如需强制隔离可覆写）。
    """
    org_field = None  # 显式指定租户字段，如 'organization' 或 'project__organization'

    def _resolve_org_filter(self):
        if self.org_field:
            return self.org_field
        model = self.queryset.model if self.queryset is not None else None
        if model is None:
            return None
        if 'organization' in [f.name for f in model._meta.get_fields()]:
            return 'organization'
        if 'project' in [f.name for f in model._meta.get_fields()]:
            return 'project__organization'
        return None

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return qs.none()
        if user.is_staff or user.is_superuser:
            return qs
        org_filter = self._resolve_org_filter()
        if org_filter:
            return qs.filter(**{org_filter: user.organization_id})
        # 未显式声明 org_field 且模型无 organization/project 字段时，
        # 默认 fail-closed：非管理员看不到任何数据，避免越权泄露。
        logger.warning(
            "TenantScopedViewSetMixin：视图 %s 未解析到租户字段，"
            "已对非管理员返回空集合（fail-closed）。若确需跨租户可见，请显式声明 org_field。",
            self.__class__.__name__,
        )
        return qs.none()


class TenantAwareViewSetMixin:
    """
    第四轮整改统一租户隔离基类（取代散点过滤，根除跨租户越权）。

    租户字段解析优先级（自动）：
      1. 显式 org_field（支持多跳，如 'document__project__organization' / 'project__created_by'）
      2. 模型直接 organization 字段
      3. 模型 project 外键 → project__organization
      4. created_by / creator 字段 → 按当前用户过滤
    未解析到任何租户字段时 fail-closed：非管理员返回空集合。

    管理员(is_staff/is_superuser)默认可见全量（设 staff_has_full_access=False 可关闭）。
    两种用法：
      (a) 无自定义 get_queryset 的视图：class X(TenantAwareViewSetMixin, viewsets.ModelViewSet)
      (b) 有自定义 get_queryset 的视图：在其末尾 return self._apply_tenant_scope(queryset)

    第六轮批次2新增——显式豁免（tenant_scope_exempt）：
      少数资源本质上是平台级公共数据（如 Django 内置 Permission 字典表、
      注册端点等），按租户过滤会直接破坏功能。这类视图不得"默默不接隔离"，
      必须显式声明：
          tenant_scope_exempt = True
          tenant_scope_exempt_reason = '平台级权限字典表，全租户共享只读，写权限由 permission_classes 限制'
      声明后 _apply_tenant_scope 放行全量，同时审计扫描器会把该视图记入
      P2 台账（"已声明租户豁免，待人工复核理由"），保证豁免可审计、不隐身。
    """
    org_field = None
    owner_field = 'created_by'   # 兼容 'creator'
    staff_has_full_access = True
    # 显式租户豁免：仅用于平台级公共资源，必须同时填写 reason
    tenant_scope_exempt = False
    tenant_scope_exempt_reason = ''
    # 自管租户过滤：自定义 get_queryset 已实现等效或更严格的租户边界
    # （典型如 owner|members 项目归属过滤），自动解析不再叠加，避免二次收紧
    # 把合法协作者误伤。必须同时填写 reason，扫描器记 P2 台账留痕。
    tenant_scope_self_managed = False
    tenant_scope_self_managed_reason = ''

    def _resolve_tenant_filter(self):
        if self.org_field:
            return self.org_field
        model = self.queryset.model if getattr(self, 'queryset', None) is not None else None
        if model is None:
            return None
        fields = model._meta.get_fields()
        field_names = [f.name for f in fields]
        if 'organization' in field_names:
            return 'organization'
        if any(f.name == 'project' and getattr(f, 'is_relation', False) for f in fields):
            return 'project__organization'
        if self.owner_field in field_names:
            return self.owner_field
        if 'creator' in field_names:
            return 'creator'
        return None

    def _apply_tenant_scope(self, qs):
        user = self.request.user
        if not user.is_authenticated:
            return qs.none()
        if self.tenant_scope_exempt:
            # 平台级公共资源，显式豁免租户过滤（理由见 tenant_scope_exempt_reason）
            if not self.tenant_scope_exempt_reason:
                logger.error(
                    "视图 %s 声明了 tenant_scope_exempt 但未填写 tenant_scope_exempt_reason，"
                    "豁免必须写明理由以便审计。",
                    self.__class__.__name__,
                )
            return qs
        if self.tenant_scope_self_managed:
            # 传入的 qs 已由自定义 get_queryset 完成租户过滤，不再叠加自动解析，
            # 否则会把 owner|members 这类协作可见性二次收紧为 owner-only。
            if not self.tenant_scope_self_managed_reason:
                logger.error(
                    "视图 %s 声明了 tenant_scope_self_managed 但未填写理由，"
                    "自管过滤必须写明其租户边界如何保证，以便审计。",
                    self.__class__.__name__,
                )
            return qs
        if self.staff_has_full_access and (user.is_staff or user.is_superuser):
            return qs
        filt = self._resolve_tenant_filter()
        if not filt:
            logger.warning(
                "TenantAwareViewSetMixin：视图 %s 未解析到租户字段，"
                "已对非管理员返回空集合（fail-closed）。",
                self.__class__.__name__,
            )
            return qs.none()
        # 末段为用户外键（created_by/creator/owner，支持多跳如 job__created_by）时按当前用户过滤
        if filt.split('__')[-1] in ('created_by', 'creator', 'owner', 'user'):
            return qs.filter(**{filt: user})
        org_id = getattr(user, 'organization_id', None)
        if org_id is None:
            return qs.none()
        return qs.filter(**{filt: org_id})

    def get_queryset(self):
        qs = super().get_queryset()
        return self._apply_tenant_scope(qs)

    # ------ 第六轮批次1零件：@action 内替代直连 Model.objects 的统一入口 ------
    def scoped_queryset(self, model, org_field=None):
        """按当前请求用户返回 model 的租户内全集（fail-closed）。

        用于 @action / 自定义方法中替代 `Model.objects.xxx` 直连：
            Config.objects.get(id=x)      → self.scoped_get(Config, id=x)
            Item.objects.filter(a=b)      → self.scoped_filter(Item, a=b)
        """
        return scoped_queryset_for(self.request.user, model, org_field=org_field,
                                   staff_full=self.staff_has_full_access)

    def scoped_filter(self, model, org_field=None, **kwargs):
        return self.scoped_queryset(model, org_field=org_field).filter(**kwargs)

    def scoped_get(self, model, org_field=None, **kwargs):
        """租户内 get：目标不在当前用户可见范围时抛 model.DoesNotExist（与原语义兼容）。"""
        return self.scoped_queryset(model, org_field=org_field).get(**kwargs)


def _tenant_filter_for_model(model, org_field=None):
    """为任意模型解析租户过滤路径（与 TenantAwareViewSetMixin 同优先级）。"""
    if org_field:
        return org_field
    fields = model._meta.get_fields()
    field_names = [f.name for f in fields]
    if 'organization' in field_names:
        return 'organization'
    if any(f.name == 'project' and getattr(f, 'is_relation', False) for f in fields):
        return 'project__organization'
    if 'created_by' in field_names:
        return 'created_by'
    if 'creator' in field_names:
        return 'creator'
    return None


def scoped_queryset_for(user, model, org_field=None, staff_full=True):
    """模块级零件：按 user 返回 model 的租户内 queryset（fail-closed）。

    供函数视图 / APIView / 非 mixin 类使用：
        from apps.core_platform.permissions import scoped_queryset_for
        qs = scoped_queryset_for(request.user, VannaConfig).filter(id=config_id)
    """
    qs = model.objects.all()
    if user is None or not getattr(user, 'is_authenticated', False):
        return qs.none()
    if staff_full and (user.is_staff or user.is_superuser):
        return qs
    filt = _tenant_filter_for_model(model, org_field)
    if not filt:
        logger.warning(
            "scoped_queryset_for：模型 %s 未解析到租户字段，已 fail-closed 返回空集合。",
            model.__name__,
        )
        return qs.none()
    if filt.split('__')[-1] in ('created_by', 'creator', 'owner', 'user'):
        return qs.filter(**{filt: user})
    org_id = getattr(user, 'organization_id', None)
    if org_id is None:
        return qs.none()
    return qs.filter(**{filt: org_id})
