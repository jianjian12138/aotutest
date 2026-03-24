import os
import django
import sys

# 初始化 Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.ui_automation.models import ElementGroup, Element, LocatorStrategy
from apps.core_platform.models import Project

def seed_elements():
    print("🚀 开始为 [UI自动化 -> 元素管理] 填充数据...")
    
    # 确保定位策略存在
    xpath_strategy, _ = LocatorStrategy.objects.get_or_create(name='xpath', defaults={'description': 'XPath 相对/绝对路径定位'})
    css_strategy, _ = LocatorStrategy.objects.get_or_create(name='css', defaults={'description': 'CSS 选择器定位'})
    id_strategy, _ = LocatorStrategy.objects.get_or_create(name='id', defaults={'description': 'DOM 元素 ID 定位'})
    name_strategy, _ = LocatorStrategy.objects.get_or_create(name='name', defaults={'description': 'DOM 元素 name 属性'})
    
    # 获取所有的 ElementGroup (在截图中叫 "Page - Login", "Page - Dashboard" 等)
    groups = list(ElementGroup.objects.all())
    if not groups:
        # 如果不存在分组，则随便找一个项目创建一个分组
        project = Project.objects.first()
        if not project:
            print("❌ 找不到任何项目，终止生成")
            return
        # 这里需要注意 UiProject，由于模型可能拆分了，可能不是 core_platform 的 Project
        # 我们这里安全点，既然页面上能看到分组，说明分组肯定存在
        print("❌ 警告：数据库中未找到任何 ElementGroup 分组")

    elements_to_create = []
    
    # 针对常见的组生成一些配套元素
    for group in groups:
        group_name = group.name.lower()
        project = group.project
        
        if 'login' in group_name:
            elements_to_create.extend([
                Element(project=project, group=group, name='Admin账号输入框', element_type='INPUT', locator_strategy=css_strategy, locator_value='#username', description='核心登录页面的用户名输入框', page=group.name, is_unique=True),
                Element(project=project, group=group, name='Password密码输入框', element_type='INPUT', locator_strategy=css_strategy, locator_value='#password', description='核心登录页面的密码输入框', page=group.name, is_unique=True),
                Element(project=project, group=group, name='统一认证登录按钮', element_type='BUTTON', locator_strategy=xpath_strategy, locator_value='//button[@type="submit"]', description='核心登录页面的主提交按钮', page=group.name, is_unique=True),
                Element(project=project, group=group, name='找回密码链接', element_type='LINK', locator_strategy=xpath_strategy, locator_value='//a[contains(text(),"忘记密码")]', description='找回密码跳转链接', page=group.name, is_unique=False)
            ])
        elif 'dashboard' in group_name:
            elements_to_create.extend([
                Element(project=project, group=group, name='用户资料卡片', element_type='CONTAINER', locator_strategy=css_strategy, locator_value='.user-profile-card', description='大盘右上角用户信息框', page=group.name),
                Element(project=project, group=group, name='数据导出Excel图标', element_type='BUTTON', locator_strategy=xpath_strategy, locator_value='//*[@id="export-btn"]', description='点击后导出报表', page=group.name),
                Element(project=project, group=group, name='侧边栏折叠开关', element_type='BUTTON', locator_strategy=css_strategy, locator_value='.el-aside .collapse-btn', description='收起左侧导航树', page=group.name)
            ])
        elif 'api' in group_name or 'testing' in group_name:
            elements_to_create.extend([
                Element(project=project, group=group, name='新建接口测试用例按钮', element_type='BUTTON', locator_strategy=css_strategy, locator_value='.create-api-case-btn', page=group.name),
                Element(project=project, group=group, name='请求方法下拉框', element_type='DROPDOWN', locator_strategy=id_strategy, locator_value='method-select', page=group.name),
                Element(project=project, group=group, name='发送请求(Send)按钮', element_type='BUTTON', locator_strategy=xpath_strategy, locator_value='//button[contains(@class,"send-request")]', page=group.name),
                Element(project=project, group=group, name='响应断言表格', element_type='TABLE', locator_strategy=css_strategy, locator_value='#assertion-table', page=group.name)
            ])
        elif 'performance' in group_name:
             elements_to_create.extend([
                Element(project=project, group=group, name='并发数滑块', element_type='INPUT', locator_strategy=id_strategy, locator_value='concurrency-slider', page=group.name),
                Element(project=project, group=group, name='压测目标服务器下拉框', element_type='DROPDOWN', locator_strategy=css_strategy, locator_value='.target-env-select', page=group.name),
                Element(project=project, group=group, name='启动Locust引擎按钮', element_type='BUTTON', locator_strategy=xpath_strategy, locator_value='//button//span[text()="启动压测"]', page=group.name)
            ])
        else:
             # 通用填充
             elements_to_create.extend([
                Element(project=project, group=group, name='新建资源按钮', element_type='BUTTON', locator_strategy=css_strategy, locator_value='.el-button--primary.create-btn', page=group.name),
                Element(project=project, group=group, name='查询搜索框', element_type='INPUT', locator_strategy=css_strategy, locator_value='.search-input input', page=group.name),
                Element(project=project, group=group, name='主干数据表格', element_type='TABLE', locator_strategy=css_strategy, locator_value='.el-table__body-wrapper', page=group.name),
                Element(project=project, group=group, name='批量删除图标', element_type='BUTTON', locator_strategy=xpath_strategy, locator_value='//i[contains(@class, "el-icon-delete")]', page=group.name)
            ])

    # 清理所有已存在元素以防止重复堆叠
    Element.objects.all().delete()
    
    Element.objects.bulk_create(elements_to_create)
    print(f"✅ 成功生成 {len(elements_to_create)} 个 UI Automation 元素节点定义！请刷新页面查看！")

if __name__ == '__main__':
    seed_elements()
