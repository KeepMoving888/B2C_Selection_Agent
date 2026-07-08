# ============================================================
# scripts/product_selection_report.py — 端到端选品报告生成器
#
# 用途：
#   串联 Google Trends + Amazon 竞品数据 + 评论分析 + 利润测算
#   + 季节性分析，输出一份完整的结构化选品报告。
#
# 运行：
#   python scripts/product_selection_report.py "cat toy"
#   python scripts/product_selection_report.py "automatic cat toy ball" --limit 3
#   python scripts/product_selection_report.py "yoga mat" --source api --limit 5
# ============================================================

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 将项目根目录加入模块搜索路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 自动加载 .env 环境变量（如果存在）
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from mcp_servers.amazon_server import AmazonMCPServer
from mcp_servers.social_server import SocialMediaMCPServer


OUTPUT_DIR = PROJECT_ROOT / "output"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="端到端选品报告生成器（Trends + Amazon + Reviews + Profit + Seasonality）"
    )
    parser.add_argument(
        "keyword",
        nargs="?",
        default=None,
        help='搜索关键词，例如 "cat toy"',
    )
    parser.add_argument(
        "--keyword",
        dest="keyword_explicit",
        default=None,
        help='搜索关键词（与位置参数等价），例如 --keyword "automatic cat toy ball"',
    )
    parser.add_argument(
        "--source",
        choices=["rainforest", "pa_api", "mock", "api"],
        default="rainforest",
        help="数据源：rainforest（默认） | pa_api | mock | api（api 等价于 rainforest）",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="分析竞品数量（默认 5）",
    )
    parser.add_argument(
        "--max-reviews",
        type=int,
        default=50,
        help="每个产品分析评论数（默认 50，最大 200）",
    )
    parser.add_argument(
        "--category",
        type=str,
        default="",
        help="品类提示，用于季节性/利润测算（如 pet_supplies, sports）",
    )
    parser.add_argument(
        "--selling-price",
        type=float,
        default=None,
        help="预期售价（USD），默认取竞品平均价",
    )
    parser.add_argument(
        "--unit-cost",
        type=float,
        default=None,
        help="预估单位成本（USD），默认按售价 25% 估算",
    )
    return parser.parse_args()


def get_keyword(args: argparse.Namespace) -> str:
    keyword = (args.keyword or args.keyword_explicit or "").strip()
    if keyword:
        return keyword
    user_input = input('请输入选品关键词（例如：cat toy）：').strip()
    if not user_input:
        print("未输入关键词，使用默认示例。")
        return "cat toy"
    return user_input


def infer_category(keyword: str) -> str:
    """根据关键词推断品类，用于季节性分析和利润测算。"""
    text = keyword.lower()
    if any(k in text for k in ["cat", "dog", "pet"]):
        return "pet_supplies"
    if any(k in text for k in ["earbud", "headphone", "speaker", "power bank", "phone case", "led strip"]):
        return "electronics"
    if any(k in text for k in ["lamp", "blender", "organizer", "kitchen"]):
        return "home_kitchen"
    if any(k in text for k in ["yoga", "resistance band", "massage gun", "fitness"]):
        return "sports"
    if any(k in text for k in ["makeup", "brush", "beauty"]):
        return "beauty"
    if any(k in text for k in ["baby", "silicone plate"]):
        return "baby"
    return "default"


def estimate_monthly_sales(bsr: Optional[int]) -> Optional[int]:
    """根据 BSR 粗略估算月销量。"""
    if bsr is None:
        return None
    if bsr <= 100:
        return 3000
    if bsr <= 1000:
        return 1500
    if bsr <= 5000:
        return 600
    if bsr <= 20000:
        return 200
    if bsr <= 50000:
        return 80
    if bsr <= 100000:
        return 30
    return 10


