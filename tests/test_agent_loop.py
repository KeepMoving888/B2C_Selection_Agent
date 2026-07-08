# ============================================================
# tests/test_agent_loop.py — Agent Loop 完整测试套件
#
# 运行：pytest tests/ -v
# 覆盖：配置、DAG 调度、死循环检测、模型路由、降级链
# ============================================================

import asyncio
import pytest
from unittest.mock import MagicMock, patch

import sys
sys.path.insert(0, '.')

from harness.agent_loop import (
    AgentLoop, AgentLoopConfig, SubTask, TaskStatus, LoopPhase
)
from harness.model_router import ModelRouter


# ── Python 3.7 兼容：自定义 async mock ───────────────

def _async_return(value):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    f = loop.create_future()
    f.set_result(value)
    return f

class AsyncMagicMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)


# ── Fixtures ──────────────────────────────────────────

@pytest.fixture
def config():
    return AgentLoopConfig()

@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.call = MagicMock(return_value=_async_return('{"result": "ok"}'))
    return llm

@pytest.fixture
def mock_router():
    router = ModelRouter()
    return router

@pytest.fixture
def mock_agents():
    agent = MagicMock()
    agent.execute = MagicMock(return_value=_async_return({"result": "done", "tokens_used": 100}))
    return {"test_agent": agent, "test_agent2": agent}

@pytest.fixture
def mock_mcp():
    return {"amazon": MagicMock()}


# ── 配置测试 ──────────────────────────────────────────

class TestAgentLoopConfig:
    def test_defaults(self):
        c = AgentLoopConfig()
        assert c.max_total_steps == 15
        assert c.parallel_agents == 3
        assert c.loop_detection_threshold == 3
        assert c.agent_timeout_seconds == 120

    def test_custom_config(self):
        c = AgentLoopConfig(max_total_steps=20, parallel_agents=5)
        assert c.max_total_steps == 20
        assert c.parallel_agents == 5


# ── DAG 调度测试 ──────────────────────────────────────

class TestDAGScheduling:
    def test_find_ready_no_deps(self, config, mock_llm, mock_router,
                                 mock_agents, mock_mcp):
        """无依赖的子任务应该全部标记为 READY"""
        loop = AgentLoop(config, mock_agents, mock_mcp, mock_router, mock_llm)
        loop.subtasks = [
            SubTask(id="t1", agent="test_agent", action="test",
                    input_data={}, depends_on=[]),
            SubTask(id="t2", agent="test_agent2", action="test",
                    input_data={}, depends_on=[]),
        ]
        ready = loop._find_ready(set())
        assert len(ready) == 2
        assert all(st.status == TaskStatus.READY for st in ready)

    def test_find_ready_with_deps(self, config, mock_llm, mock_router,
                                   mock_agents, mock_mcp):
        """有未满足依赖的子任务不应标记为 READY"""
        loop = AgentLoop(config, mock_agents, mock_mcp, mock_router, mock_llm)
        loop.subtasks = [
            SubTask(id="t1", agent="test_agent", action="test",
                    input_data={}, depends_on=[]),
            SubTask(id="t2", agent="test_agent2", action="test",
                    input_data={}, depends_on=["t1", "t3"]),  # t3 未完成
        ]
        ready = loop._find_ready(set())
        assert len(ready) == 1
        assert ready[0].id == "t1"

    def test_find_ready_deps_satisfied(self, config, mock_llm, mock_router,
                                        mock_agents, mock_mcp):
        """依赖满足后应标记为 READY"""
        loop = AgentLoop(config, mock_agents, mock_mcp, mock_router, mock_llm)
        loop.subtasks = [
            SubTask(id="t1", agent="test_agent", action="test",
                    input_data={}, depends_on=[],
                    status=TaskStatus.COMPLETED),
            SubTask(id="t2", agent="test_agent2", action="test",
                    input_data={}, depends_on=["t1"]),
        ]
        ready = loop._find_ready({"t1"})  # t1 已完成
        assert len(ready) == 1
        assert ready[0].id == "t2"


# ── 模型路由测试 ──────────────────────────────────────

