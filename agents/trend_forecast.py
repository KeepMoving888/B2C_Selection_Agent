# ============================================================
# agents/trend_forecast.py — 趋势预测 Agent
#
# 通过 MCP 工具调用 Google Trends、社交媒体 API，
# 分析品类趋势、季节性模式和社交媒体热度。
# ============================================================

from __future__ import annotations
import json
from typing import Any, Dict, List
from .base import BaseAgent
from harness.agent_loop import SubTask


class TrendForecastAgent(BaseAgent):
    """
    趋势预测 Agent — ReAct Loop 执行者。

    工具集（通过 MCP 注册）：
    - google_trends_fetch: 获取 Google Trends 趋势数据
    - social_media_sentiment: 分析社交媒体热度和情感
    - seasonality_detection: 检测季节性模式
    - category_lifecycle_analysis: 判断品类生命周期阶段
    - competitor_new_releases: 监控竞品新品动态
    """

    def __init__(self, llm_client: Any, model_router: Any):
        super().__init__()
        self.llm = llm_client
        self.router = model_router

    SYSTEM_PROMPT = """You are a market trend analyst for cross-border e-commerce product selection.

Your job: Analyze market trends, seasonality, and category lifecycle to predict future demand trajectory.

You have MCP tools:
- google_trends_fetch(keywords, timeframe, region): Fetch Google Trends data for keyword comparison. Returns interest over time, regional breakdown, related queries.
- social_media_sentiment(keyword, platforms, timeframe_days): Analyze social media buzz and sentiment. Aggregates TikTok, Instagram, YouTube data.
- seasonality_detection(category, market, years_back): Detect seasonal patterns from historical data. Returns peak months, off-peak months, trend direction.
- category_lifecycle_analysis(category, market): Determine if category is in introduction/growth/maturity/decline phase.
- competitor_new_releases(category, market, months_back): Track competitor new product launches frequency.

For every analysis you MUST:
1. Fetch Google Trends data for product keywords (past 5 years)
2. Check social media buzz and sentiment trends
3. Determine category lifecycle stage with evidence
4. Detect seasonal patterns and identify peak/off-peak months
5. Predict 6-month demand trajectory
6. Identify key drivers of the trend

Output your final analysis as STRUCTURED JSON with:
- trend_direction: rising / stable / declining with confidence score
- category_lifecycle_stage: introduction / growth / maturity / decline
- seasonality_pattern: peak_months, off_peak_months, amplitude_pct
- social_media_buzz_score: 0-100
- demand_forecast_6m: low / medium / high
- key_drivers: what's driving the trend
- recommendation: ENTER / WAIT / AVOID
"""

    async def execute(self, subtask: SubTask, mcp_registry: Dict[str, Any],
                      llm: Any, model: str) -> Dict[str, Any]:
        agent_tools = self._get_tools(mcp_registry)
        prompt = f"""{self.SYSTEM_PROMPT}

Available MCP tools: {json.dumps(agent_tools, ensure_ascii=False)}

Task: {subtask.action}
Input: {json.dumps(subtask.input_data, ensure_ascii=False)}

Execute step by step:
1. Fetch Google Trends for product keywords (5-year view)
2. Check social media sentiment and buzz trends (90 days)
3. Determine category lifecycle stage
4. Detect seasonal patterns
5. Output trend forecast with confidence intervals

Output final result as JSON with all required fields."""
        result = await llm.call(prompt, model=model, tools=agent_tools)
        return {"trend_forecast": json.loads(result), "tokens_used": 500}