def calculate_profit(selling_price: float, unit_cost: float, category: str) -> Dict:
    """确定性利润测算（复用 ProfitCalculatorAgent 逻辑）。"""
    referral_fees = {
        "pet_supplies": 0.15, "toys": 0.15,
        "home_kitchen": 0.15, "electronics": 0.08,
        "clothing": 0.17, "beauty": 0.15,
        "sports": 0.15, "baby": 0.15, "default": 0.15,
    }
    fba_fees = {
        "small_standard": 3.22, "large_standard": 5.40,
        "small_oversize": 9.88, "default": 4.80,
    }

    referral_rate = referral_fees.get(category, 0.15)

    # 根据品类和售价推断尺寸档位，更接近真实 FBA 费用
    if category in ["pet_supplies", "baby", "beauty"] or selling_price <= 15:
        size_tier = "small_standard"
    elif category in ["home_kitchen", "sports"]:
        size_tier = "large_standard"
    else:
        size_tier = "default"
    fba_fee = fba_fees.get(size_tier, 4.80)

    cost_breakdown = {
        "product_cost": round(unit_cost, 2),
        "shipping_per_unit": 2.0,
        "fba_fee": round(fba_fee, 2),
        "referral_fee": round(selling_price * referral_rate, 2),
        "advertising_per_unit": round(selling_price * 0.08, 2),
        "return_allowance": round(selling_price * 0.03, 2),
        "misc_cost": 0.50,
    }

    total_cost = sum(cost_breakdown.values())
    gross_profit = selling_price - total_cost
    gross_margin = gross_profit / selling_price if selling_price > 0 else 0

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

    recommendation = (
        "RECOMMENDED" if gross_margin >= 0.2
        else "MARGINAL" if gross_margin >= 0.1
        else "NOT RECOMMENDED"
    )

    return {
        "selling_price": round(selling_price, 2),
        "unit_cost": round(unit_cost, 2),
        "total_cost_per_unit": round(total_cost, 2),
        "gross_profit_per_unit": round(gross_profit, 2),
        "gross_margin": f"{gross_margin:.1%}",
        "cost_breakdown": cost_breakdown,
        "roi_scenarios": roi,
        "breakeven_units": round(2000 / gross_profit) if gross_profit > 0 else None,
        "recommendation": recommendation,
    }


def aggregate_reviews(reviews_list: List[Dict]) -> Dict:
    """聚合多个竞品的评论洞察。"""
    pain_point_counts: Dict[str, int] = {}
    praised_counts: Dict[str, int] = {}
    feature_counts: Dict[str, int] = {}
    total_reviews = 0
    total_positive = 0
    total_neutral = 0
    total_negative = 0

    for r in reviews_list:
        total_reviews += r.get("total_reviews_analyzed", 0)
        sentiment = r.get("sentiment_summary", {})
        total_positive += sentiment.get("positive", 0)
        total_neutral += sentiment.get("neutral", 0)
        total_negative += sentiment.get("negative", 0)

        for p in r.get("top_pain_points", []):
            key = p.get("issue", "")
            if key:
                pain_point_counts[key] = pain_point_counts.get(key, 0) + p.get("mention_count", 0)
        for p in r.get("top_praised_features", []):
            key = p.get("feature", "")
            if key:
                praised_counts[key] = praised_counts.get(key, 0) + p.get("mention_count", 0)
        for p in r.get("top_mentioned_features", []):
            key = p.get("feature", "")
            if key:
                feature_counts[key] = feature_counts.get(key, 0) + p.get("mention_count", 0)

    return {
        "products_analyzed": len(reviews_list),
        "total_reviews_analyzed": total_reviews,
        "sentiment_summary": {
            "positive": total_positive,
            "neutral": total_neutral,
            "negative": total_negative,
        },
        "top_pain_points": sorted(
            [{"issue": k, "mention_count": v} for k, v in pain_point_counts.items()],
            key=lambda x: x["mention_count"],
            reverse=True,
        )[:5],
        "top_praised_features": sorted(
            [{"feature": k, "mention_count": v} for k, v in praised_counts.items()],
            key=lambda x: x["mention_count"],
            reverse=True,
        )[:5],
        "top_mentioned_features": sorted(
            [{"feature": k, "mention_count": v} for k, v in feature_counts.items()],
            key=lambda x: x["mention_count"],
            reverse=True,
        )[:5],
    }


async def fetch_trends(social_server: SocialMediaMCPServer, keyword: str) -> Dict:
    print(f"\n📈 步骤 1/5：获取 Google Trends 趋势数据 '{keyword}' ...")
    response = await social_server.call_tool(
        "google_trends_fetch",
        {
            "keywords": [keyword],
            "region": "US",
            "timeframe": "today 12-m",
        },
    )
    result = response.get("result", response)
    print(f"   趋势方向：{result.get('trend_direction', 'unknown')} | 置信度：{result.get('confidence', 0)}")
    return result


