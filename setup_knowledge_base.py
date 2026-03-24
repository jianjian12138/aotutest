import os
import django
import sys
import uuid
import shutil

# 设置 Django 环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.conf import settings
from apps.knowledge_graph.models import KnowledgeDocument
from apps.knowledge_graph.services import KnowledgeGraphService

def seed_knowledge_base():
    docs_dir = os.path.join(settings.MEDIA_ROOT, 'knowledge_docs')
    os.makedirs(docs_dir, exist_ok=True)
    
    documents_data = [
        {
            "name": "AI辅助测试平台 - OpenAPI 接口文档 reference v1.2",
            "filename": "api_reference_v1_2.md",
            "content": """# AI测试平台 OpenAPI 参考文档

## 1. 认证机制
平台采用 Bearer Token 鉴权体系。所有对外暴露的 API 请求头必须附带 `Authorization: Bearer <Your_Token>`。
获取 Token 的路由为 `/api/v1/auth/login`。有效时间为 24 小时。

## 2. 核心模块 API

### 2.1 性能测试 (Performance Testing)
- `POST /api/v1/performance-testing/executions/`: 触发压测任务执行。参数 `{"test_suite_id": 12, "concurrency": 1000, "duration": 60}`
- `GET /api/v1/performance-testing/dashboard/summary/`: 拉取性能大盘聚合指标，包含集合数量，最近5次失败记录。

### 2.2 智能用例生成 (AI Use Case Generation)
- `POST /api/v1/requirement-analysis/analyze/`: 提交业务需求文档给大模型。参数 `{"document_id": "uuid", "model_config_id": "config_uuid"}`。返回结构化的测试用例树。
- `GET /api/v1/knowledge-graph/search/?query={text}`: RAG 查询接入点。返回知识库检索出的强相关实体关联与文档切片。

## 3. 错误码规范
- `200 OK`: 请求成功
- `401 Unauthorized`: Token 失效或被吊销
- `403 Forbidden`: 越权访问（非项目成员尝试操作项目资源）
- `500 Internal Server Error`: 大模型网关熔断或数据库主从同步超时
"""
        },
        {
            "name": "QA工程师测试平台使用白皮书 (V2 架构版)",
            "filename": "qa_user_manual_v2.md",
            "content": """# 测试平台使用说明书

## 一、平台整体定位
这是一款融合了“性能压测、UI 自动化巡检、智能需求分析和接口扫描”四大垂直场景的次世代 AI 测试管理中枢。
目标是将传统的“人工抓包 -> 脑暴用例 -> 组装脚本 -> 查看报告”流水线通过自然语言完全重构。

## 二、功能模块指引
1. **工作台 (Workspace)**: 登录后的首屏，展示本周您的用例通过率曲线与分配给您的专项缺陷。
2. **用例工厂 (Data Factory)**: 提供 MySQL 和 PostgreSQL 的表结构同步能力，用于自动化生成数据驱动的测试组。
3. **UI 自动化 (Playwright Engine)**: 在页面录制用户行为轨迹并一键转换为 Python 自动化脚本，支持静默流测试。
4. **性能测试引擎 (Locust Backend)**: 支持高达万级并发的微服务轰炸测试，原生汇出 RPS 与 99分位响应时延折线图。
5. **智能大模型配置**: 管理各个平台的云端 API Key，您可以随需切分不同模块使用的模型代理。

## 三、部署及运维要求
- **环境**: 必须开启 Redis 持久化支持因为 Celery Scheduler 依赖其作为 Broker。
- **存储**: 测试附件（如 Playwright 截取的 HTML Traces）将落盘于 `media/ui_traces`，请定期分配生命周期规则删除冷流数据。
"""
        },
        {
            "name": "专项测试工具流操作规范 (MQTT/Redis/Kafka)",
            "filename": "special_testing_tools.md",
            "content": """# 专项测试与中间件稳定性压测规范

除了常规的 HTTP(s) 层级校验，平台内置了专属底层设施的压力验证引擎，可以在【专项测试】模块下调取。

## 1. Redis 缓存雪崩与击穿模拟
通过向指定的 Key 生成器并行注入不可预测的热点数据，强行拉高 `keyspace_misses` 指标。
操作步骤：
- 在大盘选择 Redis 工具
- 配置压测目标（如 `redis://admin:123@192.168.1.10:6379`）
- 设定 1000 并发同时 GET 无法命中的散列键。

## 2. Kafka 消息队列拥堵水位压测
测试微服务消费者的消费极限能否扛住双十一峰值。
支持设置：
- `Producer Count`: 生产者集群规模
- `Payload Size`: 单条序列化消息的 Byte 体积
- `Acks`: 等待主从节点确认同步策略（all, 1, 0）

## 3. 移动端 Monkey 暴力探索
使用 Android ADB 通道进行的盲点点击，每秒可发送高达 50 次 MotionEvent 及 KeyEvent。
请注意：此测试极其耗费测试机的电池与运存，并在结束前很可能直接引发宿主 App 的 OOM。
"""
        }
    ]

    print("🚀 开始为知识库(Knowledge Graph)注入平台使用文档...")
    
    # 清理旧数据避免重复
    KnowledgeDocument.objects.all().delete()
    
    for idx, doc_data in enumerate(documents_data):
        file_path = os.path.join(docs_dir, doc_data["filename"])
        
        # 写入物理文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(doc_data["content"])
            
        # 计算大小
        file_size = os.path.getsize(file_path)
        
        # 创建数据库记录
        doc = KnowledgeDocument.objects.create(
            name=doc_data["name"],
            file_path=file_path,
            file_type="md",
            size=file_size,
            status="pending",
            source_type="file"
        )
        
        print(f"[{idx+1}/{len(documents_data)}] {doc.name} (已落盘: {file_size} Bytes)")
        
        # 调用核心 Service 对 Markdown 进行切割 (Chunking) 和提取
        try:
            KnowledgeGraphService.process_document(doc.id)
            print(f"   => 切割/解析成功, 生成切片数量: {doc.chunks.count()}")
        except Exception as e:
            print(f"   => [!] 解析发生异常(可能有Langchain环境问题): {e}")

    print("\n🎉 知识库内建自发文档生成并索引完毕！")

if __name__ == '__main__':
    seed_knowledge_base()
