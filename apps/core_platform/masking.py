"""
PII 掩码工具（第六轮批次2 · D2 整改）

背景：多处序列化器直接输出 email / phone / sender_email 等个人可识别信息，
在多租户平台里意味着任意登录用户可以通过嵌套字段（owner/creator/members）
批量收集他人联系方式。

处置原则（不改字段名，避免前端大面积改造）：
  - 本人查看自己的信息        → 明文
  - is_staff / is_superuser  → 明文（管理后台需要）
  - 其他任何情况              → 掩码
  - 无 request 上下文（脚本、内部调用）→ 掩码（保守 fail-closed）

用法：
    class UserSerializer(PIIMaskMixin, serializers.ModelSerializer):
        pii_masked_fields = ('email', 'phone')
        class Meta:
            model = User
            fields = ['id', 'username', 'email', 'phone']

审计：扫描器 D2 识别 PIIMaskMixin + pii_masked_fields 声明，
将该序列化器降级为 P2 台账留痕（不是消失），由人工复核掩码覆盖是否完整。
"""


def mask_email(value):
    """foo.bar@example.com -> fo***@example.com"""
    if not value or not isinstance(value, str):
        return value
    if '@' not in value:
        return mask_generic(value)
    local, _, domain = value.partition('@')
    keep = local[:2] if len(local) > 2 else local[:1]
    return f'{keep}***@{domain}'


def mask_phone(value):
    """13812348000 -> 138****8000"""
    if not value or not isinstance(value, str):
        return value
    digits = value.strip()
    if len(digits) <= 4:
        return '*' * len(digits)
    if len(digits) <= 7:
        return digits[:2] + '*' * (len(digits) - 2)
    return digits[:3] + '*' * (len(digits) - 7) + digits[-4:]


def mask_generic(value):
    """通用掩码：保留前 2 后 2"""
    if not value or not isinstance(value, str):
        return value
    if len(value) <= 4:
        return '*' * len(value)
    return value[:2] + '*' * (len(value) - 4) + value[-2:]


_MASKERS = {
    'email': mask_email,
    'sender_email': mask_email,
    'recipient_email': mask_email,
    'phone': mask_phone,
    'mobile': mask_phone,
    'telephone': mask_phone,
}


def mask_field(field_name, value):
    return _MASKERS.get(field_name.lower(), mask_generic)(value)


def can_view_pii(request, instance=None):
    """判断当前请求方是否有权看到 instance 的 PII 明文。"""
    user = getattr(request, 'user', None) if request is not None else None
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False):
        return True
    # 本人查看自己
    if instance is not None:
        inst_pk = getattr(instance, 'pk', None)
        if inst_pk is not None and inst_pk == getattr(user, 'pk', object()):
            # 仅当 instance 与 user 属同一模型时才认定为"本人"
            if type(instance) is type(user) or isinstance(instance, type(user)):
                return True
    return False


class PIIMaskMixin:
    """序列化器 PII 掩码 mixin，须与 pii_masked_fields 搭配使用。"""

    pii_masked_fields = ()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not self.pii_masked_fields:
            return data
        request = self.context.get('request') if hasattr(self, 'context') else None
        if can_view_pii(request, instance):
            return data
        for name in self.pii_masked_fields:
            if name in data and data[name]:
                data[name] = mask_field(name, data[name])
        return data