async def fetch_amazon_products(
    amazon_server: AmazonMCPServer, keyword: str, source: str, limit: int
) -> Dict:
    print(f"\n🔍 步骤 2/5：搜索 Amazon 竞品 '{keyword}' ...")
    response = await amazon_server.call_tool(
        "amazon_product_search",
        {
            "keyword": keyword,
            "market": "com",
            "limit": limit * 2,
            "source": source,
        },
    )
    result = response.get("result", response)
    products = result.get("results", [])

    # ASIN 去重
    seen_asins = set()
    unique_products = []
    for p in products:
        asin = p.get("asin", "")
        if asin and asin not in seen_asins:
            seen_asins.add(asin)
            unique_products.append(p)
        if len(unique_products) >= limit:
            break

    print(f"   找到 {len(unique_products)} 个去重产品")
    return {
        **result,
        "results": unique_products,
        "returned_count": len(unique_products),
    }


async def enrich_product_details(
    amazon_server: AmazonMCPServer, product: Dict, source: str
) -> Dict:
    asin = product.get("asin", "")
    if not asin:
        return product

    response = await amazon_server.call_tool(
        "amazon_product_details",
        {
            "asin": asin,
            "market": "com",
            "source": source,
        },
    )
    detail = response.get("result", response)

    is_sample_detail = detail.get("title", "").startswith("Sample Product")
    detail_title = detail.get("title", "")
    # Mock 详情兜底标题比较通用，优先保留搜索得到的真实感标题
    if is_sample_detail:
        detail_title = product.get("title", "")

    # 对于 Mock 详情，优先使用搜索阶段生成的真实感价格/评分/BSR
    price = product.get("price") if is_sample_detail else (detail.get("price") if detail.get("price") is not None else product.get("price"))
    rating = product.get("rating") if is_sample_detail else (detail.get("rating") if detail.get("rating") is not None else product.get("rating"))
    review_count = product.get("review_count", 0) if is_sample_detail else (detail.get("review_count") if detail.get("review_count") else product.get("review_count", 0))
    bsr = product.get("bsr") if is_sample_detail else detail.get("bsr")

    merged = {
        **product,
        "title": detail_title or product.get("title", ""),
        "brand": detail.get("brand") or product.get("brand", ""),
        "category": detail.get("category") or product.get("category", ""),
        "price": price,
        "currency": detail.get("currency", "USD") if detail.get("currency") else product.get("currency", "USD"),
        "rating": rating,
        "review_count": review_count,
        "bsr": bsr,
        "estimated_monthly_sales": estimate_monthly_sales(bsr),
        "dimensions": detail.get("dimensions", ""),
        "weight": detail.get("weight", ""),
        "images": detail.get("images") or product.get("images", []),
        "url": detail.get("url") or product.get("url", f"https://www.amazon.com/dp/{asin}"),
        "detail_data_quality": detail.get("data_quality", "unknown"),
    }
    return merged


async def analyze_product_reviews(
    amazon_server: AmazonMCPServer, product: Dict, source: str, max_reviews: int
) -> Dict:
    asin = product.get("asin", "")
    title = product.get("title", "")

    response = await amazon_server.call_tool(
        "amazon_review_analysis",
        {
            "asin": asin,
            "market": "com",
            "max_reviews": max_reviews,
            "source": source,
            "product_title": title,
        },
    )
    result = response.get("result", response)
    result["product_title"] = title
    result["asin"] = asin
    return result


