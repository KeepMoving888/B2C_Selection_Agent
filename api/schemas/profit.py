# api/schemas/profit.py
from typing import Dict, Optional

from pydantic import BaseModel, Field


class ProfitCalculateRequest(BaseModel):
    selling_price: float = Field(..., gt=0, description="售价 USD")
    unit_cost: float = Field(..., ge=0, description="产品成本 USD")
    category: str = Field(default="general", description="商品类目")
    market: str = Field(default="US", description="目标市场")


class ProfitCalculateResponse(BaseModel):
    selling_price: float
    unit_cost: float
    total_cost_per_unit: float
    gross_profit_per_unit: float
    gross_margin: float
    gross_margin_pct: str
    cost_breakdown: Dict[str, float]
    cost_breakdown_pct: Dict[str, str]
    roi_scenarios: Dict
    breakeven_units: Optional[int]
    suggestions: list[str] = []
