#!/usr/bin/env python3
"""
deploy/api_gateway.py
=====================
选品项目 API Gateway + 模型路由。

路由策略：
  - vllm_awq (本地 vLLM AWQ INT4)：默认 70%，处理标准选品分析请求
  - vllm_fp16 (本地 vLLM FP16)：fallback 20%，当 AWQ 质量不满足阈值时切换
  - deepseek_v4 (DeepSeek API)：复杂多步推理 10%，命中高复杂度规则直接路由

环境变量：
  - VLLM_AWQ_URL：本地 AWQ 服务地址，默认 http://127.0.0.1:8002
  - VLLM_FP16_URL：本地 FP16 服务地址，默认 http://127.0.0.1:8003
  - DEEPSEEK_API_KEY：DeepSeek API key（未配置时 fallback 到 AWQ）
  - DEEPSEEK_API_URL：DeepSeek API base，默认 https://api.deepseek.com/v1
  - GATEWAY_PORT：网关端口，默认 8080
"""

import json
import os
import random
import re
import time
from dataclasses import dataclass
from pathlib import Path

import requests
from flask import Flask, Response, jsonify, request

# Prometheus 指标导出
try:
    from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    print("[WARN] prometheus_client not installed, /metrics endpoint disabled")

app = Flask(__name__)

VLLM_AWQ_URL = os.getenv("VLLM_AWQ_URL", "http://127.0.0.1:8002")
VLLM_FP16_URL = os.getenv("VLLM_FP16_URL", "http://127.0.0.1:8003")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1")
GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", "8080"))

# 路由决策日志
LOG_DIR = Path("output/gateway_logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
ROUTE_LOG = LOG_DIR / "route_decisions.jsonl"

# Prometheus 指标定义
if PROMETHEUS_AVAILABLE:
    REQUESTS_TOTAL = Counter(
        "gateway_requests_total",
        "Total gateway requests",
        ["backend", "status"],
    )
    REQUEST_DURATION = Histogram(
        "gateway_request_duration_seconds",
        "Gateway request duration",
        ["backend"],
        buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0],
    )
    BACKEND_AVAILABILITY = Gauge(
        "gateway_backend_availability",
        "Backend availability (1=up, 0=down)",
        ["backend"],
    )
    ACTIVE_REQUESTS = Gauge(
        "gateway_active_requests",
        "Number of requests currently being processed",
    )


def _proxies():
    return {"http": None, "https": None}


@dataclass
class RouteDecision:
    backend: str
    reason: str
    weight: float
    target_url: str


