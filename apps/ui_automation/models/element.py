from apps.notifications.models import NotificationConfig
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()
from django.utils import timezone
import json
from .project import UiProject

class LocatorStrategy(models.Model):
    """元素定位策略模型"""
    name = models.CharField(max_length=50, verbose_name='策略名称')
    description = models.TextField(blank=True, verbose_name='策略描述')

    class Meta:
        db_table = 'locator_strategies'
        verbose_name = '定位策略'
        verbose_name_plural = '定位策略'

    def __str__(self):
        return self.name


class ElementGroup(models.Model):
    """元素分组模型"""
    name = models.CharField(max_length=200, verbose_name='分组名称')
    description = models.TextField(blank=True, verbose_name='分组描述')
    project = models.ForeignKey(UiProject, on_delete=models.CASCADE, related_name='element_groups', verbose_name='所属项目')
    parent_group = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, verbose_name='父分组')
    order = models.IntegerField(default=0, verbose_name='排序')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'ui_element_groups'
        verbose_name = '元素分组'
        verbose_name_plural = '元素分组'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Element(models.Model):
    """UI元素模型"""
    ELEMENT_TYPE_CHOICES = [
        ('INPUT', '输入框'),
        ('BUTTON', '按钮'),
        ('LINK', '链接'),
        ('DROPDOWN', '下拉框'),
        ('CHECKBOX', '复选框'),
        ('RADIO', '单选框'),
        ('TEXT', '文本'),
        ('IMAGE', '图片'),
        ('CONTAINER', '容器'),
        ('TABLE', '表格'),
        ('FORM', '表单'),
        ('MODAL', '弹窗'),
    ]

    VALIDATION_STATUS_CHOICES = [
        ('VALID', '有效'),
        ('INVALID', '无效'),
        ('UNKNOWN', '未知'),
        ('PENDING', '待验证'),
    ]

    project = models.ForeignKey(UiProject, on_delete=models.CASCADE, related_name='elements', verbose_name='所属项目')
    group = models.ForeignKey(ElementGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name='elements', verbose_name='所属分组')
    name = models.CharField(max_length=200, verbose_name='元素名称')
    description = models.TextField(blank=True, verbose_name='元素描述')
    element_type = models.CharField(max_length=50, choices=ELEMENT_TYPE_CHOICES, verbose_name='元素类型', default='BUTTON')

    # 主要定位策略
    locator_strategy = models.ForeignKey(LocatorStrategy, on_delete=models.PROTECT, verbose_name='定位策略')
    locator_value = models.CharField(max_length=500, verbose_name='定位表达式')

    # 备用定位策略
    backup_locators = models.JSONField(
        blank=True,
        null=True,
        verbose_name='备用定位器',
        help_text='多个定位策略的JSON数组，格式：[{"strategy": "css", "value": ".button"}, ...]'
    )

    page = models.CharField(max_length=200, verbose_name='所属页面', blank=True)
    component_name = models.CharField(max_length=100, blank=True, verbose_name='组件名称', help_text='所属UI组件名称')

    # 元素层次关系
    parent_element = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='父元素', help_text='用于构建元素层次结构')

    # 元素属性
    is_unique = models.BooleanField(default=False, verbose_name='是否唯一')
    wait_timeout = models.IntegerField(default=5, verbose_name='等待超时(秒)')
    is_visible = models.BooleanField(default=True, verbose_name='是否可见')
    is_enabled = models.BooleanField(default=True, verbose_name='是否启用')
    force_action = models.BooleanField(default=False, verbose_name='强制操作', help_text='对visibility:hidden的元素使用force选项')

    # 统计信息
    usage_count = models.IntegerField(default=0, verbose_name='使用次数', help_text='在脚本中被引用的次数')
    last_validated = models.DateTimeField(null=True, blank=True, verbose_name='最后验证时间')
    validation_status = models.CharField(max_length=20, choices=VALIDATION_STATUS_CHOICES, default='UNKNOWN', verbose_name='验证状态')
    validation_message = models.TextField(blank=True, verbose_name='验证消息')

    # 基础字段
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'ui_elements'
        verbose_name = 'UI元素'
        verbose_name_plural = 'UI元素'
        ordering = ['page', 'name']
        indexes = [
            models.Index(fields=['project', 'page']),
            models.Index(fields=['project', 'element_type']),
            models.Index(fields=['validation_status']),
        ]

    def __str__(self):
        return f'{self.page}: {self.name}' if self.page else self.name

    def increment_usage_count(self):
        """增加使用次数"""
        self.usage_count = models.F('usage_count') + 1
        self.save(update_fields=['usage_count'])

    def get_all_locators(self):
        """获取所有定位器（主要+备用）"""
        locators = [{
            'strategy': self.locator_strategy.name,
            'value': self.locator_value,
            'is_primary': True
        }]

        if self.backup_locators:
            for backup in self.backup_locators:
                locators.append({
                    'strategy': backup.get('strategy'),
                    'value': backup.get('value'),
                    'is_primary': False
                })

        return locators