async def generate_report(args: argparse.Namespace) -> Dict:
    keyword = get_keyword(args)
    # api 是 rainforest 的别名，方便命令行使用
    source = args.source if args.source != "api" else "rainforest"
    limit = min(args.limit, 10)
    max_reviews = min(args.max_reviews, 200)
    category = args.category or infer_category(keyword)

    print("=" * 70)
    print(f"  端到端选品报告：{keyword}")
    print(f"  数据源：{source} | 品类：{category} | 分析产品数：{limit}")
    print("=" * 70)

    amazon_server = AmazonMCPServer(
        rainforest_api_key=os.getenv("RAINFOREST_API_KEY"),
        pa_api_key=os.getenv("AMAZON_PA_API_KEY"),
        pa_api_secret=os.getenv("AMAZON_PA_API_SECRET"),
        pa_partner_tag=os.getenv("AMAZON_PARTNER_TAG"),
        default_source=source,
    )
    social_server = SocialMediaMCPServer()

    try:
        # 1. Google Trends
        trends = await fetch_trends(social_server, keyword)

        # 2. Amazon 竞品
        search_result = await fetch_amazon_products(amazon_server, keyword, source, limit)
        products = search_result.get("results", [])

        # 3. 获取详情
        print(f"\n📦 步骤 3/5：获取 {len(products)} 个产品详情 ...")
        detailed_products = []
        for idx, p in enumerate(products, 1):
            print(f"   ({idx}/{len(products)}) {p.get('asin', '')}")
            detailed = await enrich_product_details(amazon_server, p, source)
            detailed_products.append(detailed)

        # 4. 评论分析
        print(f"\n💬 步骤 4/5：分析 {len(detailed_products)} 个产品评论 ...")
        reviews_list = []
        for idx, p in enumerate(detailed_products, 1):
            print(f"   ({idx}/{len(detailed_products)}) {p.get('asin', '')} - {p.get('title', '')[:40]}...")
            review = await analyze_product_reviews(amazon_server, p, source, max_reviews)
            reviews_list.append(review)

        # 5. 季节性分析
        print(f"\n🗓️  步骤 5/5：获取品类季节性模式 ...")
        seasonality_response = await social_server.call_tool(
            "seasonality_detection",
            {"category": category, "market": "US", "years_back": 5},
        )
        seasonality = seasonality_response.get("result", seasonality_response)

        # 聚合评论洞察
        aggregated_reviews = aggregate_reviews(reviews_list)

        # 利润测算
        valid_prices = [p["price"] for p in detailed_products if p.get("price") is not None and p["price"] > 0]
        avg_price = round(sum(valid_prices) / len(valid_prices), 2) if valid_prices else 19.99
        selling_price = args.selling_price or avg_price
        unit_cost = args.unit_cost or round(selling_price * 0.25, 2)
        profit_analysis = calculate_profit(selling_price, unit_cost, category)

        # 市场统计
        valid_ratings = [p["rating"] for p in detailed_products if p.get("rating") is not None]
        valid_reviews = [p["review_count"] for p in detailed_products if p.get("review_count", 0) > 0]
        valid_bsrs = [p["bsr"] for p in detailed_products if p.get("bsr") is not None]
        valid_sales = [p["estimated_monthly_sales"] for p in detailed_products if p.get("estimated_monthly_sales") is not None]

        market_stats = {
            "avg_price": avg_price,
            "avg_rating": round(sum(valid_ratings) / len(valid_ratings), 1) if valid_ratings else 0,
            "avg_reviews": round(sum(valid_reviews) / len(valid_reviews), 0) if valid_reviews else 0,
            "min_bsr": min(valid_bsrs) if valid_bsrs else None,
            "avg_estimated_monthly_sales": round(sum(valid_sales) / len(valid_sales), 0) if valid_sales else None,
        }

        # 综合评分
        margin_score = 0
        if profit_analysis["gross_margin"]:
            try:
                margin_pct = float(profit_analysis["gross_margin"].rstrip("%")) / 100
                margin_score = min(margin_pct * 250, 40)
            except Exception:
                pass

        trend_score = 25 if trends.get("trend_direction") == "rising" else 15 if trends.get("trend_direction") == "stable" else 5
        competition_score = 0
        if market_stats["avg_reviews"]:
            if market_stats["avg_reviews"] < 1000:
                competition_score = 25
            elif market_stats["avg_reviews"] < 5000:
                competition_score = 15
            else:
                competition_score = 5
        review_score = 10 if aggregated_reviews["top_pain_points"] else 0

        total_score = round(margin_score + trend_score + competition_score + review_score, 1)

        final_recommendation = "谨慎进入" if total_score < 50 else "可以考虑" if total_score < 75 else "推荐进入"

        report = {
            "record_id": f"selection_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "keyword": keyword,
            "category": category,
            "market": "com",
            "data_source": source,
            "created_at": datetime.now().isoformat(),
            "executive_summary": {
                "overall_score": total_score,
                "max_score": 100,
                "recommendation": final_recommendation,
                "score_breakdown": {
                    "profit_margin": round(margin_score, 1),
                    "trend_strength": trend_score,
                    "competition_intensity": competition_score,
                    "review_insight_depth": review_score,
                },
            },
            "market_analysis": {
                "data_quality": search_result.get("data_quality", "unknown"),
                "total_search_results": search_result.get("total_results", 0),
                "analyzed_products": len(detailed_products),
                **market_stats,
                "top_products": detailed_products,
            },
            "trend_analysis": {
                "keywords": trends.get("keywords", []),
                "trend_direction": trends.get("trend_direction", "unknown"),
                "confidence": trends.get("confidence", 0),
                "current_interest": trends.get("interest_over_time", {}).get(keyword, {}).get("current_value", 0),
                "yoy_change_pct": trends.get("interest_over_time", {}).get(keyword, {}).get("yoy_change_pct", 0),
                "rising_queries": trends.get("related_queries_rising", []),
                "regional_breakdown": trends.get("regional_breakdown", []),
                "data_quality": trends.get("data_quality", "unknown"),
            },
            "review_insights": {
                "data_quality": "SIMULATED — based on product category archetypes" if source == "mock" else reviews_list[0].get("data_quality", "unknown") if reviews_list else "unknown",
                **aggregated_reviews,
                "per_product_reviews": reviews_list,
            },
            "profit_analysis": profit_analysis,
            "seasonality": seasonality,
            "final_recommendation": {
                "verdict": final_recommendation,
                "rationale": (
                    f"关键词 '{keyword}' 在 Amazon 上平均售价 ${market_stats['avg_price']}，"
                    f"毛利率 {profit_analysis['gross_margin']}，"
                    f"Google Trends 趋势为 {trends.get('trend_direction', 'unknown')}。"
                    f"竞品平均评论数 {int(market_stats['avg_reviews'])}，"
                    f"{'竞争较激烈' if market_stats['avg_reviews'] > 5000 else '竞争相对温和'}。"
                    f"主要用户痛点：{', '.join([p['issue'] for p in aggregated_reviews['top_pain_points'][:3]]) or '暂无'}。"
                ),
                "next_steps": [
                    f"针对痛点优化产品：{', '.join([p['issue'] for p in aggregated_reviews['top_pain_points'][:2]]) or '持续调研'}",
                    "验证供应链成本和交期",
                    "确认合规认证要求（FDA/CE/CPSC 等）",
                    "小批量测款，监控 BSR 和广告 ROI",
                ],
            },
        }

        return report

    finally:
        await amazon_server.close()


