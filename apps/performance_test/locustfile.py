"""Locust 性能测试配置（apps/performance_test/locustfile.py）。

WS4 门禁要求：
- 每个请求带超时（默认 30s），避免压测时无限挂起；
- 对响应体体积设上限（默认 5MB），超限记录告警但不让 worker 崩溃。
"""
import logging

from locust import HttpUser, task, between, events

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30                     # 秒（连接 + 读取）
MAX_RESPONSE_BYTES = 5 * 1024 * 1024    # 5 MB


class ApiTestUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # 为所有请求设置默认超时（HttpSession 支持 timeout 参数）
        self.client.timeout = REQUEST_TIMEOUT

    @task(3)
    def health(self):
        self._safe_request("get", "/api/v1/health")

    @task(2)
    def login(self):
        self._safe_request(
            "post", "/api/v1/mock/login",
            json={"username": "autotest", "password": "v2_agent"},
        )

    @task(1)
    def permissions(self):
        self._safe_request("get", "/api/v1/engine/permissions")

    def _safe_request(self, method, path, **kw):
        kw.setdefault("timeout", REQUEST_TIMEOUT)
        resp = self.client.request(method, path, **kw)
        size = len(resp.content)
        if size > MAX_RESPONSE_BYTES:
            logger.warning(
                "响应体 %d 字节超过上限 %d，已记录：%s %s",
                size, MAX_RESPONSE_BYTES, method.upper(), path,
            )
        return resp


@events.request.add_listener
def _on_request(request_type, name, response_time, response_length, exception, **kw):
    if exception is not None:
        logger.warning("Locust 请求失败 [%s %s]: %s", request_type, name, exception)