class PageObject(models.Model):
    """页面对象模型"""
    name = models.CharField(max_length=200, verbose_name='页面对象名称')
    class_name = models.CharField(max_length=200, verbose_name='类名')
    url_pattern = models.CharField(max_length=500, blank=True, verbose_name='URL模式', help_text='页面URL模式，支持正则表达式')
    project = models.ForeignKey(UiProject, on_delete=models.CASCADE, related_name='page_objects', verbose_name='所属项目')
    description = models.TextField(blank=True, verbose_name='描述')
    template_code = models.TextField(blank=True, verbose_name='模板代码', help_text='生成的页面对象代码模板')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'ui_page_objects'
        verbose_name = '页面对象'
        verbose_name_plural = '页面对象'
        ordering = ['name']
        unique_together = ['project', 'name']

    def __str__(self):
        return self.name

    def generate_code(self, language='javascript'):
        """生成页面对象代码"""
        if language == 'javascript':
            return self._generate_javascript_code()
        elif language == 'python':
            return self._generate_python_code()
        else:
            raise ValueError(f"Unsupported language: {language}")

    def _generate_javascript_code(self):
        """生成JavaScript页面对象代码"""
        elements = self.page_object_elements.all()

        # 生成元素属性
        element_props = []
        methods = []

        for po_element in elements:
            element = po_element.element
            if po_element.is_property:
                element_props.append(
                    f"        this.{po_element.method_name} = page.locator('{element.locator_value}');"
                )
            else:
                methods.append(f"""
    async {po_element.method_name}() {{
        return this.page.locator('{element.locator_value}');
    }}""")

        template = f"""
class {self.class_name} {{
    constructor(page) {{
        this.page = page;
{chr(10).join(element_props)}
    }}
{chr(10).join(methods)}
}}
        """.strip()

        return template

    def _generate_python_code(self):
        """生成Python页面对象代码"""
        elements = self.page_object_elements.all()

        methods = []
        for po_element in elements:
            element = po_element.element
            methods.append(f"""
    def {po_element.method_name}(self):
        return self.page.locator('{element.locator_value}')""")

        template = f"""
class {self.class_name}:
    def __init__(self, page):
        self.page = page
{chr(10).join(methods)}
        """.strip()

        return template


class PageObjectElement(models.Model):
    """页面对象与元素的关联"""
    page_object = models.ForeignKey(PageObject, on_delete=models.CASCADE, related_name='page_object_elements', verbose_name='页面对象')
    element = models.ForeignKey(Element, on_delete=models.CASCADE, verbose_name='元素')
    method_name = models.CharField(max_length=100, verbose_name='方法名称', help_text='在页面对象中的方法/属性名称')
    is_property = models.BooleanField(default=True, verbose_name='是否为属性', help_text='True为属性，False为方法')
    order = models.IntegerField(default=0, verbose_name='排序')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'ui_page_object_elements'
        verbose_name = '页面对象元素关联'
        verbose_name_plural = '页面对象元素关联'
        unique_together = ['page_object', 'method_name']
        ordering = ['order', 'method_name']

    def __str__(self):
        return f'{self.page_object.name}.{self.method_name}'


