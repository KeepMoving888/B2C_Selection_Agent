# ============================================================
# demo.py — 完整选品系统 Demo（6 Agent + 4 MCP Server）
#
# 使用方法：python demo.py
# 使用离线 LLM 客户端与离线数据，无需任何外部 API 即可运行完整链路。
# ============================================================

import asyncio
import json
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 自动加载 .env 环境变量（如果存在）
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

from harness.agent_loop import AgentLoop, AgentLoopConfig
from harness.model_router import ModelRouter
from agents.orchestrator import OrchestratorAgent
from agents.market_research import MarketResearchAgent
from agents.supply_chain import SupplyChainAgent
from agents.compliance import ComplianceAgent
from agents.profit_calculator import ProfitCalculatorAgent
from agents.trend_forecast import TrendForecastAgent
from mcp_servers.amazon_server import AmazonMCPServer
from mcp_servers.supply_server import SupplyChainMCPServer
from mcp_servers.compliance_server import ComplianceMCPServer
from mcp_servers.social_server import SocialMediaMCPServer
from feishu.integration import FeishuIntegration, FeishuConfig


class MockLLMClient:
    """离线 LLM 客户端，用于本地开发、CI 测试与无 API 凭证场景。"""

    async def call(self, prompt: str, model: str = "",
                   tools: list = None) -> str:
        p = prompt.lower()

        # Orchestrator plan / verify / synthesize prompts come first
        if "task planner" in p or "decompose" in p:
            return json.dumps([
                {"id": "m1", "agent": "market_research",
                 "action": "Analyze Amazon market demand and competition",
                 "input_data": {}, "depends_on": []},
                {"id": "s1", "agent": "supply_chain",
                 "action": "Evaluate supplier options and shipping costs",
                 "input_data": {}, "depends_on": []},
                {"id": "c1", "agent": "compliance",
                 "action": "Check FDA/CE/IP regulations",
                 "input_data": {}, "depends_on": []},
                {"id": "t1", "agent": "trend_forecast",
                 "action": "Analyze Google Trends and social media trends",
                 "input_data": {}, "depends_on": []},
                {"id": "p1", "agent": "profit_calculator",
                 "action": "Calculate total cost and profit margin",
                 "input_data": {},
                 "depends_on": ["m1", "s1"]},
            ], ensure_ascii=False)

        if "market" in p:
            return json.dumps({"market_demand_score": 0.82, "summary": "Strong demand, 15% YoY growth"}, ensure_ascii=False)
        if "supply" in p:
            return json.dumps({"supplier_count": 12, "avg_moq": 500, "unit_cost_range": "$2.50-$5.00"}, ensure_ascii=False)
        if "compliance" in p:
            return json.dumps({"fda_status": "exempt", "ip_risk": "low", "overall_risk": "low"}, ensure_ascii=False)
        if "profit" in p:
            return json.dumps({"gross_margin": "33.7%", "net_margin": "18.5%", "breakeven_units": 320}, ensure_ascii=False)
        if "trend" in p:
            return json.dumps({"trend_direction": "rising", "lifecycle_stage": "growth", "buzz_score": 78}, ensure_ascii=False)

        # Fallback
        return json.dumps({"result": "ok"}, ensure_ascii=False)


def build_all_agents(llm: MockLLMClient, router: ModelRouter) -> dict:
    """注册全部 6 个 Agent"""
    return {
        "orchestrator": OrchestratorAgent(llm, router),
        "market_research": MarketResearchAgent(llm, router),
        "supply_chain": SupplyChainAgent(llm, router),
        "compliance": ComplianceAgent(llm, router),
        "profit_calculator": ProfitCalculatorAgent(llm, router),
        "trend_forecast": TrendForecastAgent(llm, router),
    }


def build_all_mcp_servers() -> dict:
    """注册全部 4 个 MCP Server"""
    return {
        "amazon": AmazonMCPServer(),
        "supply_chain": SupplyChainMCPServer(),
        "compliance": ComplianceMCPServer(),
        "social_media": SocialMediaMCPServer(),
    }


async def main():
    print("=" * 60)
    print("  跨境电商 Multi-Agent 智能选品系统")
    print("=" * 60)

    llm = MockLLMClient()
    router = ModelRouter()
    config = AgentLoopConfig()

    agents = build_all_agents(llm, router)
    mcp_registry = build_all_mcp_servers()
    print(f"  Agents: {len(agents)} | MCP Servers: {len(mcp_registry)}")

    loop = AgentLoop(config=config, agents=agents, mcp_registry=mcp_registry,
                     model_router=router, llm_client=llm)

    print("\n> Task: 分析宠物咀嚼玩具在美国亚马逊的可行性\n")
    start = time.time()
    report = await loop.run(
        task="分析宠物咀嚼玩具（dog chew toys）在美国亚马逊平台的市场可行性",
        context={"category": "Pet Supplies > Dog Toys", "market": "US",
                 "platform": "amazon", "budget": "$5,000-$10,000"},
    )
    elapsed = time.time() - start

    meta = report.pop("_meta", {})
    print(f"  耗时: {elapsed:.1f}s | Steps: {meta.get('total_steps', '?')}")
    print(f"  Tokens: {meta.get('total_tokens_used', '?')}")
    print(f"  Agent成功率: {meta.get('agent_success_rate', '?')}")
    stats = router.get_stats()
    if stats:
        print(f"  路由分布: Premium={stats.get('premium_ratio','?')} Local={stats.get('local_ratio','?')} Flash={stats.get('flash_ratio','?')}")
    print("\n  Done.")


if __name__ == "__main__":
    asyncio.run(main())
