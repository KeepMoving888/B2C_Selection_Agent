# ============================================================
# agents/__init__.py — 全部 6 个 Agent 注册
# ============================================================

from .orchestrator import OrchestratorAgent
from .market_research import MarketResearchAgent
from .supply_chain import SupplyChainAgent
from .compliance import ComplianceAgent
from .profit_calculator import ProfitCalculatorAgent
from .trend_forecast import TrendForecastAgent

__all__ = [
    "OrchestratorAgent",
    "MarketResearchAgent",
    "SupplyChainAgent",
    "ComplianceAgent",
    "ProfitCalculatorAgent",
    "TrendForecastAgent",
]
