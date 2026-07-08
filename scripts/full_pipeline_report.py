# ============================================================
# scripts/full_pipeline_report.py — Multi-Agent 全链路选品报告
#
# 用途：
#   1. 随机/指定行业，串联 6 个 Agent + 4 个 MCP Server
#   2. 各 Agent 在执行阶段真实调用 MCP tools 获取模拟数据
#   3. 输出具备商业落地价值的结构化选品报告
#
# 运行：
#   python scripts/full_pipeline_report.py
#   python scripts/full_pipeline_report.py --industry 3c
#   python scripts/full_pipeline_report.py --industry pet --keyword "cat toy"
# ============================================================

import argparse
import asyncio
import json
import os
import random
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from harness.agent_loop import AgentLoop, AgentLoopConfig, SubTask
from harness.model_router import ModelRouter
from agents.market_research import MarketResearchAgent
from agents.supply_chain import SupplyChainAgent
from agents.compliance import ComplianceAgent
from agents.profit_calculator import ProfitCalculatorAgent
from agents.trend_forecast import TrendForecastAgent
from mcp_servers.amazon_server import AmazonMCPServer
from mcp_servers.supply_server import SupplyChainMCPServer
from mcp_servers.compliance_server import ComplianceMCPServer
from mcp_servers.social_server import SocialMediaMCPServer


OUTPUT_DIR = PROJECT_ROOT / "output"


def market_price_hint(category: str) -> float:
    """用于关税申报价值估算的品类均价提示。"""
    return {
        "pet_supplies": 5.0, "electronics": 25.0, "home_kitchen": 20.0,
        "sports": 25.0, "beauty": 8.0, "baby": 6.0,
    }.get(category, 5.0)


