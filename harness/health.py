# ============================================================
# harness/health.py — 健康检查 + Prometheus 指标
#
# 生产环境必备：Kubernetes liveness/readiness probe + 指标暴露
# ============================================================

import time
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Callable


# ── Prometheus 指标注册表 ──────────────────────────────

class MetricsRegistry:
    """简易 Prometheus 指标注册表（生产环境可换 prometheus_client）"""

    def __init__(self):
        self._counters: Dict[str, int] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, list] = {}
        self._lock = threading.Lock()

    def counter_inc(self, name: str, value: int = 1, labels: Dict[str, str] = None):
        with self._lock:
            key = self._metric_key(name, labels)
            self._counters[key] = self._counters.get(key, 0) + value

    def gauge_set(self, name: str, value: float, labels: Dict[str, str] = None):
        with self._lock:
            key = self._metric_key(name, labels)
            self._gauges[key] = value

    def histogram_observe(self, name: str, value: float, labels: Dict[str, str] = None):
        with self._lock:
            key = self._metric_key(name, labels)
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(value)

    def _metric_key(self, name: str, labels: Dict[str, str] = None) -> str:
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f'{name}{{{label_str}}}'

    def render_prometheus(self) -> str:
        """渲染 Prometheus 格式"""
        lines = []
        lines.append("# HELP agent_task_total Total number of agent tasks")
        lines.append("# TYPE agent_task_total counter")
        for key, val in self._counters.items():
            lines.append(f"agent_{key} {val}")

        lines.append("# HELP agent_gauge Agent gauge metrics")
        lines.append("# TYPE agent_gauge gauge")
        for key, val in self._gauges.items():
            lines.append(f"agent_{key} {val:.4f}")

        lines.append("# HELP agent_duration_seconds Agent task duration")
        lines.append("# TYPE agent_duration_seconds histogram")
        for key, vals in self._histograms.items():
            for v in vals[-100:]:  # 最近 100 个
                lines.append(f"agent_{key}_bucket{{le=\"+Inf\"}} {v:.4f}")

        return "\n".join(lines) + "\n"


# 全局指标注册表
metrics = MetricsRegistry()


# ── 健康检查 ───────────────────────────────────────────

class HealthStatus:
    """系统健康状态"""
    def __init__(self):
        self.start_time = time.time()
        self.last_task_time: float = 0
        self.active_tasks: int = 0
        self.total_tasks: int = 0
        self.failed_tasks: int = 0
        self.gpu_available: bool = False
        self.vllm_healthy: bool = False
        self.deepseek_api_healthy: bool = False
        self.mcp_servers_healthy: Dict[str, bool] = {}

    def to_dict(self) -> Dict:
        uptime = time.time() - self.start_time
        return {
            "status": "healthy" if self._is_healthy() else "degraded",
            "uptime_seconds": int(uptime),
            "uptime_human": f"{uptime/3600:.1f}h",
            "active_tasks": self.active_tasks,
            "total_tasks_completed": self.total_tasks,
            "task_success_rate": (
                f"{(1 - self.failed_tasks/max(self.total_tasks,1)):.1%}"
            ),
            "gpu_available": self.gpu_available,
            "vllm_healthy": self.vllm_healthy,
            "deepseek_api_healthy": self.deepseek_api_healthy,
            "mcp_servers": {k: "up" if v else "down"
                           for k, v in self.mcp_servers_healthy.items()},
            "version": "2.0.0",
        }

    def _is_healthy(self) -> bool:
        return self.gpu_available and (
            self.vllm_healthy or self.deepseek_api_healthy
        )


health = HealthStatus()


# ── HTTP Handler ───────────────────────────────────────

class HealthHandler(BaseHTTPRequestHandler):
    """合并 /health 和 /metrics 的 HTTP handler"""

    def do_GET(self):
        if self.path == "/health":
            self._respond_json(health.to_dict())
        elif self.path == "/health/live":
            self._respond_json({"status": "alive"}, 200)
        elif self.path == "/health/ready":
            ready = health._is_healthy()
            self._respond_json(
                {"status": "ready" if ready else "not_ready"},
                200 if ready else 503,
            )
        elif self.path == "/metrics":
            self._respond_text(metrics.render_prometheus())
        else:
            self.send_response(404)
            self.end_headers()

    def _respond_json(self, data: Dict, code: int = 200):
        body = json.dumps(data, ensure_ascii=False, indent=2)
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def _respond_text(self, text: str, code: int = 200):
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # 抑制 HTTP 日志噪音


def start_health_server(port: int = 8080):
    """启动健康检查 + 指标 HTTP 服务（后台线程）"""
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
