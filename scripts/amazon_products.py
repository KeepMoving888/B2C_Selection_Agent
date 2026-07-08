# ============================================================
# scripts/amazon_products.py — Amazon 竞品数据采集工具
#
# 用途：
#   1. 根据关键词获取 Amazon 真实产品数据
#   2. 将结果转换为飞书 Base 可同步的结构化记录
#   3. 与 Google Trends 数据结合，形成选品市场维度分析
#
# 运行：
#   python scripts/amazon_products.py "dog chew toys"                  # 默认 Rainforest
#   python scripts/amazon_products.py "dog chew toys" --source mock    # 使用 Mock
#   python scripts/amazon_products.py "dog chew toys" --source pa_api  # 使用 Amazon 官方 API
#   python scripts/amazon_products.py                                  # 交互式输入
#
# 环境变量：
#   RAINFOREST_API_KEY=your_rainforest_api_key
#   AMAZON_PA_API_KEY=your-pa-api-key
#   AMAZON_PA_API_SECRET=your-pa-api-secret
#   AMAZON_PARTNER_TAG=your-partner-tag
# ============================================================

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List

# 将项目根目录加入模块搜索路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 自动加载 .env 环境变量（如果存在）
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from mcp_servers.amazon_server import AmazonMCPServer


OUTPUT_DIR = PROJECT_ROOT / "output"


def parse_args() -> argparse.Namespace:
    """解析命令行参数：关键词 + 数据源选择。"""
    parser = argparse.ArgumentParser(
        description="Amazon 竞品数据采集工具（支持 Rainforest / PA API / Mock 多数据源）"
    )
    parser.add_argument(
        "keyword",
        nargs="?",
        default=None,
        help='搜索关键词，例如 "dog chew toys"',
    )
    parser.add_argument(
        "--source",
        choices=["rainforest", "pa_api", "mock"],
        default="rainforest",
        help="数据源：rainforest（默认，免费试用） | pa_api（生产官方 API） | mock（兜底）",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="返回产品数量（最大 20，默认 10）",
    )
    return parser.parse_args()


def get_keyword(args: argparse.Namespace) -> str:
    """从命令行参数或交互式输入获取关键词。"""
    if args.keyword:
        return args.keyword.strip()

    print("请输入要搜索的 Amazon 产品关键词：")
    print("  示例：dog chew toys")
    user_input = input("> ").strip()
    if not user_input:
        print("未输入关键词，使用默认示例。")
        return "dog chew toys"
    return user_input


def to_feishu_record(search_result: dict) -> dict:
    """将 Amazon 搜索结果转换为飞书 Base 可同步的结构化记录。"""
    products = search_result.get("results", [])

    # 计算市场统计（兼容 None 值）
    prices = [p.get("price") for p in products if p.get("price") is not None and p.get("price") > 0]
    ratings = [p.get("rating") for p in products if p.get("rating") is not None]
    reviews = [p.get("review_count") for p in products if p.get("review_count") is not None and p.get("review_count") > 0]
    bsrs = [p.get("bsr") for p in products if p.get("bsr") is not None and p.get("bsr") > 0]

    avg_price = round(sum(prices) / len(prices), 2) if prices else 0
    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0
    avg_reviews = round(sum(reviews) / len(reviews), 0) if reviews else 0

    # 取 Top 3 产品
    top_products = products[:3]

    return {
        "record_id": f"amazon_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "source": f"Amazon ({search_result.get('source', 'unknown')})",
        "keyword": search_result.get("keyword", ""),
        "market": search_result.get("market", "com"),
        "total_results": search_result.get("total_results", 0),
        "returned_count": search_result.get("returned_count", 0),
        "data_quality": search_result.get("data_quality", ""),
        "avg_price": avg_price,
        "avg_rating": avg_rating,
        "avg_reviews": int(avg_reviews),
        "min_bsr": min(bsrs) if bsrs else None,
        "top_products": top_products,
        "created_at": datetime.now().isoformat(),
    }


async def main():
    print("=" * 70)
    print("  Amazon 竞品数据采集工具（多数据源）")
    print("=" * 70)

    args = parse_args()
    keyword = get_keyword(args)
    print(f"\n关键词：{keyword}")
    print(f"数据源：{args.source} | 市场：com | 返回数量：{args.limit}")
    print("-" * 70)

    if args.source == "rainforest" and not os.getenv("RAINFOREST_API_KEY"):
        print("⚠️  未设置 RAINFOREST_API_KEY 环境变量，将回退到离线品类画像数据。")
        print("    如需在线数据，请先设置：$env:RAINFOREST_API_KEY='your_key'")
        print()

    server = AmazonMCPServer(
        rainforest_api_key=os.getenv("RAINFOREST_API_KEY"),
        pa_api_key=os.getenv("AMAZON_PA_API_KEY"),
        pa_api_secret=os.getenv("AMAZON_PA_API_SECRET"),
        pa_partner_tag=os.getenv("AMAZON_PARTNER_TAG"),
        default_source=args.source,
    )
    response = await server.call_tool(
        "amazon_product_search",
        {
            "keyword": keyword,
            "market": "com",
            "limit": args.limit,
            "source": args.source,
        },
    )

    result = response.get("result", response)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 转换为飞书 Base 记录格式并保存
    feishu_record = to_feishu_record(result)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"amazon_{timestamp}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(feishu_record, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print(f"  数据质量：{result.get('data_quality', 'unknown')}")
    print(f"  飞书记录已保存：{output_path}")
    print("=" * 70)

    # 关闭 HTTP session，避免资源泄漏
    await server.close()


if __name__ == "__main__":
    asyncio.run(main())
