import os
import django
import sys
from datetime import timedelta
import random

# 设置 Django 环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.utils import timezone
from apps.core_platform.models import User, Project
from apps.requirement_analysis.models import (
    RequirementDocument, 
    RequirementAnalysis, 
    BusinessRequirement, 
    GeneratedTestCase
)

def populate_platform_requirements():
    print("🚀 开始注入真实 AI 智能测试平台 (http://localhost:5656) 本身的 Requirement & Test Cases 架构数据...")

    # 获取默认用户和项目
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.first()
    
    project = Project.objects.filter(name="针对平台自身的自测项目").first()
    if not project:
        project = Project.objects.first()

    # 清除之前所有自动生成的数据
    RequirementDocument.objects.filter(title__startswith="[Auto-Gen]").delete()
    RequirementDocument.objects.filter(title__startswith="[Platform-Spec]").delete()

    now = timezone.now()

    # 1. 创建平台相关的需求文档
    docs = [
        {
            "title": "[Platform-Spec] AI智能测试平台v1.0 产品需求规格说明书.pdf",
            "type": "pdf",
            "size": 1024 * 1024 * 8.5,
            "text": "1. UI自动化录制回放引擎集成设计\n2. 引入 DeepSeek 驱动大模型智能生成测试用例\n3. 全局定时调度中心设计 (Cron表达式支持)\n4. Webhook 第三方群机器人通知 (飞书/钉钉)"
        },
        {
            "title": "[Platform-Spec] 统一测试看板报告渲染与分析系统架构设计.docx",
            "type": "docx",
            "size": 1024 * 1024 * 1.2,
            "text": "1. 统一接口与 UI 异步测试的跨数据库关联映射模型\n2. 支持十万级测试日志记录的渲染性能优化\n3. API 性能压测的实时图标数据分析"
        }
    ]

    for doc_data in docs:
        doc = RequirementDocument.objects.create(
            title=doc_data['title'],
            document_type=doc_data['type'],
            status='analyzed',
            uploaded_by=admin_user,
            project=project,
            file_size=doc_data['size'],
            extracted_text=doc_data['text'],
            created_at=now - timedelta(days=random.randint(1, 3))
        )
        print(f"✅ 创建需求评审文档: {doc.title}")

        analysis = RequirementAnalysis.objects.create(
            document=doc,
            analysis_report=f"【AI 文档分析】：已成功解构文档 {doc.title}。\n从架构文档中提取出围绕「测试执行调度」与「大模型自动生成」的核心测试平台自构建要求，建议立刻分配给研发与测试部门建立回归基线。",
            requirements_count=random.randint(4, 9),
            analysis_time=15.8,
            created_at=doc.created_at + timedelta(minutes=2)
        )

        
        # 3. 创建 Business Requirements (根据不同文档分配不同的具体需求)
        if "v1.0" in doc.title:
            req_templates = [
                {"name": "UI自动化录制回放引擎集成", "type": "functional", "module": "UI自动化", "level": "high", "desc": "系统需内置 Playwright 无头浏览器驱动环境，允许编写跨域页面点击、表单回填等端到端 (E2E) 测试用例，并支持捕获截图和执行录屏。"},
                {"name": "DeepSeek 大模型自动生成用例", "type": "functional", "module": "需求和用例", "level": "high", "desc": "基于用户上传的 PRD 产品需求文档或文本输入，调用本地 / 云端 LLM，自动解析并下钻生成标准格式的断言测试用例，并覆盖正向与异常场景。"},
                {"name": "全局调度中心配置", "type": "functional", "module": "调度中心", "level": "medium", "desc": "利用 Celery/APScheduler 支持挂载执行套件，用户可配置标准的 Cron 表达式实现凌晨无人值守的健康巡检。"},
                {"name": "第三方 Webhook 飞书告警推送", "type": "interface", "module": "通知中心", "level": "medium", "desc": "测试任务执行完成或者崩溃后，异步抓取测试看板统计报表并构造卡片格式的 Markdown Payload 推送至指定的飞书/钉钉机器人群组。"}
            ]
        else:
            req_templates = [
                {"name": "多维测试报告异步聚合并视", "type": "usability", "module": "统一看板", "level": "high", "desc": "解决 UI执行记录和 API执行记录的数据库异构问题，通过统一对象层拦截 (TestReport) 实现全局唯一看板聚合显示。"},
                {"name": "百万级接口响应测试数据渲染优化", "type": "performance", "module": "统一看板", "level": "high", "desc": "统一测试大屏需要能够顺滑支撑单次超过 100 万级 API HTTP 响应日志返回对象的渲染解析，不能发生 Vue DOM Crash (OOM)。"}
            ]

        for i, req_tmp in enumerate(req_templates):
            req = BusinessRequirement.objects.create(
                analysis=analysis,
                requirement_id=f"PTR-{doc.id}-{100+i}",
                requirement_name=req_tmp['name'],
                requirement_type=req_tmp['type'],
                module=req_tmp['module'],
                requirement_level=req_tmp['level'],
                reviewer="测试平台 AI",
                description=req_tmp['desc'],
                acceptance_criteria=f"验证平台内部的【{req_tmp['name']}】模块能够按照设定的架构规范稳健流转数据包。",
                created_at=analysis.created_at + timedelta(minutes=8)
            )
            print(f"  └─ 归纳平台业务需求: {req.requirement_id} - {req.requirement_name}")

            # 4. 创建生成的测试用例
            for j in range(random.randint(2, 4)):
                status_choices = ['generated', 'reviewing', 'approved', 'adopted']
                
                # 为用例生成贴合平台自身的测试步骤文案
                test_steps = (
                    f"1. 登录 http://localhost:5656 测试平台后门\n"
                    f"2. 导航至左侧树形菜单：【{req_tmp['module']}】\n"
                    f"3. 构造平台底层模型负载测试（Mock 数据组：Platform_Load_Testing_Set_{j+1}）\n"
                    f"4. 发起调用请求并检查返回状态码及内容解析完整度"
                )
                
                GeneratedTestCase.objects.create(
                    requirement=req,
                    case_id=f"P-TC-{req.requirement_id}-{j+1}",
                    title=f"自测场景：验证内部模块 {req.requirement_name} 在并发或异常态下的健壮性",
                    priority="P1" if req_tmp['level'] == 'high' else "P2",
                    precondition="1. 测试平台后端 (0.0.0.0:4545) 运行状态良好\n2. 对应的 PostgreSQL 数据库引擎没有锁表",
                    test_steps=test_steps,
                    expected_result="后端应不报错 500 引发系统崩溃；前端 UI 能够正常给出 Toast 交互反馈；所有状态迁移均有迹可循。",
                    status=random.choice(status_choices),
                    generated_by_ai="DeepSeek-Coder-V2",
                    reviewed_by_ai="Qwen-Max",
                    review_comments="该内部自测步骤完整，已覆盖核心断言节点，准入。" if random.random() > 0.4 else "用例缺乏性能瓶颈压力限定条件，建议人工复核。",
                    created_at=req.created_at + timedelta(minutes=15)
                )

    print("\n🎉 专门针对该测试平台本身的自需求/自测试架构数据注入完成！请刷新前端页面查看【需求和用例】仪表盘。")

if __name__ == "__main__":
    populate_platform_requirements()
