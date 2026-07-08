# ============================================================
# scripts/google_trends.py — Google Trends 选品数据采集工具
#
# 用途：
#   1. 根据自定义关键词获取真实 Google Trends 趋势数据
#   2. 将结果转换为飞书 Base 可同步的结构化记录
#   3. 保存原始结果到 output/ 目录，供后续 Agent 流程使用
#
# 运行：
#   python scripts/google_trends.py "dog chew toys, cat toys"
#   python scripts/google_trends.py                    # 交互式输入
#
# 关键词分隔符：英文逗号 , 或分号 ;
# ============================================================

import asyncio
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List

# 将项目根目录加入模块搜索路径，确保能导入 mcp_servers
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 自动加载 .env 环境变量（如果存在）
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from mcp_servers.social_server import SocialMediaMCPServer


OUTPUT_DIR = PROJECT_ROOT / "output"


def parse_keywords() -> List[str]:
    """从命令行参数或交互式输入获取关键词，支持逗号/分号分隔。"""
    raw_input = ""

    if len(sys.argv) > 1:
        raw_input = " ".join(sys.argv[1:])
    else:
        print("请输入要分析的选品关键词（用英文逗号或分号分隔）：")
        print("  示例：dog chew toys, cat toys, pet water fountain")
        raw_input = input("> ").strip()

    if not raw_input:
        print("未输入关键词，使用默认示例。")
        return ["dog chew toys", "cat toys"]

    # 按逗号或分号分隔，并去除前后空白
    keywords = [kw.strip() for kw in re.split(r"[,;]", raw_input) if kw.strip()]

    if not keywords:
        print("未解析到有效关键词，使用默认示例。")
        return ["dog chew toys", "cat toys"]

    return keywords


def to_feishu_record(trend_result: dict) -> dict:
    """将趋势数据转换为飞书 Base 可同步的结构化记录。"""
    keywords = trend_result.get("keywords", [])
    interest = trend_result.get("interest_over_time", {})

    # 提取主关键词的指标（兼容在线数据按 keyword 分组和离线扁平结构两种格式）
    primary_kw = keywords[0] if keywords else ""
    primary_metrics = interest.get(primary_kw, {})

    # 离线扁平结构直接取顶层字段
    if not primary_metrics and interest:
        primary_metrics = {
            "current_value": interest.get("current_value", 0),
            "period_high": interest.get("12m_high", 0),
            "period_low": interest.get("12m_low", 0),
            "yoy_change_pct": interest.get("yoy_change_pct", 0),
        }

    return {
        "record_id": f"trends_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "source": "Google Trends (pytrends)",
        "keywords": " | ".join(keywords),
        "region": trend_result.get("region", "US"),
        "timeframe": trend_result.get("timeframe", ""),
        "data_quality": trend_result.get("data_quality", ""),
        "trend_direction": trend_result.get("trend_direction", ""),
        "confidence": trend_result.get("confidence", 0),
        "primary_keyword": primary_kw,
        "current_interest": primary_metrics.get("current_value", 0),
        "period_high": primary_metrics.get("period_high", 0),
        "period_low": primary_metrics.get("period_low", 0),
        "yoy_change_pct": primary_metrics.get("yoy_change_pct", 0),
        "top_region": (
            trend_result["regional_breakdown"][0]["region"]
            if trend_result.get("regional_breakdown")
            else ""
        ),
        "rising_queries": ", ".join(trend_result.get("related_queries_rising", [])[:3]),
        "raw_result": trend_result,
        "created_at": datetime.now().isoformat(),
    }


async def main():
    print("=" * 70)
    print("  Google Trends 选品数据采集工具")
    print("=" * 70)

    keywords = parse_keywords()
    print(f"\n解析后的关键词：{keywords}")
    print("地区：US | 时间范围：today 12-m")
    print("-" * 70)

    server = SocialMediaMCPServer()
    response = await server.call_tool(
        "google_trends_fetch",
        {
            "keywords": keywords,
            "region": "US",
            "timeframe": "today 12-m",
        },
    )

    result = response.get("result", response)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 转换为飞书 Base 记录格式并保存
    feishu_record = to_feishu_record(result)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = OUTPUT_DIR / f"trends_{timestamp}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(feishu_record, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print(f"  数据质量：{result.get('data_quality', 'unknown')}")
    print(f"  飞书记录已保存：{output_path}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
