# ============================================================
# scripts/amazon_product_analysis.py — Amazon 产品深度分析工具
#
# 用途：
#   1. 根据关键词搜索 Amazon 产品
#   2. 对每个产品调用详情接口获取真实 BSR、品牌、类目、尺寸
#   3. 生成带销量排名的专业选品分析记录
#
# 运行：
#   python scripts/amazon_product_analysis.py "cat toy"
#   python scripts/amazon_product_analysis.py "automatic cat toy ball" --limit 5
# ============================================================

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# 将项目根目录加入模块搜索路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 自动加载 .env 环境变量（如果存在）
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from mcp_servers.amazon_server import AmazonMCPServer


OUTPUT_DIR = PROJECT_ROOT / "output"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Amazon 产品深度分析工具（含真实 BSR/品牌/类目）"
    )
    parser.add_argument(
        "keyword",
        nargs="?",
        default=None,
        help='搜索关键词，例如 "automatic cat toy ball"',
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
        help="要获取详情的产品数量（默认 5）",
    )
    return parser.parse_args()


def get_keyword(args: argparse.Namespace) -> str:
    keyword = (args.keyword or args.keyword_explicit or "").strip()
    if keyword:
        return keyword
    user_input = input('请输入 Amazon 搜索关键词（例如：automatic cat toy ball）：').strip()
    if not user_input:
        print("未输入关键词，使用默认示例。")
        return "automatic cat toy ball"
    return user_input


def estimate_monthly_sales(bsr: Optional[int], category: str = "") -> Optional[int]:
    """根据 BSR 粗略估算月销量（非常粗略，仅供参考）。"""
    if bsr is None:
        return None
    # 简化模型：BSR 越小销量越高
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


async def analyze_keyword(server: AmazonMCPServer, keyword: str, source: str, limit: int) -> dict:
    """搜索关键词并获取每个产品的详情。"""
    print(f"\n🔍 步骤 1/2：搜索关键词 '{keyword}' ...")

    search_response = await server.call_tool(
        "amazon_product_search",
        {
            "keyword": keyword,
            "market": "com",
            "limit": limit * 2,  # 多搜一些，去重后取前 N
            "source": source,
        },
    )
    search_result = search_response.get("result", search_response)

    products = search_result.get("results", [])
    if not products:
        return {
            "keyword": keyword,
            "source": source,
            "data_quality": search_result.get("data_quality", "unknown"),
            "error": "未找到产品",
            "products": [],
        }

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

    print(f"   找到 {len(unique_products)} 个去重产品，开始获取详情 ...")

    detailed_products = []
    for idx, product in enumerate(unique_products, 1):
        asin = product.get("asin", "")
        if not asin:
            continue

        print(f"   步骤 2/2：获取 ASIN {asin} 详情 ({idx}/{len(unique_products)}) ...")
        detail_response = await server.call_tool(
            "amazon_product_details",
            {
                "asin": asin,
                "market": "com",
                "source": source,
            },
        )
        detail = detail_response.get("result", detail_response)

        # 合并搜索和详情数据
        merged = {
            "asin": asin,
            "title": detail.get("title") or product.get("title", ""),
            "brand": detail.get("brand") or product.get("brand", ""),
            "category": detail.get("category") or product.get("category", ""),
            "price": detail.get("price") if detail.get("price") is not None else product.get("price"),
            "currency": detail.get("currency", "USD"),
            "rating": detail.get("rating") if detail.get("rating") is not None else product.get("rating"),
            "review_count": detail.get("review_count") if detail.get("review_count") else product.get("review_count", 0),
            "bsr": detail.get("bsr"),
            "estimated_monthly_sales": estimate_monthly_sales(detail.get("bsr")),
            "dimensions": detail.get("dimensions", ""),
            "weight": detail.get("weight", ""),
            "images": detail.get("images") or product.get("images", []),
            "url": detail.get("url") or product.get("url", f"https://www.amazon.com/dp/{asin}"),
            "detail_data_quality": detail.get("data_quality", "unknown"),
        }
        detailed_products.append(merged)

    # 计算统计
    valid_prices = [p["price"] for p in detailed_products if p.get("price") is not None and p["price"] > 0]
    valid_ratings = [p["rating"] for p in detailed_products if p.get("rating") is not None]
    valid_reviews = [p["review_count"] for p in detailed_products if p.get("review_count", 0) > 0]
    valid_bsrs = [p["bsr"] for p in detailed_products if p.get("bsr") is not None]
    valid_sales = [p["estimated_monthly_sales"] for p in detailed_products if p.get("estimated_monthly_sales") is not None]

    return {
        "record_id": f"amazon_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "keyword": keyword,
        "source": source,
        "market": "com",
        "data_quality": search_result.get("data_quality", "unknown"),
        "total_search_results": search_result.get("total_results", 0),
        "analyzed_count": len(detailed_products),
        "avg_price": round(sum(valid_prices) / len(valid_prices), 2) if valid_prices else 0,
        "avg_rating": round(sum(valid_ratings) / len(valid_ratings), 1) if valid_ratings else 0,
        "avg_reviews": round(sum(valid_reviews) / len(valid_reviews), 0) if valid_reviews else 0,
        "min_bsr": min(valid_bsrs) if valid_bsrs else None,
        "avg_estimated_monthly_sales": round(sum(valid_sales) / len(valid_sales), 0) if valid_sales else None,
        "products": detailed_products,
        "created_at": datetime.now().isoformat(),
    }


async def main():
    print("=" * 70)
    print("  Amazon 产品深度分析工具（含真实 BSR/销量估算）")
    print("=" * 70)

    args = parse_args()
    keyword = get_keyword(args)

    # api 是 rainforest 的别名，方便命令行使用
    source = args.source if args.source != "api" else "rainforest"

    print(f"\n关键词：{keyword}")
    print(f"数据源：{source} | 详情产品数：{args.limit}")
    print("-" * 70)

    server = AmazonMCPServer(
        rainforest_api_key=os.getenv("RAINFOREST_API_KEY"),
        pa_api_key=os.getenv("AMAZON_PA_API_KEY"),
        pa_api_secret=os.getenv("AMAZON_PA_API_SECRET"),
        pa_partner_tag=os.getenv("AMAZON_PARTNER_TAG"),
        default_source=source,
    )

    try:
        result = await analyze_keyword(server, keyword, source, args.limit)

        print("\n" + "=" * 70)
        print("  分析结果汇总")
        print("=" * 70)
        print(f"  数据质量：{result['data_quality']}")
        print(f"  分析产品数：{result['analyzed_count']}")
        print(f"  平均价格：${result['avg_price']}")
        print(f"  平均评分：{result['avg_rating']}")
        print(f"  平均评论数：{int(result['avg_reviews'])}")
        print(f"  最小 BSR：{result['min_bsr']}")
        print(f"  平均估算月销量：{result['avg_estimated_monthly_sales']}")
        print("=" * 70)

        # 保存结果
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"amazon_analysis_{timestamp}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 详细报告已保存：{output_path}")

    finally:
        await server.close()


if __name__ == "__main__":
    asyncio.run(main())