class GrayscaleRouter:
    """灰度路由器：按配置权重 + 规则做后端选择。"""

    DEFAULT_WEIGHTS = {
        "vllm_awq": 0.70,
        "vllm_fp16": 0.20,
        "deepseek_v4": 0.10,
    }

    COMPLEXITY_KEYWORDS = [
        "多步推理", "深度分析", "对比多个类目", "预测未来趋势",
        "跨平台", "多维度", "综合评估", "复杂", "竞品全面对比",
        "供应链深度", "财务模型", "ROI", "投资回报",
    ]

    def __init__(self, weights: dict | None = None):
        self.weights = weights or self.DEFAULT_WEIGHTS
        self._validate_weights()

    def _validate_weights(self):
        total = sum(self.weights.values())
        assert abs(total - 1.0) < 1e-6, f"Weights must sum to 1.0, got {total}"

    def _complexity_score(self, prompt: str) -> int:
        """简单启发式复杂度评分。"""
        score = 0
        text = prompt.lower()
        # 长度权重
        score += min(len(prompt) // 100, 20)
        # 关键词权重
        for kw in self.COMPLEXITY_KEYWORDS:
            if kw.lower() in text:
                score += 15
        # 多问题权重
        score += len(re.findall(r"[？\?]", prompt)) * 5
        return min(score, 100)

    def _has_deepseek(self) -> bool:
        return bool(DEEPSEEK_API_KEY)

    def _has_fp16(self) -> bool:
        try:
            r = requests.get(f"{VLLM_FP16_URL}/v1/models", timeout=2, proxies=_proxies())
            return r.status_code == 200
        except Exception:
            return False

    def route(self, prompt: str, fallback: bool = False) -> RouteDecision:
        complexity = self._complexity_score(prompt)

        # 规则优先：高复杂度直接走 DeepSeek
        if complexity >= 80 and self._has_deepseek():
            return RouteDecision("deepseek_v4", f"complexity={complexity}", self.weights["deepseek_v4"])

        # fallback 场景
        if fallback and self._has_fp16():
            return RouteDecision("vllm_fp16", "fallback_flag", self.weights["vllm_fp16"])

        # 按权重随机选择（DeepSeek 未配置时其权重归并到 AWQ）
        effective_weights = dict(self.weights)
        if not self._has_deepseek():
            effective_weights["vllm_awq"] += effective_weights.pop("deepseek_v4", 0.0)
        if not self._has_fp16():
            effective_weights["vllm_awq"] += effective_weights.pop("vllm_fp16", 0.0)

        r = random.random()
        cumulative = 0.0
        for backend, weight in effective_weights.items():
            cumulative += weight
            if r <= cumulative:
                target = {
                    "vllm_awq": VLLM_AWQ_URL,
                    "vllm_fp16": VLLM_FP16_URL,
                    "deepseek_v4": DEEPSEEK_API_URL,
                }[backend]
                reason = "weight_random"
                if backend == "deepseek_v4":
                    reason += f", complexity={complexity}"
                return RouteDecision(backend, reason, weight, target)

        return RouteDecision("vllm_awq", "default", effective_weights.get("vllm_awq", 1.0), VLLM_AWQ_URL)


router = GrayscaleRouter()


def _log_decision(prompt: str, decision: RouteDecision, latency_ms: float, status: str):
    record = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "backend": decision.backend,
        "reason": decision.reason,
        "weight": decision.weight,
        "target_url": decision.target_url,
        "latency_ms": round(latency_ms, 2),
        "status": status,
        "prompt_preview": prompt[:80],
    }
    with open(ROUTE_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _forward_to_vllm(target_url: str, payload: dict) -> tuple:
    """转发到本地 vLLM 服务。"""
    model = payload.get("model", "")
    if target_url == VLLM_AWQ_URL and not model:
        payload["model"] = "/home/b2cuser/models/qwen2.5-7b-ecommerce-awq-v3"
    resp = requests.post(
        f"{target_url}/v1/chat/completions",
        json=payload,
        timeout=300,
        proxies=_proxies(),
    )
    return resp.json(), resp.status_code


def _forward_to_deepseek(payload: dict) -> tuple:
    """转发到 DeepSeek API。"""
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    resp = requests.post(
        f"{DEEPSEEK_API_URL}/chat/completions",
        json=payload,
        headers=headers,
        timeout=300,
        proxies=_proxies(),
    )
    return resp.json(), resp.status_code


@app.route("/v1/chat/completions", methods=["POST"])
def chat_completions():
    start = time.time()
    if PROMETHEUS_AVAILABLE:
        ACTIVE_REQUESTS.inc()

    payload = request.get_json(force=True)
    prompt = ""
    if payload.get("messages"):
        prompt = payload["messages"][-1].get("content", "")

    fallback = payload.pop("_fallback", False)
    decision = router.route(prompt, fallback=fallback)
    status_label = "error"

    try:
        if decision.backend == "deepseek_v4":
            data, status = _forward_to_deepseek(payload)
        else:
            data, status = _forward_to_vllm(decision.target_url, payload)
        latency_ms = (time.time() - start) * 1000
        status_label = "success" if status == 200 else f"error_{status}"
        _log_decision(prompt, decision, latency_ms, status_label)
        return jsonify(data), status
    except Exception as e:
        latency_ms = (time.time() - start) * 1000
        _log_decision(prompt, decision, latency_ms, f"exception: {str(e)}")
        return jsonify({"error": str(e)}), 502
    finally:
        duration = time.time() - start
        if PROMETHEUS_AVAILABLE:
            REQUEST_DURATION.labels(backend=decision.backend).observe(duration)
            REQUESTS_TOTAL.labels(backend=decision.backend, status=status_label).inc()
            ACTIVE_REQUESTS.dec()


@app.route("/health", methods=["GET"])
def health():
    backends = {
        "vllm_awq": False,
        "vllm_fp16": False,
        "deepseek_v4": bool(DEEPSEEK_API_KEY),
    }
    try:
        r = requests.get(f"{VLLM_AWQ_URL}/v1/models", timeout=2, proxies=_proxies())
        backends["vllm_awq"] = r.status_code == 200
    except Exception:
        pass
    try:
        r = requests.get(f"{VLLM_FP16_URL}/v1/models", timeout=2, proxies=_proxies())
        backends["vllm_fp16"] = r.status_code == 200
    except Exception:
        pass

    if PROMETHEUS_AVAILABLE:
        for name, available in backends.items():
            BACKEND_AVAILABILITY.labels(backend=name).set(1 if available else 0)

    return jsonify({"status": "ok", "backends": backends})


@app.route("/metrics", methods=["GET"])
def metrics():
    """Prometheus 指标端点。"""
    if not PROMETHEUS_AVAILABLE:
        return jsonify({"error": "prometheus_client not installed"}), 503
    # 刷新后端健康状态
    health()
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.route("/metrics/route_stats", methods=["GET"])
def route_stats():
    """返回最近 1 小时的路由统计。"""
    if not ROUTE_LOG.exists():
        return jsonify({})
    stats = {"total": 0, "by_backend": {}, "avg_latency_ms": 0.0}
    latencies = []
    cutoff = time.time() - 3600
    with open(ROUTE_LOG, "r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            ts = time.mktime(time.strptime(rec["timestamp"], "%Y-%m-%d %H:%M:%S"))
            if ts < cutoff:
                continue
            stats["total"] += 1
            stats["by_backend"][rec["backend"]] = stats["by_backend"].get(rec["backend"], 0) + 1
            latencies.append(rec["latency_ms"])
    if latencies:
        stats["avg_latency_ms"] = round(sum(latencies) / len(latencies), 2)
    return jsonify(stats)


if __name__ == "__main__":
    print(f"[Gateway] Starting on port {GATEWAY_PORT}")
    print(f"[Gateway] AWQ backend: {VLLM_AWQ_URL}")
    print(f"[Gateway] FP16 backend: {VLLM_FP16_URL} (available={router._has_fp16()})")
    print(f"[Gateway] DeepSeek backend: {DEEPSEEK_API_URL} (available={router._has_deepseek()})")
    app.run(host="0.0.0.0", port=GATEWAY_PORT, threaded=True)
