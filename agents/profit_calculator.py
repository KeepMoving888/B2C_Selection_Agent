# ============================================================
# agents/profit_calculator.py — 利润测算 Agent
#
# 确定性 Rule-based 计算引擎。不依赖 LLM 推理，直接套用
# Amazon 真实费率表进行利润计算，避免大模型的计算幻觉。
# Mixed-Agent 架构：推理型任务用 LLM，计算型任务用规则引擎。
# ============================================================

from __future__ import annotations
import json
from typing import Any, Dict
from .base import BaseAgent
from harness.agent_loop import SubTask


class ProfitCalculatorAgent(BaseAgent):
    """
    利润测算 Agent — 确定性 Rule-based 计算。

    逻辑说明：利润计算是确定性数学公式，使用 LLM 推理反而
    引入数字计算错误的幻觉风险。本 Agent 直接从上游 Agent 获取
    采购价和售价数据，套用平台真实费率公式输出确定性结果。
    这是 Mixed-Agent 架构的体现：推理型任务用 LLM Agent，
    计算型任务用 Rule-based Agent。
    """

    def __init__(self, llm_client: Any, model_router: Any):
        super().__init__()
        self.llm = llm_client
        self.router = model_router

    # Amazon US Referral Fee by product category
    REFERRAL_FEES = {
        "pet_supplies": 0.15, "toys": 0.15,
        "home_kitchen": 0.15, "electronics": 0.08,
        "clothing": 0.17, "beauty": 0.15,
        "sports": 0.15, "default": 0.15,
    }

    # FBA pickup & delivery fee per unit by size tier
    FBA_FEES = {
        "small_standard": 3.22, "large_standard": 5.40,
        "small_oversize": 9.88, "default": 4.80,
    }

    async def execute(self, subtask: SubTask, mcp_registry: Dict,
                      llm: Any = None, model: str = "") -> Dict[str, Any]:
        """
        确定性计算流程：
        1. 从上游 Agent 提取成本数据
        2. 套用平台费率公式
        3. 多场景 ROI 计算
        4. 输出结构化利润表
        """
        input_data = subtask.input_data
        supply = input_data.get("supply_chain", {})
        market = input_data.get("market_research", {})

        unit_cost = float(supply.get("unit_cost",
                          input_data.get("unit_cost", 5.0)))
        shipping = float(supply.get("shipping_per_unit", 2.0))
        selling_price = float(market.get("recommended_price",
                              input_data.get("selling_price", 19.99)))

        category = input_data.get("category", "default")
        referral_rate = self.REFERRAL_FEES.get(category, 0.15)
        size_tier = input_data.get("size_tier", "default")
        fba_fee = self.FBA_FEES.get(size_tier, 4.80)

        cost_breakdown = {
            "product_cost": round(unit_cost, 2),
            "shipping_per_unit": round(shipping, 2),
            "fba_fee": round(fba_fee, 2),
            "referral_fee": round(selling_price * referral_rate, 2),
            "advertising_per_unit": round(selling_price * 0.08, 2),
            "return_allowance": round(selling_price * 0.03, 2),
            "misc_cost": 0.50,
        }

        total_cost = sum(cost_breakdown.values())
        gross_profit = selling_price - total_cost
        gross_margin = gross_profit / selling_price if selling_price > 0 else 0

        # 多场景 ROI（保守/中性/乐观）
        scenarios = {
            "conservative": {"sales": 100, "price": selling_price * 0.9},
            "neutral": {"sales": 300, "price": selling_price},
            "optimistic": {"sales": 600, "price": selling_price * 1.1},
        }

        roi = {}
        for name, params in scenarios.items():
            m_rev = params["sales"] * params["price"]
            m_cost = params["sales"] * total_cost
            m_profit = m_rev - m_cost
            investment = unit_cost * 500 + 2000
            payback = investment / m_profit if m_profit > 0 else None
            roi[name] = {
                "monthly_sales": params["sales"],
                "monthly_revenue": round(m_rev, 2),
                "monthly_profit": round(m_profit, 2),
                "roi_pct": round(m_profit / investment * 100, 1),
                "payback_months": round(payback, 1) if payback else None,
            }

        recommendation = ("RECOMMENDED" if gross_margin >= 0.2
                          else "MARGINAL" if gross_margin >= 0.1
                          else "NOT RECOMMENDED")

        return {
            "profit_analysis": {
                "selling_price": round(selling_price, 2),
                "total_cost_per_unit": round(total_cost, 2),
                "gross_profit_per_unit": round(gross_profit, 2),
                "gross_margin": f"{gross_margin:.1%}",
                "cost_breakdown": cost_breakdown,
                "roi_scenarios": roi,
                "breakeven_units": (
                    round(2000 / gross_profit) if gross_profit > 0 else None),
                "recommendation": recommendation,
            },
            "tokens_used": 0,
        }
