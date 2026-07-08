# ============================================================
# monitoring/metrics.py —— Prometheus 指标采集层
#
# 设计：
#   - 优先使用 prometheus_client 暴露 /metrics
#   - 未安装时自动降级为内存统计（Noop），保证测试/开发环境可运行
#   - 通过 MetricsCollector 统一收口，避免散落在各模块
# ============================================================

from __future__ import annotations

import time
from typing import Dict, Optional


try:
    from prometheus_client import (
        Counter, Gauge, Histogram, start_http_server, CollectorRegistry,
    )
    _PROMETHEUS_AVAILABLE = True
except ImportError:
    _PROMETHEUS_AVAILABLE = False


class _NoopMetric:
    """兼容 Counter/Gauge/Histogram 的 no-op 实现。"""
    def inc(self, amount=1):
        pass

    def set(self, value):
        pass

    def observe(self, value):
        pass

    def labels(self, *args, **kwargs):
        return self


class MetricsCollector:
    """
    统一指标收集器。

    当前覆盖：
      - Agent 运行成功率 / 延迟 / Replan 次数
      - 模型路由分布
      - LLM 调用延迟与状态码
      - RAG 检索延迟与命中数
    """

    def __init__(self, registry: Optional["CollectorRegistry"] = None):
        self._enabled = _PROMETHEUS_AVAILABLE
        self._memory: Dict[str, float] = {}

        if self._enabled:
            self._registry = registry or CollectorRegistry()
            self._agent_runs = Counter(
                "agent_runs_total", "Total agent loop runs",
                ["status"], registry=self._registry,
            )
            self._agent_duration = Histogram(
                "agent_run_duration_seconds", "Agent loop duration",
                ["phase"], registry=self._registry,
            )
            self._model_route = Counter(
                "model_route_total", "Model routing decisions",
                ["model", "tier"], registry=self._registry,
            )
            self._llm_requests = Counter(
                "llm_requests_total", "LLM requests",
                ["model", "status"], registry=self._registry,
            )
            self._llm_duration = Histogram(
                "llm_request_duration_seconds", "LLM request duration",
                ["model"], registry=self._registry,
            )
            self._rag_queries = Counter(
                "rag_queries_total", "RAG retrieval queries",
                ["status"], registry=self._registry,
            )
            self._rag_latency = Histogram(
                "rag_latency_seconds", "RAG retrieval latency",
                registry=self._registry,
            )
            self._rag_hits = Gauge(
                "rag_hits", "RAG hits for last query",
                registry=self._registry,
            )
        else:
            self._agent_runs = _NoopMetric()
            self._agent_duration = _NoopMetric()
            self._model_route = _NoopMetric()
            self._llm_requests = _NoopMetric()
            self._llm_duration = _NoopMetric()
            self._rag_queries = _NoopMetric()
            self._rag_latency = _NoopMetric()
            self._rag_hits = _NoopMetric()

    # ── Agent Loop 指标 ───────────────────────────────

    def record_task_completed(self, success: bool, meta: Dict):
        status = "success" if success else "failure"
        self._agent_runs.labels(status=status).inc()
        if meta:
            self._memory["last_total_time"] = meta.get("total_time_seconds", 0)
            self._memory["last_success_rate"] = meta.get("agent_success_rate", 0)

    def record_phase_timing(self, phase: str, duration_seconds: float):
        self._agent_duration.labels(phase=phase).observe(duration_seconds)

    def record_replan(self):
        self._memory["replan_count"] = self._memory.get("replan_count", 0) + 1

    # ── 模型路由指标 ──────────────────────────────────

    def record_model_route(self, model: str, tier: str):
        self._model_route.labels(model=model, tier=tier).inc()

    # ── LLM 调用指标 ──────────────────────────────────

    def record_llm_request(self, model: str, duration_seconds: float, success: bool):
        status = "success" if success else "failure"
        self._llm_requests.labels(model=model, status=status).inc()
        self._llm_duration.labels(model=model).observe(duration_seconds)

    def time_llm_request(self, model: str):
        """上下文管理器，用于统计单次 LLM 调用耗时。"""
        return _TimedRequest(self, model)

    # ── RAG 检索指标 ──────────────────────────────────

    def record_rag_query(self, duration_seconds: float, hits: int, success: bool = True):
        status = "success" if success else "failure"
        self._rag_queries.labels(status=status).inc()
        self._rag_latency.observe(duration_seconds)
        self._rag_hits.set(hits)

    # ── 服务入口 ──────────────────────────────────────

    def start_server(self, port: int = 9091, addr: str = "0.0.0.0"):
        """启动 /metrics HTTP 服务。"""
        if not self._enabled:
            print("[WARN] prometheus_client 未安装，无法启动 /metrics 服务")
            return
        start_http_server(port, addr=addr, registry=self._registry)
        print(f"[Metrics] Prometheus /metrics listening on http://{addr}:{port}/metrics")

    def is_enabled(self) -> bool:
        """prometheus_client 是否可用。"""
        return self._enabled

    def get_memory_stats(self) -> Dict:
        """获取内存中的最新统计（Noop 模式或调试用）。"""
        return self._memory.copy()


class _TimedRequest:
    def __init__(self, collector: MetricsCollector, model: str):
        self.collector = collector
        self.model = model
        self.start = None

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start
        self.collector.record_llm_request(self.model, duration, exc_type is None)
