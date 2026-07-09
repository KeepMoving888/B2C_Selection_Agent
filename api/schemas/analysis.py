# api/schemas/analysis.py
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AnalysisCreate(BaseModel):
    keyword: str = Field(..., min_length=1, description="分析关键词，支持英文关键词，多个用逗号/分号分隔")
    market: str = Field(default="US", description="目标市场代码")
    budget: str = Field(default="medium", description="预算区间")
    selling_price: Optional[float] = Field(default=None, description="可选售价")
    unit_cost: Optional[float] = Field(default=None, description="可选成本")


class AnalysisResponse(BaseModel):
    id: str = Field(..., description="分析记录 ID")
    status: str = Field(default="completed", description="任务状态")
    report: Dict[str, Any]


class AnalysisHistoryItem(BaseModel):
    id: str
    keyword: str
    market: str
    grade: str
    overall_score: float
    created_at: str


class AnalysisHistoryResponse(BaseModel):
    items: List[AnalysisHistoryItem]
    total: int
