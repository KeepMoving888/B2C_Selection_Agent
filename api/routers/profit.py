# api/routers/profit.py
from typing import Optional

from fastapi import APIRouter

from api.schemas.profit import ProfitCalculateRequest, ProfitCalculateResponse
from api.services.report_engine import _calculate_profit

router = APIRouter(prefix="/profit", tags=["利润测算"])


def _build_suggestions(profit: dict) -> list[str]:
    suggestions = []
    margin = profit["gross_margin"]
    breakdown = profit["cost_breakdown"]
    total = profit["total_cost_per_unit"]
    top_cost = max(breakdown, key=breakdown.get)
    top_cost_pct = profit["cost_breakdown_pct"].get(top_cost, "0%")

    if margin < 0.15:
        suggestions.append(
            f"毛利率仅 {profit['gross_margin_pct']}，建议优先压缩{top_cost}（占比 {top_cost_pct}）或上调售价 5-10%。"
        )
    else:
        suggestions.append(
            f"毛利率 {profit['gross_margin_pct']} 健康，可重点优化{top_cost}（占比 {top_cost_pct}）以扩大利润安全垫。"
        )

    if breakdown.get("广告费用", 0) / total > 0.12:
        suggestions.append("广告费用占比较高，建议通过关键词精准投放、A/B 测试主图与 A+ 内容提升转化率，降低 ACoS。")
    else:
        suggestions.append("广告占比可控，可适度增加预算抢占头部关键词排名，放大销量规模。")

    if breakdown.get("FBA 费用", 0) > 4:
        suggestions.append("FBA 费用较大，可优化包装尺寸/重量，或评估轻小商品计划降本。")
    else:
        suggestions.append("FBA 费用处于合理区间，关注库存周转，避免长期仓储费侵蚀利润。")

    return suggestions


@router.post("/calculate", response_model=ProfitCalculateResponse)
async def calculate_profit(payload: ProfitCalculateRequest):
    profit = _calculate_profit(
        selling_price=payload.selling_price,
        unit_cost=payload.unit_cost,
        category=payload.category,
        market=payload.market,
    )
    return ProfitCalculateResponse(
        selling_price=profit["selling_price"],
        unit_cost=profit["unit_cost"],
        total_cost_per_unit=profit["total_cost_per_unit"],
        gross_profit_per_unit=profit["gross_profit_per_unit"],
        gross_margin=profit["gross_margin"],
        gross_margin_pct=profit["gross_margin_pct"],
        cost_breakdown=profit["cost_breakdown"],
        cost_breakdown_pct=profit["cost_breakdown_pct"],
        roi_scenarios=profit["roi_scenarios"],
        breakeven_units=profit.get("breakeven_units"),
        suggestions=_build_suggestions(profit),
    )
