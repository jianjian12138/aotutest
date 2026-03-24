import os
import django
import sys
import random
from datetime import timedelta

# 设置 Django 环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.utils import timezone
from apps.core_platform.models import User
from apps.performance_test.models import (
    PerformanceProject,
    PerformanceCollection,
    PerformanceRequest,
    PerformanceEnvironment,
    PerformanceTestSuite,
    PerformanceTestSuiteRequest,
    PerformanceTestExecution,
    PerformanceTestHistory
)

def setup_performance_tests():
    print("🚀 开始架构【性能测试】负载数据 (Target: http://localhost:5656) ...")

    admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
    now = timezone.now()

    env, _ = PerformanceEnvironment.objects.get_or_create(
        name="本地平台基准压测环境 (Localhost)",
        defaults={
            "description": "针对当前运行的 AI 测试平台本体进行并发摸底",
            "scope": "GLOBAL",
            "variables": {"base_url": "http://localhost:5656"},
            "is_active": True,
            "created_by": admin_user
        }
    )

    project, _ = PerformanceProject.objects.get_or_create(
        name="AI测试平台核心链路高并发压测",
        defaults={
            "description": "使用 Locust 引擎对本平台核心的查询、大模型拉取接口进行 1000 QPS 级别的压力测试",
            "project_type": "HTTP",
            "status": "IN_PROGRESS",
            "owner": admin_user
        }
    )

    PerformanceCollection.objects.filter(project=project).delete()
    PerformanceTestSuite.objects.filter(project=project).delete()

    collection = PerformanceCollection.objects.create(
        project=project,
        name="核心 API 负载集合",
        description="包含最耗费性能的只读看板查询及大屏聚合接口"
    )

    requests_data = [
        {"name": "获取统一测试大屏指标 (Dashboard Aggregation)", "method": "GET", "url": "/api/reports/dashboard/summary/"},
        {"name": "拉取智能用例生成列表 (LLM Tasks List)", "method": "GET", "url": "/api/requirement_analysis/testcase-generation-tasks/"},
        {"name": "请求调度执行队列 (Scheduler Queue)", "method": "GET", "url": "/api/scheduler/jobs/"},
        {"name": "获取数据工厂表元数据 (DataFactory Async)", "method": "GET", "url": "/api/data_factory/table-metadata/"}
    ]

    req_objects = []
    for idx, r_data in enumerate(requests_data):
        req = PerformanceRequest.objects.create(
            collection=collection,
            name=r_data["name"],
            method=r_data["method"],
            url=r_data["url"],
            headers={"Authorization": "Bearer {{token}}", "Content-Type": "application/json"},
            created_by=admin_user,
            order=idx
        )
        req_objects.append(req)

    suite = PerformanceTestSuite.objects.create(
        name="[1000并发基准] 平台主要链路混合压测套件",
        description="基于 Locust 引擎模拟 1000 个真实坐席同时查看看板",
        project=project,
        environment=env,
        locust_settings={
            "users": 1000,
            "spawn_rate": 50,
            "run_time": "5m"
        },
        worker_count=4,
        created_by=admin_user
    )

    weights = [10, 3, 5, 2]
    for idx, req in enumerate(req_objects):
        PerformanceTestSuiteRequest.objects.create(
            test_suite=suite,
            request=req,
            weight=weights[idx],
            order=idx
        )

    execution = PerformanceTestExecution.objects.create(
        test_suite=suite,
        status="COMPLETED",
        start_time=now - timedelta(minutes=10),
        end_time=now - timedelta(minutes=5),
        executed_by=admin_user,
        total_requests=45230,
        passed_requests=45228,
        failed_requests=2,
        duration=300,
        rps=150.7,
        response_time_avg=23.4,
        response_time_min=8.2,
        response_time_max=1204.5,
        concurrency=1000,
        results={
            "error_rate": 0.004,
            "median_response_time": 18.6,
            "cpu_usage_avg": "45.2%",
            "memory_usage_avg": "2.4GB"
        }
    )

    # PerformanceTestHistory creates individual request traces!
    # I'll just write ~40 samples across requests to visualize individual spikes.
    histories = []
    for _ in range(40):
        req = random.choice(req_objects)
        is_error = random.random() < 0.05
        status_code = 500 if is_error else 200
        histories.append(PerformanceTestHistory(
            execution=execution,
            request=req,
            environment=env,
            request_data={"url": env.variables['base_url'] + req.url},
            response_data={"error": "Timeout"} if is_error else {"status": "success"},
            status_code=status_code,
            response_time=random.uniform(10.0, 450.0) if is_error else random.uniform(8.0, 35.0)
        ))
    
    PerformanceTestHistory.objects.bulk_create(histories)

    print("\n🎉 性能测试套件全链路闭环数据已成功生成！")

if __name__ == "__main__":
    setup_performance_tests()
