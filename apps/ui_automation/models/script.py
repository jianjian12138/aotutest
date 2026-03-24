from apps.notifications.models import NotificationConfig
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()
from django.utils import timezone
import json
from .project import UiProject
from .element import Element, PageObject

class TestScript(models.Model):
    """测试脚本模型"""
    SCRIPT_TYPE_CHOICES = [
        ('CODE', '代码'),
        ('LOW_CODE', '低代码'),
        ('NO_CODE', '无代码'),
    ]

    LANGUAGE_CHOICES = [
        ('python', 'Python'),
        ('javascript', 'JavaScript'),
    ]

    FRAMEWORK_CHOICES = [
        ('playwright', 'Playwright'),
        ('selenium', 'Selenium'),
        ('airtest', 'Airtest'),
    ]

    project = models.ForeignKey(UiProject, on_delete=models.CASCADE, related_name='test_scripts', verbose_name='所属项目')
    name = models.CharField(max_length=200, verbose_name='脚本名称')
    description = models.TextField(blank=True, verbose_name='脚本描述')
    script_type = models.CharField(max_length=20, choices=SCRIPT_TYPE_CHOICES, verbose_name='脚本类型', default='LOW_CODE')
    content = models.TextField(verbose_name='脚本内容')  # 可以是代码或JSON格式的低代码配置
    language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES, verbose_name='脚本语言', default='python', blank=True)
    framework = models.CharField(max_length=20, choices=FRAMEWORK_CHOICES, verbose_name='执行框架', default='playwright', blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'ui_test_scripts'
        verbose_name = 'UI测试脚本'
        verbose_name_plural = 'UI测试脚本'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class ScriptStep(models.Model):
    """脚本步骤模型"""
    ACTION_TYPE_CHOICES = [
        ('CLICK', '点击'),
        ('INPUT', '输入'),
        ('SELECT', '选择'),
        ('VERIFY', '验证'),
        ('WAIT', '等待'),
        ('HOVER', '悬停'),
        ('SCROLL', '滚动'),
        ('NAVIGATE', '导航'),
        ('SCREENSHOT', '截图'),
        ('SWITCH_TAB', '切换标签页'),
        ('AI_ACT', 'AI操作(Stagehand)'),
        ('AI_EXTRACT', 'AI提取(Stagehand)'),
        ('AI_VISION', 'AI视觉操作(Magnitude)'),
        ('drag_and_drop', '拖拽'),
        ('upload', '文件上传'),
        ('custom', '自定义'),
    ]

    script = models.ForeignKey(TestScript, on_delete=models.CASCADE, related_name='steps', verbose_name='所属脚本')
    step_order = models.IntegerField(verbose_name='步骤顺序')
    action_type = models.CharField(max_length=20, choices=ACTION_TYPE_CHOICES, verbose_name='操作类型')
    target_element = models.ForeignKey(Element, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='目标元素')
    page_object = models.ForeignKey(PageObject, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='页面对象')

    # 操作参数
    action_params = models.JSONField(blank=True, null=True, verbose_name='操作参数', help_text='JSON格式的操作参数')

    # 步骤描述
    description = models.CharField(max_length=500, verbose_name='步骤描述')
    expected_result = models.CharField(max_length=500, blank=True, verbose_name='预期结果')

    # 执行配置
    wait_before = models.IntegerField(default=0, verbose_name='执行前等待(毫秒)')
    wait_after = models.IntegerField(default=0, verbose_name='执行后等待(毫秒)')
    retry_count = models.IntegerField(default=0, verbose_name='重试次数')
    enable_debug_capture = models.BooleanField(default=False, verbose_name='启用调试采集')
    extract_key = models.CharField(max_length=100, null=True, blank=True, verbose_name='提取字典键', help_text='若填写,结果(如获取文本)将保存至上下文变量池')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'ui_script_steps'
        verbose_name = '脚本步骤'
        verbose_name_plural = '脚本步骤'
        ordering = ['step_order']
        unique_together = ['script', 'step_order']

    def __str__(self):
        return f'{self.script.name} - Step {self.step_order}: {self.action_type}'


class ScriptElementUsage(models.Model):
    """脚本元素使用记录"""
    USAGE_TYPE_CHOICES = [
        ('CLICK', '点击'),
        ('INPUT', '输入'),
        ('VERIFY', '验证'),
        ('WAIT', '等待'),
        ('HOVER', '悬停'),
        ('SELECT', '选择'),
        ('SCROLL', '滚动'),
        ('ATTRIBUTE', '属性获取'),
        ('TEXT', '文本获取'),
    ]

    script = models.ForeignKey(TestScript, on_delete=models.CASCADE, related_name='element_usages', verbose_name='脚本')
    element = models.ForeignKey(Element, on_delete=models.CASCADE, related_name='script_usages', verbose_name='元素')
    usage_type = models.CharField(max_length=50, choices=USAGE_TYPE_CHOICES, verbose_name='使用类型')
    line_number = models.IntegerField(verbose_name='行号', help_text='在脚本中的行号')
    context = models.TextField(blank=True, verbose_name='上下文代码', help_text='使用元素的代码上下文')
    frequency = models.IntegerField(default=1, verbose_name='使用频次', help_text='在脚本中使用的次数')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'ui_script_element_usages'
        verbose_name = '脚本元素使用记录'
        verbose_name_plural = '脚本元素使用记录'
        unique_together = ['script', 'element', 'line_number']
        ordering = ['script', 'line_number']

    def __str__(self):
        return f'{self.script.name} uses {self.element.name} ({self.usage_type})'


