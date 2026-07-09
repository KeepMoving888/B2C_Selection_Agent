# api/routers/analysis.py
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.routers.auth import UserInfo, get_current_user
from api.schemas.analysis import (
    AnalysisCreate,
    AnalysisHistoryItem,
    AnalysisHistoryResponse,
    AnalysisResponse,
)
from api.services.report_engine import generate_report

router = APIRouter(prefix="/analysis", tags=["商品分析"])

# 阶段一：内存存储分析记录
_analysis_store: Dict[str, Dict[str, Any]] = {}


def _split_keywords(text: str) -> List[str]:
    """使用逗号或分号分隔关键词，兼容英文关键词中的空格。"""
    parts = []
    for sep in (",", ";"):
        if sep in text:
            parts = [p.strip() for p in text.split(sep) if p.strip()]
            break
    if not parts:
        parts = [text.strip()]
    return parts


@router.post("", response_model=AnalysisResponse)
async def create_analysis(
    payload: AnalysisCreate,
    user: Optional[UserInfo] = Depends(get_current_user),
):
    keywords = _split_keywords(payload.keyword)
    primary_keyword = keywords[0]

    report = generate_report(
        keyword=primary_keyword,
        market=payload.market,
        budget=payload.budget,
        selling_price=payload.selling_price,
        unit_cost=payload.unit_cost,
    )

    analysis_id = str(uuid.uuid4())
    record = {
        "id": analysis_id,
        "user": user.username if user else "anonymous",
        "keyword": primary_keyword,
        "keywords": keywords,
        "market": payload.market,
        "budget": payload.budget,
        "status": "completed",
        "report": report,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _analysis_store[analysis_id] = record

    return AnalysisResponse(id=analysis_id, status="completed", report=report)


@router.get("/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(analysis_id: str):
    record = _analysis_store.get(analysis_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分析记录不存在")
    return AnalysisResponse(
        id=record["id"],
        status=record["status"],
        report=record["report"],
    )


@router.get("/history/list", response_model=AnalysisHistoryResponse)
async def list_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    items = sorted(_analysis_store.values(), key=lambda x: x["created_at"], reverse=True)
    total = len(items)
    page = items[offset : offset + limit]
    return AnalysisHistoryResponse(
        items=[
            AnalysisHistoryItem(
                id=r["id"],
                keyword=r["keyword"],
                market=r["market"],
                grade=r["report"]["grade"],
                overall_score=r["report"]["overall_score"],
                created_at=r["created_at"],
            )
            for r in page
        ],
        total=total,
    )


@router.post("/{analysis_id}/compare")
async def compare_analysis(analysis_id: str, target_id: str):
    source = _analysis_store.get(analysis_id)
    target = _analysis_store.get(target_id)
    if not source or not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对比记录不存在")
    return {
        "source": {
            "id": source["id"],
            "keyword": source["keyword"],
            "grade": source["report"]["grade"],
            "overall_score": source["report"]["overall_score"],
        },
        "target": {
            "id": target["id"],
            "keyword": target["keyword"],
            "grade": target["report"]["grade"],
            "overall_score": target["report"]["overall_score"],
        },
    }