class TestModelRouter:
    def test_orchestrator_routes_to_premium(self):
        router = ModelRouter()
        assert router.route("orchestrator") == "v4-pro"

    def test_agent_routes(self):
        router = ModelRouter()
        assert router.route("market_research") == "qwen2.5-7b-orpo"
        assert router.route("supply_chain") == "v4-flash"
        assert router.route("compliance") == "v4-flash"
        assert router.route("trend_forecast") == "qwen2.5-7b-orpo"

    def test_calculator_routes_to_base(self):
        router = ModelRouter()
        assert router.route("profit_calculator") == "qwen2.5-7b-base"

    def test_fallback_chain(self):
        router = ModelRouter()
        router.mark_unhealthy("v4-pro")
        assert router.route("orchestrator") == "qwen2.5-7b-orpo"
        router.mark_unhealthy("v4-flash")
        assert router.route("supply_chain") == "qwen2.5-7b-orpo"

    def test_all_unhealthy_raises(self):
        router = ModelRouter()
        router.mark_unhealthy("v4-pro")
        router.mark_unhealthy("v4-flash")
        router.mark_unhealthy("qwen2.5-7b-orpo")
        router.mark_unhealthy("qwen2.5-7b-base")
        with pytest.raises(RuntimeError, match="All model tiers unavailable"):
            router.route("orchestrator")

    def test_route_history(self):
        router = ModelRouter()
        router.route("orchestrator")
        router.route("market_research")
        router.route("supply_chain")
        stats = router.get_stats()
        assert stats["total_requests"] == 3


# ── 集成测试（端到端 Demo）───────────────────────────

@pytest.mark.asyncio
async def test_demo_run():
    """端到端：完整选品分析流程"""
    from agents.orchestrator import OrchestratorAgent
    from agents.market_research import MarketResearchAgent
    from agents.supply_chain import SupplyChainAgent
    from agents.compliance import ComplianceAgent
    from agents.profit_calculator import ProfitCalculatorAgent
    from agents.trend_forecast import TrendForecastAgent

    async def _mock_llm_call(prompt, model="", tools=None):
        p = prompt.lower()
        if "task planner" in p or "decompose" in p:
            return (
                '[{"id":"m1","agent":"market_research","action":"analyze market",'
                '"input_data":{},"depends_on":[]},'
                '{"id":"s1","agent":"supply_chain","action":"find suppliers",'
                '"input_data":{},"depends_on":[]}]'
            )
        if "product selection report" in p or "executive_summary" in p:
            return (
                '{"executive_summary":"Promising","overall_score":78,'
                '"dimension_scores":{"market":32,"supply":22,"profit":16,"risk":8},'
                '"detailed_analysis":{},"risk_warnings":[],'
                '"action_recommendations":[],"data_sources":[]}'
            )
        return '{"result":"ok"}'

    llm = MagicMock()
    llm.call = _mock_llm_call

    router = ModelRouter()
    config = AgentLoopConfig()

    agents = {
        "orchestrator": OrchestratorAgent(llm, router),
        "market_research": MarketResearchAgent(llm, router),
        "supply_chain": SupplyChainAgent(llm, router),
        "compliance": ComplianceAgent(llm, router),
        "profit_calculator": ProfitCalculatorAgent(llm, router),
        "trend_forecast": TrendForecastAgent(llm, router),
    }

    loop = AgentLoop(config, agents, {}, router, llm)

    result = await loop.run(
        task="分析宠物咀嚼玩具在美国亚马逊的可行性",
        context={"category": "Pet Supplies", "market": "US"}
    )

    assert "result" in result or "_meta" in result


# ── 边界测试 ──────────────────────────────────────────

class TestEdgeCases:
    def test_empty_subtasks(self, config, mock_llm, mock_router,
                             mock_agents, mock_mcp):
        """空任务列表不应崩溃"""
        loop = AgentLoop(config, mock_agents, mock_mcp, mock_router, mock_llm)
        loop.context = MagicMock()
        loop.context.agent_success_rate = 0.0
        loop.subtasks = []
        aggregated = asyncio.run(loop._aggregate())
        assert aggregated["total_subtasks"] == 0

    def test_all_failed_subtasks(self, config, mock_llm, mock_router,
                                  mock_agents, mock_mcp):
        """全部失败的子任务应正确报告"""
        loop = AgentLoop(config, mock_agents, mock_mcp, mock_router, mock_llm)
        loop.context = MagicMock()
        loop.context.agent_success_rate = 0.0
        loop.subtasks = [
            SubTask(id="f1", agent="test_agent", action="test",
                    input_data={}, depends_on=[],
                    status=TaskStatus.FAILED, error="timeout"),
            SubTask(id="f2", agent="test_agent", action="test",
                    input_data={}, depends_on=[],
                    status=TaskStatus.FAILED, error="api error"),
        ]
        aggregated = asyncio.run(loop._aggregate())
        assert aggregated["total_subtasks"] == 2
        assert aggregated["failed"] == 2
        assert aggregated["agent_success_rate"] == 0.0
