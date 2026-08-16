from django.apps import AppConfig


class EvalPodConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.eval_pod'
    verbose_name = 'Agent 测评 / LLM 测试 评测舱'

    def ready(self):
        # E7：幂等播种平台级 Benchmark 目录（SWE-bench/GAIA/τ-bench 等）
        try:
            from .benchmarks import ensure_benchmark_catalog
            ensure_benchmark_catalog()
        except Exception:  # noqa: BLE001
            # 防止目录未迁移完成前阻塞 app 加载（迁移后自愈）
            pass
