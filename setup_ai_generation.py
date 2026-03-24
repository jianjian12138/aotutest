import os
import django
import sys
from datetime import timedelta
from django.utils import timezone

# 设置 Django 环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.core_platform.models import User, Project
from apps.requirement_analysis.models import (
    PromptConfig,
    AIModelConfig,
    TestCaseGenerationTask
)

def setup_ai_generation():
    print("🚀 开始注入【提示词配置】、【AI模型配置】及【智能用例生成】测试数据...")

    # 获取默认用户和项目
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.first()
    
    project = Project.objects.filter(name="针对平台自身的自测项目").first()
    if not project:
        project = Project.objects.first()

    now = timezone.now()

    # 1. 注入提示词配置 (PromptConfig)
    print("注入提示词...")
    PromptConfig.objects.all().delete()
    
    writer_prompt = PromptConfig.objects.create(
        name="DeepSeek 核心用例提炼系统提示词",
        prompt_type="writer",
        content="你是一个从业15年的资深测试工程师。请阅读用户提供的【需求说明】或【PRD文档片段】，并按照以下格式输出测试用例：\n\n1. 用例编号 (例如: TC-001)\n2. 用例名称 (例如: 登录密码错误容错)\n3. 优先级 (P0/P1/P2/P3)\n4. 前置条件\n5. 详细测试操作步骤\n6. 期望系统结果响应\n\n要求：必须覆盖至少1个正向主流程场景和2个异常拦截场景。排版清晰，专业严谨。",
        is_active=True,
        created_by=admin_user,
        created_at=now
    )
    
    reviewer_prompt = PromptConfig.objects.create(
        name="Qwen 自动化用例多维评审提示词",
        prompt_type="reviewer",
        content="你是一个严格的 QA 审核专家。请评审下面的草稿测试用例集是否符合准入标准：\n1. 边界值是否考虑？\n2. 步骤逻辑是否完整可执行？\n3. 预期结果是否唯一且客观可判言定？\n如果符合，请回复【通过并采纳】。如果不符合，请直接指出修改意见。",
        is_active=True,
        created_by=admin_user,
        created_at=now
    )

    # 2. 注入AI模型配置 (AIModelConfig) (使用占位符，仅为了UI展示)
    print("注入AI模型配置...")
    AIModelConfig.objects.all().delete()
    
    writer_model = AIModelConfig.objects.create(
        name="[预置] 阿里通义千问大模型 (Qwen-Turbo)",
        model_type="qwen",
        role="writer",
        api_key="sk-xxxxxxxxx",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model_name="qwen-turbo",
        max_tokens=4095,
        temperature=0.7,
        top_p=0.9,
        is_active=True,
        created_by=admin_user,
        created_at=now
    )
    
    reviewer_model = AIModelConfig.objects.create(
        name="[预置] 硅基流动云端模型 (DeepSeek-V3)",
        model_type="siliconflow",
        role="reviewer",
        api_key="sk-yyyyyyy",
        base_url="https://api.siliconflow.cn/v1",
        model_name="deepseek-ai/DeepSeek-V3",
        max_tokens=2048,
        temperature=0.3,
        top_p=0.9,
        is_active=True,
        created_by=admin_user,
        created_at=now
    )

    # 3. 注入智能用例生成测试任务 (TestCaseGenerationTask)
    print("生成测试用例生成历史任务...")
    TestCaseGenerationTask.objects.all().delete()
    
    # 模拟一个执行成功的历史记录 (方便用户在平台前台直接看到报告)
    generated_text = """### 生成结果:
1. 用例编号: TC-LOGIN-01
2. 用例名称: 飞书WebHook告警正常触发测试
3. 优先级: P0
4. 前置条件: 调度中心任务配置完毕，Webhook URL 有效
5. 操作步骤:
   - 触发 0.0.0.0:4545 的健康巡检任务
   - 截取 HTTP 响应流
   - 监控系统状态日志
6. 期望结果: 控制台输出 `Webhook Dispatch Success`，飞书群收到告警卡片。
"""
    
    review_text = """### 专家评审意见：
✅ 步骤清晰，目标路径定义准确。
⚠️ 建议补充 `Webhook URL` 无效时的异常断言抛出（Timeout 或 403 容错）。
综合结论：【通过并采纳】。"""

    task = TestCaseGenerationTask.objects.create(
        task_id="TKG-TEST-0001",
        title="[AI测试] 飞书 Webhook 告警链路自测用例生成",
        requirement_text="需要编写用例，验证当自动化系统跑完测试后，能否将汇总生成的 TestReport 通过 API 推送给飞书机器人的 Webhook，并在网络中断时进行异常熔断。",
        status="completed",
        progress=100,
        project=project,
        writer_model_config=writer_model,
        reviewer_model_config=reviewer_model,
        writer_prompt_config=writer_prompt,
        reviewer_prompt_config=reviewer_prompt,
        generated_test_cases=generated_text,
        review_feedback=review_text,
        final_test_cases=generated_text + "\n\n" + review_text,
        generation_log="[16:40:01] 触发模型生成请求...\n[16:40:15] Writer大模型(Qwen)响应成功，耗时 14s\n[16:40:17] 触发 Reviewer大模型(DeepSeek)评审请求...\n[16:40:29] Reviewer大模型评审完成。\n[16:40:30] 任务结束，已发回给用户。",
        created_by=admin_user,
        created_at=now - timedelta(minutes=15),
        completed_at=now - timedelta(minutes=14)
    )

    print("\n🎉 【提示词】与【AI生成记录】数据注入完成！您可以前往平台相应菜单查看。")

if __name__ == "__main__":
    setup_ai_generation()
