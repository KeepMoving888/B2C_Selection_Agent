# ============================================================
# scripts/publish_to_feishu.py — 一键发布选品报告到飞书
#
# 用途：
#   1. 读取 JSON 选品报告
#   2. 生成简洁商务版飞书文档（归档到知识库）
#   3. 将核心指标写入 Base 多维表
#   4. 上传 JSON 报告作为附件
#
# 运行：
#   python scripts/publish_to_feishu.py output/full_pipeline_report_xxx.json
# ============================================================

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from feishu.integration import FeishuConfig, FeishuIntegration


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="发布选品报告到飞书（文档 + 多维表 + 附件）")
    parser.add_argument("report_json", help="选品报告 JSON 文件路径")
    parser.add_argument(
        "--no-attachment", action="store_true",
        help="不上传 JSON 附件",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    report_path = Path(args.report_json)
    if not report_path.exists():
        print(f"❌ 报告文件不存在: {report_path}")
        sys.exit(1)

    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    config = FeishuConfig()
    feishu = FeishuIntegration(config)

    print("=" * 60)
    print("发布选品报告到飞书")
    print("=" * 60)

    result = feishu.publish_selection_report(
        report,
        json_path=str(report_path) if not args.no_attachment else None,
    )

    print("\n✅ 发布成功")
    print(f"   飞书文档：{result['doc_url']}")
    print(f"   多维表记录：{result['record_url']}")
    print(f"   record_id：{result['record_id']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
