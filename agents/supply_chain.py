# ============================================================
# agents/supply_chain.py — 供应链评估 Agent
#
# 通过 MCP 工具调用 1688/阿里国际站 API，评估供应商、
# 物流成本、MOQ 和交期。
# ============================================================

from __future__ import annotations
import json
from typing import Any, Dict, List
from .base import BaseAgent
from harness.agent_loop import SubTask


class SupplyChainAgent(BaseAgent):
    """
    供应链评估 Agent — ReAct Loop 执行者。

    工具集（通过 MCP 注册）：
    - supplier_search: 搜索 1688 / 阿里国际站供应商
    - shipping_cost_estimate: 估算海运/空运/快递/FBA 物流成本
    - moq_price_analysis: 分析 MOQ 和阶梯定价
    - supplier_verification: 核验供应商资质（营业执照/出口能力/认证）
    - lead_time_estimate: 估算生产+运输总交期
    """

    def __init__(self, llm_client: Any, model_router: Any):
        super().__init__()
        self.llm = llm_client
        self.router = model_router

    SYSTEM_PROMPT = """You are a supply chain specialist for cross-border e-commerce.

Your job: Evaluate the supply chain feasibility of sourcing a product from China for sale on a target platform (Amazon/eBay/Shopify).

You have MCP tools:
- supplier_search(keyword, min_order, max_price): Search suppliers on 1688/Alibaba. Returns supplier list with price, MOQ, location, transaction history.
- shipping_cost_estimate(weight_kg, volume_cbm, origin, destination, method): Estimate shipping costs for sea/air/express/FBA warehouse.
- moq_price_analysis(product_spec, quantity_range): Analyze MOQ requirements and tiered pricing.
- supplier_verification(supplier_id): Verify supplier qualifications (business license, export capability, certifications like ISO, BSCI).
- lead_time_estimate(product_type, quantity, shipping_method): Estimate production + shipping total lead time.

For every analysis you MUST:
1. Search for at least 5 potential suppliers with comparison
2. Calculate total landed cost per unit for each shipping method
3. Assess supply risk (supplier concentration, seasonal constraints, material availability)
4. Check if small seller can meet MOQ requirements
5. Recommend top 3 suppliers with clear justification

Output your final analysis as STRUCTURED JSON with:
- supplier_comparison: array of suppliers with price/moq/lead_time/rating
- landed_cost_per_unit: cost breakdown by shipping method
- recommended_suppliers: top 3 with justification
- supply_risk_assessment: low/medium/high with reasons
- moq_feasibility: can small seller meet MOQ?
- total_lead_time_days: best case estimate
"""

    async def execute(self, subtask: SubTask, mcp_registry: Dict[str, Any],
                      llm: Any, model: str) -> Dict[str, Any]:
        agent_tools = self._get_tools(mcp_registry)
        prompt = f"""{self.SYSTEM_PROMPT}

Available MCP tools: {json.dumps(agent_tools, ensure_ascii=False)}

Task: {subtask.action}
Input: {json.dumps(subtask.input_data, ensure_ascii=False)}

Execute step by step:
1. Search suppliers matching product specs on 1688/Alibaba
2. For each supplier, check: unit price, MOQ, lead time, certifications
3. Calculate shipping options (sea/air/express/FBA) and landed costs
4. Assess supply chain risks
5. Output structured recommendation

Output final result as JSON with all required fields."""
        result = await llm.call(prompt, model=model, tools=agent_tools)
        return {"supply_chain_analysis": json.loads(result), "tokens_used": 500}
