# ============================================================
# agents/orchestrator.py — Orchestrator Agent
#
# 多 Agent 系统的中央调度器。负责意图理解、任务规划、
# 质量验证和最终报告生成。
# ============================================================

from __future__ import annotations

import json
from typing import Any, Dict, List

from harness.agent_loop import SubTask
from .base import BaseAgent


class OrchestratorAgent(BaseAgent):
    """
    Orchestrator Agent — 选品系统的调度核心。

    不直接执行分析，而是将复杂任务拆解后分发给 5 个
    专业 Agent 协作完成，最终汇总生成结构化报告。
    Multi-Agent 架构的核心价值：分工专业化。
    """

    def __init__(self, llm_client: Any, model_router: Any):
        self.llm = llm_client
        self.router = model_router

    async def execute(
        self,
        subtask: SubTask,
        mcp_registry: Dict[str, Any],
        llm: Any,
        model: str,
    ) -> Dict[str, Any]:
        action = subtask.action.lower()

        if "plan" in action or "decompose" in action:
            return await self._generate_plan(subtask, llm, model)
        elif "verify" in action or "validate" in action:
            return await self._verify_quality(subtask, llm, model)
        elif "synthesize" in action or "report" in action:
            return await self._synthesize_report(subtask, llm, model)
        else:
            return await self._generic_execute(subtask, llm, model)

    async def _generate_plan(
        self, subtask: SubTask, llm: Any, model: str
    ) -> Dict:
        prompt = f"""You are a product selection strategist for cross-border e-commerce.

Task: {subtask.action}
Context: {json.dumps(subtask.input_data, ensure_ascii=False)}

Decompose this into a detailed execution plan with:
1. Analysis steps (what to analyze, in what order)
2. Data sources needed (Amazon, 1688, Google Trends, FDA, etc.)
3. Dependencies between steps
4. Success criteria for each step

Output as structured JSON.
"""
        response = await llm.call(prompt, model=model)
        return {"plan": json.loads(response), "tokens_used": 500}

    async def _verify_quality(
        self, subtask: SubTask, llm: Any, model: str
    ) -> Dict:
        results = subtask.input_data.get("aggregated_results", {})
        prompt = f"""You are a quality assurance specialist for product selection analysis.

Aggregated results from multiple agents: {json.dumps(results, ensure_ascii=False)}

Verify:
1. Completeness: Are all 6 dimensions covered? (market/supply/compliance/profit/trend/social)
2. Consistency: Do any findings contradict each other?
3. Confidence: How reliable is each analysis? Flag low-confidence items.

Output JSON: completeness_score(0-1), consistency_score(0-1),
confidence_flags, overall_pass(true/false), issues[]"""
        response = await llm.call(prompt, model=model)
        return {"verification": json.loads(response), "tokens_used": 400}

    async def _synthesize_report(
        self, subtask: SubTask, llm: Any, model: str
    ) -> Dict:
        return {"report": "placeholder", "tokens_used": 300}

    async def _generic_execute(
        self, subtask: SubTask, llm: Any, model: str
    ) -> Dict:
        response = await llm.call(
            f"Execute: {subtask.action}\nInput: {json.dumps(subtask.input_data)}",
            model=model)
        return {"result": response, "tokens_used": 300}
