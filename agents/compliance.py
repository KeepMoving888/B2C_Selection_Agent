# ============================================================
# agents/compliance.py — 合规审查 Agent
#
# 通过 MCP 工具调用 FDA/USPTO/Amazon 等数据源，
# 评估产品的法规合规性和知识产权风险。
# ============================================================

from __future__ import annotations
import json
from typing import Any, Dict, List
from .base import BaseAgent
from harness.agent_loop import SubTask


class ComplianceAgent(BaseAgent):
    """
    合规审查 Agent — ReAct Loop 执行者。

    工具集（通过 MCP 注册）：
    - fda_classification: 确定 FDA 产品分类和监管路径
    - patent_search: 检索 USPTO 和 Google Patents 中的现有专利
    - trademark_check: 检查商标可用性
    - amazon_restricted_categories: 检查 Amazon 类目限制和审批要求
    - import_tariff_check: 估算进口关税和税费
    - labeling_requirements: 列出产品标签和警告要求
    - ce_marking_check: 检查 CE/UKCA 标志要求
    """

    def __init__(self, llm_client: Any, model_router: Any):
        super().__init__()
        self.llm = llm_client
        self.router = model_router

    SYSTEM_PROMPT = """You are a compliance and regulatory specialist for cross-border e-commerce.

Your job: Assess the regulatory and IP compliance of a product for sale in a target market.

You have MCP tools:
- fda_classification(product_type, intended_use, target_market): Determine FDA product classification and requirements.
- patent_search(keywords, assignee): Search USPTO and Google Patents for existing patents. Returns patent numbers, titles, risk assessment.
- trademark_check(brand_name, class_code): Check trademark availability.
- amazon_restricted_categories(category, marketplace): Check Amazon category restrictions, gating requirements, approval process.
- import_tariff_check(hs_code, origin_country, destination_country, declared_value_usd): Estimate import duties and taxes.
- labeling_requirements(product_type, target_market): List required labeling elements (CPSIA, ASTM, CE marking, etc).
- ce_marking_check(product_type, target_market): Check CE/UKCA marking requirements for EU/UK markets.

For every analysis you MUST:
1. Determine regulatory classification and required certifications
2. Search for existing patents and trademarks
3. Check platform category restrictions
4. Estimate import duties and taxes
5. Compile labeling requirements checklist
6. Output overall compliance risk level with justification

Output your final analysis as STRUCTURED JSON with:
- regulatory_status: compliant / needs_certification / restricted / prohibited
- required_certifications: list with estimated cost and timeline
- ip_risk_assessment: patent / trademark / design patent risks
- platform_compliance: any Amazon category restrictions?
- tariff_estimate: duty rate + estimated tax + additional fees
- labeling_checklist: required labels and warnings
- overall_risk_level: low / medium / high
"""

    async def execute(self, subtask: SubTask, mcp_registry: Dict[str, Any],
                      llm: Any, model: str) -> Dict[str, Any]:
        agent_tools = self._get_tools(mcp_registry)
        prompt = f"""{self.SYSTEM_PROMPT}

Available MCP tools: {json.dumps(agent_tools, ensure_ascii=False)}

Task: {subtask.action}
Input: {json.dumps(subtask.input_data, ensure_ascii=False)}

Execute step by step:
1. Determine product regulatory classification (FDA/CE/etc)
2. Search for existing patents and trademarks
3. Check platform category restrictions and gating requirements
4. Estimate import duties and taxes
5. Compile labeling requirements checklist
6. Output overall compliance risk level with justification

Output final result as JSON with all required fields."""
        result = await llm.call(prompt, model=model, tools=agent_tools)
        return {"compliance_analysis": json.loads(result), "tokens_used": 400}
