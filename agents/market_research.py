# ============================================================
# agents/market_research.py — 市场调研 Agent
#
# 通过 MCP 工具调用 Amazon/Google Trends/社交媒体 API，
# 分析产品在市场中的需求、竞争和趋势。
# ============================================================

from __future__ import annotations

import json
from typing import Any, Dict, List

from harness.agent_loop import SubTask
from .base import BaseAgent


class MarketResearchAgent(BaseAgent):
    """
    市场调研 Agent — ReAct Loop 执行者。

    工具集（通过 MCP 注册）：
    - amazon_best_sellers_rank: 获取 Amazon 类目 Best Sellers
    - amazon_product_search: 搜索产品并获取详情
    - google_trends_query: 查询 Google Trends 关键词趋势
    - keyword_volume_estimate: 估算关键词月搜索量
    - competitor_listing_analyzer: 竞品 listing 深度分析
    - seasonal_trend_analyzer: 季节性趋势分析

    ReAct Loop 适合本 Agent 的使用场景：Market Agent 的任务粒度
    已经细化到单维度分析（如"分析 Top 10 竞品定价策略"），
    不需要更复杂的 Plan-and-Execute。这是分层架构的体现：
    Orchestrator 负责全局规划，Worker Agent 负责局部执行。
    """

    SYSTEM_PROMPT = """You are a market research specialist for cross-border e-commerce.

Your job: Analyze the market potential of a product on a specific platform and market.

You have access to MCP tools:
- amazon_best_sellers_rank(category): Get top products in a category
- amazon_product_search(keyword, market): Search products with details
- google_trends_query(keyword, region, timeframe): Get trend data
- keyword_volume_estimate(keyword, market): Estimate monthly search volume
- competitor_listing_analyzer(asin_list): Deep competitor analysis
- seasonal_trend_analyzer(category, market): Seasonal pattern analysis

For every analysis, you MUST:
1. State which tool you're calling and why
2. Interpret the result in business terms
3. Assign a market_demand_score (0-1) with clear reasoning
4. Flag any data quality issues

Output your final analysis as structured JSON.
"""

    def __init__(self, llm_client: Any, model_router: Any):
        super().__init__()
        self.llm = llm_client
        self.router = model_router

    async def execute(
        self,
        subtask: SubTask,
        mcp_registry: Dict[str, Any],
        llm: Any,
        model: str,
    ) -> Dict[str, Any]:
        agent_tools = self._get_tools(mcp_registry)

        prompt = f"""{self.SYSTEM_PROMPT}

Available MCP tools: {json.dumps(agent_tools, ensure_ascii=False)}

Task: {subtask.action}
Input parameters: {json.dumps(subtask.input_data, ensure_ascii=False)}

Think step by step:
1. Which tools do I need? In what order?
2. What data will each tool provide?
3. How do I synthesize the results into a market assessment?

Execute the analysis using the available tools.
Output final result as JSON with:
- market_demand_score (0-1)
- competitor_landscape_summary
- keyword_opportunity_analysis
- seasonal_relevance
- risk_factors
- data_quality_notes
"""
        response = await llm.call(prompt, model=model, tools=agent_tools)
        return {"market_analysis": json.loads(response), "tokens_used": 600}
