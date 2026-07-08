# ============================================================
# scripts/amazon_review_analysis.py — Amazon 评论分析工具
#
# 用途：
#   1. 根据 ASIN 获取 Amazon 产品评论
#   2. 分析评论情感、痛点、优点、功能提及
#   3. 输出产品迭代建议和飞书 Base 可同步记录
#
# 运行：
#   python scripts/amazon_review_analysis.py "B07F45GGPT"
#   python scripts/amazon_review_analysis.py "B0DLRH694Y" --max-reviews 50
# ============================================================

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

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
        description="Amazon 评论分析工具（提取用户痛点、优点、迭代建议）"
    )
    parser.add_argument(
        "asin",
        nargs="?",
        default=None,
        help='Amazon ASIN，例如 "B07F45GGPT"',
    )
    parser.add_argument(
        "--source",
        choices=["rainforest", "pa_api", "mock"],
        default="rainforest",
        help="数据源：rainforest（默认） | pa_api | mock",
    )
    parser.add_argument(
        "--max-reviews",
        type=int,
        default=100,
        help="分析评论数量（默认 100，最大 200）",
    )
    return parser.parse_args()


def get_asin(args: argparse.Namespace) -> str:
    if args.asin:
        return args.asin.strip().upper()
    user_input = input('请输入 Amazon ASIN（例如：B07F45GGPT）：').strip().upper()
    if not user_input:
        print("未输入 ASIN，使用默认示例。")
        return "B07F45GGPT"
    return user_input


def to_feishu_record(analysis: dict) -> dict:
    """将评论分析结果转换为飞书 Base 可同步的结构化记录。"""
    return {
        "record_id": f"review_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "source": f"Amazon Review ({analysis.get('source', 'unknown')})",
        "asin": analysis.get("asin", ""),
        "market": analysis.get("market", "com"),
        "total_reviews_analyzed": analysis.get("total_reviews_analyzed", 0),
        "data_quality": analysis.get("data_quality", ""),
        "positive_count": analysis.get("sentiment_summary", {}).get("positive", 0),
        "neutral_count": analysis.get("sentiment_summary", {}).get("neutral", 0),
        "negative_count": analysis.get("sentiment_summary", {}).get("negative", 0),
        "top_pain_points": [
            f"{p['issue']} ({p['mention_count']}次)"
            for p in analysis.get("top_pain_points", [])
        ],
        "top_praised_features": [
            f"{f['feature']} ({f['mention_count']}次)"
            for f in analysis.get("top_praised_features", [])
        ],
        "iteration_suggestions": analysis.get("iteration_suggestions", []),
        "raw_analysis": analysis,
        "created_at": datetime.now().isoformat(),
    }


async def main():
    print("=" * 70)
    print("  Amazon 评论分析工具")
    print("=" * 70)

    args = parse_args()
    asin = get_asin(args)

    print(f"\nASIN：{asin}")
    print(f"数据源：{args.source} | 最大评论数：{args.max_reviews}")
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

    try:
        response = await server.call_tool(
            "amazon_review_analysis",
            {
                "asin": asin,
                "market": "com",
                "max_reviews": args.max_reviews,
                "source": args.source,
            },
        )
        result = response.get("result", response)

        print(json.dumps(result, ensure_ascii=False, indent=2))

        # 保存飞书记录
        feishu_record = to_feishu_record(result)

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"review_analysis_{timestamp}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(feishu_record, f, ensure_ascii=False, indent=2)

        print("\n" + "=" * 70)
        print(f"  数据质量：{result.get('data_quality', 'unknown')}")
        print(f"  飞书记录已保存：{output_path}")
        print("=" * 70)

    finally:
        await server.close()


if __name__ == "__main__":
    asyncio.run(main())
