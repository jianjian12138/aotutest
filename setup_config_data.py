import os
import django
import sys

# 设置 Django 环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.assistant.models import AIWorkflowConfig

def seed_workflows_and_mcp():
    print("🚀 开始为 [MCP 管理] & [工作流配置] 注入平台生态数据...")
    
    # 清理旧测试数据避免重复
    AIWorkflowConfig.objects.all().delete()
    
    # ----------------
    # 1. MCP 服务器节点配置
    # ----------------
    mcp_configs = [
        {
            "name": "Local Filesystem & OS Access (本地权限基建)",
            "provider": "mcp",
            "mcp_type": "local",
            "api_url": "npx -y @modelcontextprotocol/server-everything",
            "is_active": True,
            "additional_config": {
                "deploy_mode": "local",
                "mcp_args": "--allow-read --allow-write"
            }
        },
        {
            "name": "GitHub Repository Scanner (企业源码审查)",
            "provider": "mcp",
            "mcp_type": "remote",
            "api_url": "https://mcp.github.com/v1/tools",
            "api_key": "ghp_mock_XXXXXXXXXXXXXXXXXXXXXXXXXXXX",
            "is_active": True,
            "additional_config": {
                "deploy_mode": "online",
                "mcp_type": "sse"
            }
        },
        {
            "name": "PostgreSQL Metadata Inspector (数据库表结构探测)",
            "provider": "mcp",
            "mcp_type": "local",
            "api_url": "python -m mcp_postgres_analyzer",
            "is_active": False,
            "additional_config": {
                "deploy_mode": "local",
                "mcp_env": {"PG_URI": "postgresql://admin:123@127.0.0.1:5432/ruoyi"}
            }
        }
    ]
    
    for m in mcp_configs:
        AIWorkflowConfig.objects.create(**m)
        print(f"✅ 生成 MCP 节点: {m['name']}")


    # ----------------
    # 2. AI 工作流 (Workflow) 配置
    # ----------------
    workflow_configs = [
        {
            "name": "Dify RAG 内测文档问答流 (Staging)",
            "provider": "dify",
            "api_url": "http://192.168.10.12/v1",
            "api_key": "app-dify-XXXXXXXXXXXXXXXXXXXX",
            "workflow_id": "sys_knowledge_graph_rag",
            "is_active": True,
            "additional_config": {"deploy_mode": "local"}
        },
        {
            "name": "Coze 自动化视觉缺陷断言流 (SaaS)",
            "provider": "coze",
            "api_url": "https://api.coze.com/open_api/v2",
            "api_key": "pat_coze_XXXXXXXXXXXXXXXXXXXX",
            "workflow_id": "vision_bug_detector_7210x",
            "is_active": True,
            "additional_config": {"deploy_mode": "online"}
        },
        {
            "name": "n8n CI/CD 飞书告警分发管道",
            "provider": "n8n",
            "api_url": "http://localhost:5678/webhook",
            "is_active": False,
            "additional_config": {"deploy_mode": "local"}
        }
    ]
    
    for w in workflow_configs:
        AIWorkflowConfig.objects.create(**w)
        print(f"✅ 生成 工作流配置: {w['name']}")

    print("\n🎉 MCP 与 工作流平台数据配置写入成功！")

if __name__ == '__main__':
    seed_workflows_and_mcp()
