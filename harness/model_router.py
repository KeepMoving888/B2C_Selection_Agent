# ============================================================
# harness/model_router.py — 四层智能模型路由
#
# 根据任务复杂度和成本要求自动选择最优模型。
# 路由决策：简单查询 → V4 Flash(便宜)，复杂推理 → V4 Pro(强)，
# 领域分析 → Qwen2.5-7B ORPO(本地零成本)，API 不可用 → Base(保底)
# ============================================================

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from monitoring.metrics import MetricsCollector


class ModelTier(Enum):
    FLASH = "flash"         # V4 Flash — 简单任务，高性价比
    LOCAL = "local"         # Qwen2.5-7B ORPO — 领域微调，零边际成本
    PREMIUM = "premium"     # V4 Pro — 复杂推理，最强质量
    FALLBACK = "fallback"   # Qwen2.5-7B Base — 降级保底


@dataclass
class ModelRoute:
    model_name: str
    tier: ModelTier
    estimated_latency_ms: int
    estimated_cost_per_1k_tokens: float
    reason: str


class ModelRouter:
    """
    四层智能模型路由。

    决策树：
    - Orchestrator Plan/Verify/Synthesize → V4 Pro（需要强推理）
    - 简单工具调用/数据检索 → V4 Flash（便宜够用）
    - 领域分析/竞品/趋势 → Qwen2.5-7B ORPO（领域微调，懂业务）
    - API 不可用时 → Qwen2.5-7B Base（保底）
    """

    MODELS = {
        "v4-flash": {
            # DeepSeek V4 系列高速模型（2026-04 发布）。
            # 旧别名 deepseek-chat 计划于 2026-07-24 退役。
            "name": "deepseek-v4-flash",
            "tier": ModelTier.FLASH,
            "latency_ms": 500,
            "cost_per_1k": 0.00014,       # 官方 promo 价 ~$0.14/1M input
        },
        "v4-pro": {
            # DeepSeek V4 系列旗舰推理模型（2026-04 发布）。
            # 旧别名 deepseek-reasoner 计划于 2026-07-24 退役。
            "name": "deepseek-v4-pro",
            "tier": ModelTier.PREMIUM,
            "latency_ms": 3000,
            "cost_per_1k": 0.000435,      # 官方 promo 价 ~$0.435/1M input
        },
        "qwen2.5-7b-orpo": {
            "name": "qwen2.5-7b-orpo-ecommerce",
            "tier": ModelTier.LOCAL,
            "latency_ms": 200,
            "cost_per_1k": 0.0,
        },
        "qwen2.5-7b-base": {
            "name": "qwen2.5-7b-base",
            "tier": ModelTier.FALLBACK,
            "latency_ms": 250,
            "cost_per_1k": 0.0,
        },
    }

    # Agent -> 默认模型映射
    AGENT_MODEL_MAP = {
        "orchestrator":    "v4-pro",
        "market_research": "qwen2.5-7b-orpo",
        "supply_chain":    "v4-flash",
        "compliance":      "v4-flash",
        "profit_calculator": "qwen2.5-7b-base",
        "trend_forecast":  "qwen2.5-7b-orpo",
    }

    # Orchestrator 的复杂推理阶段强制使用 Pro
    PREMIUM_PHASES = {"plan", "synthesize", "verify", "replan"}

    def __init__(self, metrics_collector: Optional["MetricsCollector"] = None):
        self._route_history: list = []
        self._model_health: Dict[str, bool] = {
            m: True for m in self.MODELS}
        self._metrics = metrics_collector

    def route(self, agent_or_phase: str) -> str:
        """路由决策入口"""
        if agent_or_phase in self.PREMIUM_PHASES:
            target = "v4-pro"
        else:
            target = self.AGENT_MODEL_MAP.get(
                agent_or_phase, "qwen2.5-7b-orpo")

        if not self._model_health.get(target, False):
            target = self._fallback(target)

        route = ModelRoute(
            model_name=target,
            tier=self.MODELS[target]["tier"],
            estimated_latency_ms=self.MODELS[target]["latency_ms"],
            estimated_cost_per_1k_tokens=self.MODELS[target]["cost_per_1k"],
            reason=f"{agent_or_phase} -> {target}",
        )
        self._route_history.append(route)
        if self._metrics:
            self._metrics.record_model_route(
                model=target,
                tier=self.MODELS[target]["tier"].value,
            )
        return target

    def _fallback(self, current: str) -> str:
        """递归降级：Pro -> ORPO -> Base，最底层抛异常"""
        chain = {
            "v4-pro": "qwen2.5-7b-orpo",
            "v4-flash": "qwen2.5-7b-orpo",
            "qwen2.5-7b-orpo": "qwen2.5-7b-base",
        }
        next_model = chain.get(current)
        if next_model and self._model_health.get(next_model, False):
            return next_model
        if next_model:
            return self._fallback(next_model)
        if current == "qwen2.5-7b-base":
            raise RuntimeError(
                "All model tiers unavailable — check GPU/API")
        return current

    def mark_unhealthy(self, model_name: str):
        self._model_health[model_name] = False

    def mark_healthy(self, model_name: str):
        self._model_health[model_name] = True

    def get_stats(self) -> Dict:
        """路由统计 — 用于监控和成本分析"""
        total = len(self._route_history)
        if total == 0:
            return {}
        flash = sum(1 for r in self._route_history
                    if r.tier == ModelTier.FLASH)
        local = sum(1 for r in self._route_history
                    if r.tier == ModelTier.LOCAL)
        premium = sum(1 for r in self._route_history
                      if r.tier == ModelTier.PREMIUM)
        cost_saved = flash * 0.002 + local * 0.002  # 相比全部用Pro节省
        return {
            "total_requests": total,
            "flash_ratio": f"{flash / total:.1%}",
            "local_ratio": f"{local / total:.1%}",
            "premium_ratio": f"{premium / total:.1%}",
            "cost_saved_vs_all_pro": f"${cost_saved:.4f}",
        }
