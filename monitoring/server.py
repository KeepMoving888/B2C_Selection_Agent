# ============================================================
# monitoring/server.py —— 监控服务启动入口
# ============================================================

from monitoring.metrics import MetricsCollector


def run_metrics_server(port: int = 9091, addr: str = "0.0.0.0") -> MetricsCollector:
    """启动 Prometheus /metrics 服务并返回采集器实例。"""
    collector = MetricsCollector()
    collector.start_server(port, addr)
    return collector