# 行业池：覆盖深圳跨境电商主流行业
INDUSTRY_KEYWORDS = {
    "pet": ["cat toy", "dog chew toys", "automatic cat toy", "cat scratcher"],
    "3c": ["wireless earbuds", "bluetooth speaker", "power bank", "led strip lights"],
    "home": ["portable blender", "led desk lamp", "kitchen organizer"],
    "sports": ["yoga mat", "resistance bands", "massage gun"],
    "beauty": ["makeup brush set", "facial cleansing brush"],
    "baby": ["baby silicone plate", "baby bibs"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Multi-Agent 全链路选品报告（真实感模拟数据闭环）"
    )
    parser.add_argument(
        "--industry",
        choices=list(INDUSTRY_KEYWORDS.keys()) + ["random"],
        default="random",
        help="测试行业（默认随机）",
    )
    parser.add_argument(
        "--keyword",
        default=None,
        help="指定关键词（覆盖行业随机选择）",
    )
    parser.add_argument(
        "--source",
        choices=["rainforest", "pa_api", "mock"],
        default="rainforest",
        help="Amazon 数据源（默认 rainforest，无 key 自动回退 mock）",
    )
    return parser.parse_args()


def pick_keyword(args: argparse.Namespace) -> tuple[str, str]:
    """返回 (industry, keyword)"""
    if args.keyword:
        industry = args.industry if args.industry != "random" else "custom"
        return industry, args.keyword

    industry = args.industry
    if industry == "random":
        industry = random.choice(list(INDUSTRY_KEYWORDS.keys()))
    keyword = random.choice(INDUSTRY_KEYWORDS[industry])
    return industry, keyword


def map_industry_to_category(industry: str) -> str:
    mapping = {
        "pet": "pet_supplies", "3c": "electronics", "home": "home_kitchen",
        "sports": "sports", "beauty": "beauty", "baby": "baby", "custom": "default",
    }
    return mapping.get(industry, "default")


class EnhancedMockLLMClient:
    """
    增强型 Mock LLM：
    - understand / plan / synthesize 返回结构化数据
    - 不覆盖 Worker Agent 已拿到的 MCP 真实感数据
    """

    def __init__(self, keyword: str, category: str, industry: str):
        self.keyword = keyword
        self.category = category
        self.industry = industry

    async def call(self, prompt: str, model: str = "", tools: list = None) -> str:
        p = prompt.lower()

        # 意图理解
        if "extract structured intent" in p:
            return json.dumps({
                "product_category": self.category,
                "target_market": "US",
                "target_platform": "amazon",
                "seller_level": "small_to_medium",
                "budget_range": "$5,000-$15,000",
                "special_requirements": ["realistic mock data", "profitability first month"],
            }, ensure_ascii=False)

        # 任务规划
        if "task planner" in p or "decompose" in p:
            return json.dumps([
                {"id": "m1", "agent": "market_research",
                 "action": f"Analyze Amazon market demand and competition for '{self.keyword}'",
                 "input_data": {"keyword": self.keyword, "category": self.category},
                 "depends_on": []},
                {"id": "s1", "agent": "supply_chain",
                 "action": f"Evaluate 1688/Alibaba suppliers and shipping for '{self.keyword}'",
                 "input_data": {"keyword": self.keyword, "category": self.category},
                 "depends_on": []},
                {"id": "c1", "agent": "compliance",
                 "action": f"Check FDA/CE/IP and Amazon restrictions for '{self.keyword}'",
                 "input_data": {"keyword": self.keyword, "category": self.category},
                 "depends_on": []},
                {"id": "t1", "agent": "trend_forecast",
                 "action": f"Analyze Google Trends and seasonality for '{self.keyword}'",
                 "input_data": {"keyword": self.keyword, "category": self.category},
                 "depends_on": []},
                {"id": "p1", "agent": "profit_calculator",
                 "action": "Calculate total cost, profit margin and ROI scenarios",
                 "input_data": {"category": self.category},
                 "depends_on": ["m1", "s1"]},
            ], ensure_ascii=False)

        # 最终报告生成（优先判断，避免 aggregated JSON 中的 verify 字段触发误匹配）
        if prompt.strip().lower().startswith("generate a product selection report"):
            return json.dumps(self._build_final_report(prompt), ensure_ascii=False)

        # 质量验证
        if prompt.strip().lower().startswith("you are a quality assurance specialist"):
            return json.dumps({
                "completeness_score": 1.0,
                "consistency_score": 0.9,
                "overall_pass": True,
                "issues": ["Data is simulated; verify with real APIs before production launch"],
            }, ensure_ascii=False)

        # Worker Agent 的 LLM 辅助总结（已在各 Agent 中直接使用 MCP 数据，这里兜底）
        return json.dumps({"summary": "analysis based on MCP tool outputs", "confidence": "medium"})

    def _extract_aggregated(self, prompt: str) -> Dict:
        """从 synthesize prompt 中解析 aggregated JSON。"""
        marker = "Analysis: "
        idx = prompt.find(marker)
        if idx < 0:
            return {}
        text = prompt[idx + len(marker):]
        # 去除 trailing instructions
        for tail in ["\nOutput JSON with:", "\nOutput JSON"]:
            tidx = text.find(tail)
            if tidx >= 0:
                text = text[:tidx]
        try:
            return json.loads(text)
        except Exception as e:
            print(f"[DEBUG] Failed to parse aggregated JSON: {e}")
            print(f"[DEBUG] Text preview: {text[:500]}...")
            return {}

    def _build_final_report(self, prompt: str) -> Dict:
        agg = self._extract_aggregated(prompt)
        results = agg.get("results_by_agent", {})

        market = results.get("market_research", [{}])[0].get("market_analysis", {})
        supply = results.get("supply_chain", [{}])[0].get("supply_analysis", {})
        compliance = results.get("compliance", [{}])[0].get("compliance_analysis", {})
        trend = results.get("trend_forecast", [{}])[0].get("trend_analysis", {})
        profit = results.get("profit_calculator", [{}])[0].get("profit_analysis", {})

        margin_str = profit.get("gross_margin", "0%")
        try:
            margin = float(margin_str.rstrip("%")) / 100
        except Exception:
            margin = 0

        market_score = min(market.get("market_demand_score", 0.5) * 40, 40)
        supply_score = 25 if supply.get("supplier_count", 0) > 0 else 10
        profit_score = max(0, min(margin * 80, 20))
        risk_score = 10 if compliance.get("overall_risk", "low") in ("low", "low_to_medium") else 3
        trend_score = 5 if trend.get("trend_direction") == "rising" else 3

        total = round(market_score + supply_score + profit_score + risk_score + trend_score, 1)

        verdict = "谨慎进入" if total < 55 else "可以考虑" if total < 75 else "推荐进入"

        return {
            "executive_summary": {
                "product_keyword": self.keyword,
                "industry": self.industry,
                "target_market": "US",
                "target_platform": "amazon",
                "overall_score": total,
                "max_score": 100,
                "verdict": verdict,
                "key_findings": [
                    f"市场需求评分：{market.get('market_demand_score', 0):.2f}/1.0",
                    f"竞品平均售价：${market.get('avg_price', 0):.2f}",
                    f"供应商最低 MOQ：{supply.get('min_moq', 'N/A')} pcs",
                    f"预估毛利率：{margin_str}",
                    f"合规风险：{compliance.get('overall_risk', 'unknown')}",
                    f"趋势方向：{trend.get('trend_direction', 'unknown')}",
                ],
            },
            "dimension_scores": {
                "market": round(market_score, 1),
                "supply": supply_score,
                "profit": round(profit_score, 1),
                "risk": risk_score,
                "trend": trend_score,
            },
            "detailed_analysis": {
                "market": market,
                "supply": supply,
                "compliance": compliance,
                "trend": trend,
                "profit": profit,
            },
            "risk_warnings": [
                "本报告基于示例数据生成，正式投产前需用真实 API 复核",
                "关税、FBA 费率和平台佣金可能变动，建议定期重新测算",
                "专利检索为示例结果，上架前务必做 FTO（自由实施）分析",
            ],
            "action_recommendations": [
                f"针对用户核心痛点优化产品：{', '.join(market.get('top_pain_points', [])[:2]) or '持续调研'}",
                f"联系 {supply.get('supplier_count', 0)} 家供应商获取样品并核价",
                "确认合规认证要求并完成 CPC/FCC/FDA 等必要检测",
                "小批量（300-500 pcs）测款，监控 BSR、广告 ACoS 和退货率",
            ],
            "data_sources": {
                "market": "Amazon (Rainforest/Mock) + Google Trends",
                "supply": "1688/Alibaba (Mock)",
                "compliance": "FDA/CPSC/USPTO/Amazon Restricted Categories (Mock)",
                "trend": "Google Trends + Seasonality (Mock)",
            },
        }


class EnhancedMarketResearchAgent(MarketResearchAgent):
    """市场调研 Agent 增强版：执行时真实调用 Amazon + Trends MCP tools。"""

    async def execute(self, subtask: SubTask, mcp_registry: Dict,
                      llm: Any, model: str) -> Dict:
        keyword = subtask.input_data.get("keyword", "cat toy")
        category = subtask.input_data.get("category", "pet_supplies")

        amazon = mcp_registry["amazon"]
        social = mcp_registry["social_media"]

        # 1. Amazon 产品搜索
        search_resp = await amazon.call_tool(
            "amazon_product_search",
            {"keyword": keyword, "market": "com", "limit": 5, "source": "mock"},
        )
        search_result = search_resp.get("result", search_resp)
        products = search_result.get("results", [])

        # 2. 评论分析（Top 3 产品）
        review_insights = []
        for p in products[:3]:
            review_resp = await amazon.call_tool(
                "amazon_review_analysis",
                {
                    "asin": p.get("asin", ""),
                    "market": "com",
                    "max_reviews": 50,
                    "source": "mock",
                    "product_title": p.get("title", ""),
                    "category_hint": category,
                },
            )
            review_insights.append(review_resp.get("result", review_resp))

        # 3. Google Trends
        trend_resp = await social.call_tool(
            "google_trends_fetch",
            {"keywords": [keyword], "region": "US", "timeframe": "today 12-m"},
        )
        trends = trend_resp.get("result", trend_resp)

        valid_prices = [p["price"] for p in products if p.get("price")]
        avg_price = round(sum(valid_prices) / len(valid_prices), 2) if valid_prices else 19.99
        valid_reviews = [p.get("review_count", 0) for p in products if p.get("review_count", 0) > 0]
        avg_reviews = round(sum(valid_reviews) / len(valid_reviews), 0) if valid_reviews else 0
        min_bsr = min([p["bsr"] for p in products if p.get("bsr")], default=None)

        # 聚合痛点
        all_pain_points = []
        for r in review_insights:
            for pt in r.get("top_pain_points", []):
                all_pain_points.append(pt.get("issue", ""))

        demand_score = 0.7
        if trends.get("trend_direction") == "rising":
            demand_score += 0.1
        if min_bsr and min_bsr < 1000:
            demand_score += 0.1
        if avg_reviews < 3000:
            demand_score += 0.05
        demand_score = min(demand_score, 0.95)

        return {
            "market_analysis": {
                "keyword": keyword,
                "category": category,
                "market_demand_score": round(demand_score, 2),
                "avg_price": avg_price,
                "avg_reviews": int(avg_reviews),
                "min_bsr": min_bsr,
                "top_products_count": len(products),
                "top_pain_points": list(dict.fromkeys(all_pain_points))[:5],
                "trend_direction": trends.get("trend_direction", "unknown"),
                "trend_confidence": trends.get("confidence", 0),
                "data_quality": search_result.get("data_quality", "unknown"),
                "competitor_landscape_summary": (
                    f"'{keyword}' 在 Amazon 上找到 {len(products)} 个去重竞品，"
                    f"平均售价 ${avg_price}，平均评论 {int(avg_reviews)}。"
                    f"{'竞争较激烈' if avg_reviews > 5000 else '竞争相对温和'}。"
                ),
                "keyword_opportunity_analysis": (
                    "关键词机会：" + (
                        "需求呈上升趋势，且存在明显未被满足的痛点，适合切入。"
                        if trends.get("trend_direction") == "rising"
                        else "需求稳定，建议通过差异化功能切入。"
                    )
                ),
                "seasonal_relevance": trends.get("interest_over_time", {}).get(keyword, {}).get("peak_months", "all_year"),
                "risk_factors": ["Review-driven market", "Potential brand dominance"] if avg_reviews > 10000 else ["Low entry barrier"],
                "data_quality_notes": search_result.get("data_quality", ""),
            },
            "tokens_used": 0,
        }


class EnhancedSupplyChainAgent(SupplyChainAgent):
    """供应链 Agent 增强版：执行时真实调用 1688/Alibaba Mock MCP tools。"""

    async def execute(self, subtask: SubTask, mcp_registry: Dict,
                      llm: Any, model: str) -> Dict:
        keyword = subtask.input_data.get("keyword", "cat toy")
        supply = mcp_registry["supply_chain"]

        supplier_resp = await supply.call_tool(
            "supplier_search",
            {"keyword": keyword, "platform": "both", "limit": 10},
        )
        supplier_data = supplier_resp.get("result", supplier_resp)

        suppliers = supplier_data.get("suppliers", [])
        base_avg = supplier_data.get("price_range", {}).get("avg", 2.75)
        min_moq = min([s.get("moq", 9999) for s in suppliers], default=300)

        # 根据品类调整更真实的采购均价
        keyword = subtask.input_data.get("keyword", "")
        text = keyword.lower()
        cost_multipliers = {
            "wireless earbuds": 4.5, "bluetooth speaker": 5.5, "power bank": 3.5,
            "led strip": 1.5, "massage gun": 6.0, "yoga mat": 2.0,
            "resistance bands": 1.2, "makeup brush": 1.0, "baby silicone plate": 1.3,
            "portable blender": 3.0, "led desk lamp": 2.5, "kitchen organizer": 1.8,
        }
        multiplier = 1.0
        for kw, m in cost_multipliers.items():
            if kw in text:
                multiplier = m
                break
        avg_price = round(base_avg * multiplier, 2)

        # 根据品类估算重量（kg）
        category = subtask.input_data.get("category", "default")
        weight_map = {
            "pet_supplies": 0.25, "electronics": 0.35, "home_kitchen": 0.6,
            "sports": 0.8, "beauty": 0.2, "baby": 0.3,
        }
        weight = weight_map.get(category, 0.4)

        shipping_resp = await supply.call_tool(
            "shipping_cost_estimate",
            {"weight_kg": weight, "quantity": min_moq, "method": "all"},
        )
        shipping = shipping_resp.get("result", shipping_resp)

        best_method = shipping.get("recommendation", "sea_freight")
        best_estimate = shipping.get("estimates", {}).get(best_method, {})
        shipping_per_unit = best_estimate.get("cost_per_unit", 2.0)

        return {
            "supply_analysis": {
                "keyword": keyword,
                "supplier_count": len(suppliers),
                "avg_unit_cost_usd": avg_price,
                "min_moq": min_moq,
                "top_suppliers": [
                    {
                        "name": s.get("name", ""),
                        "location": s.get("location", ""),
                        "moq": s.get("moq", 0),
                        "unit_price_usd": s.get("unit_price_usd", 0),
                        "certifications": s.get("certifications", []),
                        "rating": s.get("rating", 0),
                    }
                    for s in suppliers[:3]
                ],
                "recommended_shipping": best_method,
                "shipping_per_unit": shipping_per_unit,
                "shipping_estimates": shipping.get("estimates", {}),
                "lead_time_days_range": "12-20 days",
                "data_quality": supplier_data.get("data_quality", "unknown"),
            },
            "unit_cost": avg_price,
            "shipping_per_unit": shipping_per_unit,
            "tokens_used": 0,
        }


class EnhancedComplianceAgent(ComplianceAgent):
    """合规 Agent 增强版：执行时真实调用 FDA/USPTO/Amazon 限制 MCP tools。"""

    async def execute(self, subtask: SubTask, mcp_registry: Dict,
                      llm: Any, model: str) -> Dict:
        keyword = subtask.input_data.get("keyword", "cat toy")
        category = subtask.input_data.get("category", "pet_supplies")

        compliance = mcp_registry["compliance"]

        fda_resp = await compliance.call_tool(
            "fda_classification",
            {"product_type": keyword, "intended_use": "consumer product", "target_market": "US"},
        )
        fda = fda_resp.get("result", fda_resp)

        restriction_resp = await compliance.call_tool(
            "amazon_restricted_categories",
            {"category": category, "marketplace": "US"},
        )
        restrictions = restriction_resp.get("result", restriction_resp)

        patent_resp = await compliance.call_tool(
            "patent_search",
            {"keywords": keyword.split()[:3]},
        )
        patent = patent_resp.get("result", patent_resp)

        # 根据品类选择更真实的 HS code
        hs_code_map = {
            "pet_supplies": "9503.00", "electronics": "8518.30",
            "home_kitchen": "8509.40", "sports": "9506.91",
            "beauty": "9603.30", "baby": "3924.90", "default": "9503.00",
        }
        hs_code = hs_code_map.get(category, "9503.00")

        tariff_resp = await compliance.call_tool(
            "import_tariff_check",
            {"hs_code": hs_code, "origin_country": "CN", "destination_country": "US",
             "declared_value_usd": market_price_hint(category)},
        )
        tariff = tariff_resp.get("result", tariff_resp)

        risk_factors = []
        if restrictions.get("gated"):
            risk_factors.append(f"Amazon 类目 '{category}' 需要审批")
        if patent.get("overall_ip_risk") in ("medium", "high"):
            risk_factors.append("存在中等专利风险，建议做 FTO")
        if fda.get("requires_premarket_approval"):
            risk_factors.append("需要 FDA 预审批")

        overall_risk = patent.get("overall_ip_risk", "low")
        if restrictions.get("risk_level") == "medium":
            overall_risk = "medium"
        if risk_factors:
            overall_risk = "medium"

        return {
            "compliance_analysis": {
                "keyword": keyword,
                "category": category,
                "fda_classification": fda,
                "amazon_restrictions": restrictions,
                "ip_risk": patent,
                "import_tariff": tariff,
                "risk_factors": risk_factors or ["未发现重大合规风险（基于模拟数据）"],
                "overall_risk": overall_risk,
                "data_quality": "MOCK — production uses FDA/USPTO/Amazon SP-API",
            },
            "tokens_used": 0,
        }


class EnhancedTrendForecastAgent(TrendForecastAgent):
    """趋势预测 Agent 增强版：执行时真实调用 Trends + Seasonality MCP tools。"""

    async def execute(self, subtask: SubTask, mcp_registry: Dict,
                      llm: Any, model: str) -> Dict:
        keyword = subtask.input_data.get("keyword", "cat toy")
        category = subtask.input_data.get("category", "pet_supplies")

        social = mcp_registry["social_media"]

        trend_resp = await social.call_tool(
            "google_trends_fetch",
            {"keywords": [keyword], "region": "US", "timeframe": "today 12-m"},
        )
        trends = trend_resp.get("result", trend_resp)

        season_resp = await social.call_tool(
            "seasonality_detection",
            {"category": category, "market": "US", "years_back": 5},
        )
        season = season_resp.get("result", season_resp)

        return {
            "trend_analysis": {
                "keyword": keyword,
                "category": category,
                "trend_direction": trends.get("trend_direction", "unknown"),
                "confidence": trends.get("confidence", 0),
                "lifecycle_stage": season.get("lifecycle_stage", "growth"),
                "peak_months": season.get("peak_months", []),
                "buzz_score": trends.get("interest_over_time", {}).get(keyword, {}).get("current_value", 50),
                "rising_queries": trends.get("related_queries_rising", []),
                "data_quality": trends.get("data_quality", "unknown"),
            },
            "tokens_used": 0,
        }


async def main():
    args = parse_args()
    industry, keyword = pick_keyword(args)
    category = map_industry_to_category(industry)

    print("=" * 70)
    print("  Multi-Agent 全链路选品报告")
    print(f"  随机行业：{industry.upper()} | 关键词：{keyword}")
    print("=" * 70)

    llm = EnhancedMockLLMClient(keyword=keyword, category=category, industry=industry)
    router = ModelRouter()
    config = AgentLoopConfig()

    agents = {
        "market_research": EnhancedMarketResearchAgent(llm, router),
        "supply_chain": EnhancedSupplyChainAgent(llm, router),
        "compliance": EnhancedComplianceAgent(llm, router),
        "profit_calculator": ProfitCalculatorAgent(llm, router),
        "trend_forecast": EnhancedTrendForecastAgent(llm, router),
    }

    mcp_registry = {
        "amazon": AmazonMCPServer(
            rainforest_api_key=os.getenv("RAINFOREST_API_KEY"),
            default_source=args.source,
        ),
        "supply_chain": SupplyChainMCPServer(),
        "compliance": ComplianceMCPServer(),
        "social_media": SocialMediaMCPServer(),
    }

    loop = AgentLoop(config=config, agents=agents, mcp_registry=mcp_registry,
                     model_router=router, llm_client=llm)

    try:
        report = await loop.run(
            task=f"分析 {keyword} 在美国亚马逊平台的选品可行性",
            context={"category": category, "market": "US", "platform": "amazon",
                     "budget": "$5,000-$15,000"},
        )

        # 利润测算精修：AgentLoop 默认不会把依赖结果注入 input_data，
        # 因此用 detailed_analysis 中的 market/supply 数据重新精算。
        market_result = report.get("detailed_analysis", {}).get("market", {})
        supply_result = report.get("detailed_analysis", {}).get("supply", {})

        if market_result and supply_result:
            selling_price = market_result.get("avg_price", 19.99)
            unit_cost = supply_result.get("avg_unit_cost_usd", 5.0)
            shipping = supply_result.get("shipping_per_unit", 2.0)
            size_tier = "small_standard" if category in ("pet_supplies", "baby", "beauty") else "default"

            profit_task = SubTask(
                id="p1", agent="profit_calculator",
                action="Recalculate profit with real MCP data",
                input_data={
                    "category": category,
                    "selling_price": selling_price,
                    "unit_cost": unit_cost,
                    "shipping_per_unit": shipping,
                    "size_tier": size_tier,
                },
            )
            profit_agent = ProfitCalculatorAgent(llm, router)
            profit_result = await profit_agent.execute(profit_task, mcp_registry, llm, "")
            report["detailed_analysis"]["profit"] = profit_result.get("profit_analysis", {})

            # 用真实利润数据刷新评分与摘要
            profit_analysis = report["detailed_analysis"]["profit"]
            margin_str = profit_analysis.get("gross_margin", "0%")
            try:
                margin = float(margin_str.rstrip("%")) / 100
            except Exception:
                margin = 0
            scores = report.get("dimension_scores", {})
            scores["profit"] = round(max(0, min(margin * 80, 20)), 1)
            total = round(scores.get("market", 0) + scores.get("supply", 0) +
                          scores.get("profit", 0) + scores.get("risk", 0) +
                          scores.get("trend", 0), 1)
            report["executive_summary"]["overall_score"] = total
            report["executive_summary"]["verdict"] = (
                "谨慎进入" if total < 55 else "可以考虑" if total < 75 else "推荐进入"
            )
            findings = report["executive_summary"].get("key_findings", [])
            if len(findings) >= 6:
                findings[0] = f"市场需求评分：{market_result.get('market_demand_score', 0):.2f}/1.0"
                findings[1] = f"竞品平均售价：${selling_price:.2f}"
                findings[2] = f"供应商最低 MOQ：{supply_result.get('min_moq', 'N/A')} pcs"
                findings[3] = f"预估毛利率：{margin_str}"
                findings[4] = f"合规风险：{report['detailed_analysis'].get('compliance', {}).get('overall_risk', 'unknown')}"
                findings[5] = f"趋势方向：{report['detailed_analysis'].get('trend', {}).get('trend_direction', 'unknown')}"

        meta = report.pop("_meta", {})

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_kw = re.sub(r"[^\w\-]+", "_", keyword).strip("_").lower()
        output_path = OUTPUT_DIR / f"full_pipeline_report_{safe_kw}_{timestamp}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        summary = report.get("executive_summary", {})
        scores = report.get("dimension_scores", {})

        print("\n" + "=" * 70)
        print("  报告摘要")
        print("=" * 70)
        print(f"  关键词：{summary.get('product_keyword', keyword)}")
        print(f"  综合评分：{summary.get('overall_score', 0)}/{summary.get('max_score', 100)}")
        print(f"  结论：{summary.get('verdict', 'unknown')}")
        print(f"  维度得分：市场 {scores.get('market', 0)} | 供应链 {scores.get('supply', 0)} | "
              f"利润 {scores.get('profit', 0)} | 风险 {scores.get('risk', 0)} | 趋势 {scores.get('trend', 0)}")
        print(f"  执行耗时：{meta.get('total_time_seconds', 0):.1f}s")
        print(f"  Agent 成功率：{meta.get('agent_success_rate', '?')}")
        print(f"\n✅ 完整报告已保存：{output_path}")

    finally:
        await mcp_registry["amazon"].close()


if __name__ == "__main__":
    asyncio.run(main())
