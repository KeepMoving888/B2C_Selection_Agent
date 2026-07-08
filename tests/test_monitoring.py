# ============================================================
# tests/test_monitoring.py — 监控体系集成测试
# ============================================================

import asyncio
import sys
import time
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, '.')

from harness.agent_loop import AgentLoop, AgentLoopConfig
from harness.model_router import ModelRouter
from llm.client import MultiProviderLLMClient, LLMConfig
from monitoring.metrics import MetricsCollector


class _FakeMetric:
    """用于验证 metrics 是否被正确记录的内存指标替代"""

    def __init__(self):
        self.calls = []

    def labels(self, *args, **kwargs):
        self.calls.append(("labels", args, kwargs))
        return self

    def inc(self, amount=1):
        self.calls.append(("inc", amount))

    def observe(self, value):
        self.calls.append(("observe", value))

    def set(self, value):
        self.calls.append(("set", value))


class _FakeMetricsCollector:
    """最小化 MetricsCollector 替代，记录所有调用"""

    def __init__(self):
        self.routes = []
        self.llm_requests = []
        self.phase_timings = []
        self.task_completions = []
        self.replans = 0

    def record_model_route(self, model: str, tier: str):
        self.routes.append({"model": model, "tier": tier})

    def record_llm_request(self, model: str, duration_seconds: float, success: bool):
        self.llm_requests.append({
            "model": model,
            "duration_seconds": duration_seconds,
            "success": success,
        })

    def record_phase_timing(self, phase: str, duration_seconds: float):
        self.phase_timings.append({"phase": phase, "duration_seconds": duration_seconds})

    def record_task_completed(self, success: bool, meta: dict):
        self.task_completions.append({"success": success, "meta": meta})

    def record_replan(self):
        self.replans += 1


def test_metrics_collector_noop_without_prometheus():
    """未安装 prometheus_client 时，MetricsCollector 应降级为 Noop 不抛异常"""
    collector = MetricsCollector()
    collector.record_model_route("v4-pro", "premium")
    collector.record_llm_request("v4-pro", 0.1, True)
    collector.record_phase_timing("plan", 0.2)
    collector.record_task_completed(True, {"total_time_seconds": 1.0})
    collector.record_replan()
    collector.record_rag_query(0.05, 2, True)
    # 不应抛异常；内存统计记录最后一次任务信息
    stats = collector.get_memory_stats()
    assert stats.get("last_total_time") == 1.0
    assert stats.get("replan_count") == 1


def test_model_router_records_routes():
    """ModelRouter 应把路由决策上报给 MetricsCollector"""
    metrics = _FakeMetricsCollector()
    router = ModelRouter(metrics_collector=metrics)
    router.route("orchestrator")
    router.route("market_research")
    router.route("supply_chain")

    assert len(metrics.routes) == 3
    assert metrics.routes[0]["model"] == "v4-pro"
    assert metrics.routes[0]["tier"] == "premium"
    assert metrics.routes[1]["model"] == "qwen2.5-7b-orpo"
    assert metrics.routes[1]["tier"] == "local"


def test_llm_client_records_success_and_failure():
    """MultiProviderLLMClient 应记录 LLM 调用耗时与成功/失败状态"""
    metrics = _FakeMetricsCollector()
    client = MultiProviderLLMClient(
        config=LLMConfig(deepseek_api_key="test-key", timeout_seconds=5),
        metrics_collector=metrics,
    )

    # mock _call_once 返回成功
    async def _mock_call_once(*args, **kwargs):
        return "ok"
    client._call_once = _mock_call_once

    asyncio.run(client.call("hi", model="v4-pro"))
    assert len(metrics.llm_requests) == 1
    assert metrics.llm_requests[0]["model"] == "v4-pro"
    assert metrics.llm_requests[0]["success"] is True

    # mock _call_once 抛异常
    async def _mock_raise(*args, **kwargs):
        raise Exception("boom")
    client._call_once = _mock_raise
    client._health = {"deepseek": True, "vllm_orpo": True, "vllm_base": True}

    with pytest.raises(Exception):
        asyncio.run(client.call("hi", model="v4-pro"))
    # 链上有 3 个模型，每个都失败
    assert len(metrics.llm_requests) == 4
    for req in metrics.llm_requests[1:]:
        assert req["success"] is False


def test_agent_loop_records_phase_and_completion():
    """AgentLoop 应记录阶段耗时与任务完成状态"""
    metrics = _FakeMetricsCollector()

    async def _mock_llm(prompt, model="", tools=None):
        p = prompt.lower()
        if "extract structured intent" in p:
            return '{"product_category":"pet","target_market":"US"}'
        if "task planner" in p or "decompose" in p:
            return '[{"id":"m1","agent":"test_agent","action":"a","input_data":{},"depends_on":[]}]'
        if "product selection report" in p or "executive_summary" in p:
            return '{"executive_summary":"ok","overall_score":70,"dimension_scores":{"market":30,"supply":20,"profit":15,"risk":5},"detailed_analysis":{},"risk_warnings":[],"action_recommendations":[],"data_sources":[]}'
        return '{"result":"ok"}'

    llm = MagicMock()
    llm.call = _mock_llm

    router = ModelRouter(metrics_collector=metrics)
    agent = MagicMock()
    agent.execute = MagicMock(return_value=_async_future({"result": "done", "tokens_used": 10}))

    loop = AgentLoop(
        config=AgentLoopConfig(),
        agents={"test_agent": agent},
        mcp_registry={},
        model_router=router,
        llm_client=llm,
        metrics_collector=metrics,
    )

    result = asyncio.run(loop.run(
        task="分析宠物玩具在美国的市场",
        context={"category": "Pet Supplies", "market": "US"},
    ))

    assert "_meta" in result
    assert len(metrics.task_completions) == 1
    assert metrics.task_completions[0]["success"] is True
    # 至少记录 understand/plan/execute/aggregate/verify/synthesize 几个阶段
    phases = {t["phase"] for t in metrics.phase_timings}
    assert "understand" in phases
    assert "plan" in phases
    assert "synthesize" in phases


def test_agent_loop_records_failure():
    """AgentLoop 执行异常时应记录失败"""
    metrics = _FakeMetricsCollector()

    async def _mock_llm(prompt, model="", tools=None):
        raise Exception("llm failed")

    llm = MagicMock()
    llm.call = _mock_llm
    router = ModelRouter(metrics_collector=metrics)

    # Python 3.7 下 Semaphore 需要当前事件循环
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    loop = AgentLoop(
        config=AgentLoopConfig(),
        agents={},
        mcp_registry={},
        model_router=router,
        llm_client=llm,
        metrics_collector=metrics,
    )

    with pytest.raises(Exception):
        asyncio.run(loop.run("test", {}))

    assert len(metrics.task_completions) == 1
    assert metrics.task_completions[0]["success"] is False


def _async_future(value):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    f = loop.create_future()
    f.set_result(value)
    return f