async def main():
    args = parse_args()

    report = await generate_report(args)

    # 保存报告
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_keyword = re.sub(r"[^\w\-]+", "_", report["keyword"]).strip("_").lower()
    output_path = OUTPUT_DIR / f"selection_report_{safe_keyword}_{timestamp}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 控制台摘要
    summary = report["executive_summary"]
    market = report["market_analysis"]
    profit = report["profit_analysis"]
    trend = report["trend_analysis"]

    print("\n" + "=" * 70)
    print("  端到端选品报告摘要")
    print("=" * 70)
    print(f"  关键词：{report['keyword']}")
    print(f"  综合评分：{summary['overall_score']}/{summary['max_score']} — {summary['recommendation']}")
    print(f"  数据质量：{market['data_quality']}")
    print(f"  平均售价：${market['avg_price']} | 平均评分：{market['avg_rating']}")
    print(f"  平均评论数：{int(market['avg_reviews'])} | 最小 BSR：{market['min_bsr']}")
    print(f"  毛利率：{profit['gross_margin']} | 单件毛利：${profit['gross_profit_per_unit']}")
    print(f"  Google Trends：{trend['trend_direction']} (置信度 {trend['confidence']})")
    print("=" * 70)
    print(f"\n✅ 完整报告已保存：{output_path}")


if __name__ == "__main__":
    asyncio.run(main())
