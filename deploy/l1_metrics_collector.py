#!/usr/bin/env python3
"""
deploy/l1_metrics_collector.py
=============================
L1 业务指标采集器。

在飞书审批结果回写、ERP 销售数据同步等节点调用，
计算并上报核心选品业务指标：
  - selection_adoption_rate     系统推荐采纳率
  - first_month_success_rate    首月成功率
  - cost_per_selection          单选品决策成本
  - avg_inference_latency_p95   推理服务 P95 延迟
  - daily_throughput            日处理选品请求数

输出：
  - output/l1_metrics/l1_metrics_YYYYMMDD.jsonl
  - 可对接飞书 Base（需配置 FEISHU_APP_ID / FEISHU_APP_SECRET / FEISHU_BASE_ID）
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

OUTPUT_DIR = Path("output/l1_metrics")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class L1MetricsCollector:
    """采集 L1 业务指标，支持本地落盘与飞书 Base 回写。"""

    def __init__(
        self,
        feishu_base_id: Optional[str] = None,
        feishu_table_id: Optional[str] = None,
    ):
        self.feishu_base_id = feishu_base_id or os.getenv("FEISHU_BASE_ID")
        self.feishu_table_id = feishu_table_id or os.getenv("FEISHU_L1_TABLE_ID")
        self.records: list[dict] = []

    @staticmethod
    def calculate(
        report_id: str,
        total_recommended: int,
        adopted: int,
        first_month_hit: int,
        total_cost_cny: float,
        p95_latency_s: float,
        daily_throughput: int,
        date: Optional[str] = None,
    ) -> dict:
        """计算单条 L1 指标记录。"""
        adoption_rate = adopted / total_recommended if total_recommended > 0 else 0.0
        success_rate = first_month_hit / adopted if adopted > 0 else 0.0
        cost_per = total_cost_cny / total_recommended if total_recommended > 0 else 0.0

        record = {
            "report_id": report_id,
            "date": date or datetime.now().strftime("%Y-%m-%d"),
            "selection_adoption_rate": round(adoption_rate, 4),
            "first_month_success_rate": round(success_rate, 4),
            "cost_per_selection": round(cost_per, 4),
            "avg_inference_latency_p95": round(p95_latency_s, 3),
            "daily_throughput": daily_throughput,
            "raw": {
                "total_recommended": total_recommended,
                "adopted": adopted,
                "first_month_hit": first_month_hit,
                "total_cost_cny": total_cost_cny,
            },
            "created_at": int(time.time()),
        }
        return record

    def append(self, record: dict) -> None:
        """追加一条记录到内存队列。"""
        self.records.append(record)

    def save_local(self) -> Path:
        """将当前记录落盘到 output/l1_metrics/。"""
        date_str = datetime.now().strftime("%Y%m%d")
        path = OUTPUT_DIR / f"l1_metrics_{date_str}.jsonl"
        with open(path, "a", encoding="utf-8") as f:
            for rec in self.records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self.records = []
        return path

    def to_feishu_record(self, record: dict) -> dict:
        """把指标记录转成飞书 Base 字段格式。"""
        return {
            "报告编号": {"text": record["report_id"]},
            "日期": {"text": record["date"]},
            "选品采纳率": record["selection_adoption_rate"],
            "首月成功率": record["first_month_success_rate"],
            "单选品成本": record["cost_per_selection"],
            "P95延迟": record["avg_inference_latency_p95"],
            "日处理量": record["daily_throughput"],
        }

    def push_to_feishu(self) -> Optional[dict]:
        """推送当前记录到飞书 Base（占位实现，需接入 lark-base skill）。"""
        if not self.feishu_base_id or not self.feishu_table_id:
            print("[L1Metrics] Skip Feishu push: base_id or table_id not configured.")
            return None

        # 实际接入时调用 lark-base append_records：
        # from lark_base import append_records
        # append_records(self.feishu_base_id, self.feishu_table_id,
        #                [self.to_feishu_record(r) for r in self.records])
        print(f"[L1Metrics] Would push {len(self.records)} records to Feishu Base.")
        return {"pushed": len(self.records)}


def demo():
    """示例：模拟一次飞书审批回写后的指标采集。"""
    collector = L1MetricsCollector()

    # 模拟某日数据
    record = collector.calculate(
        report_id="RPT20260708001",
        total_recommended=100,
        adopted=42,
        first_month_hit=28,
        total_cost_cny=86.4,  # API + 人工审核成本
        p95_latency_s=8.948,
        daily_throughput=1250,
    )
    collector.append(record)

    path = collector.save_local()
    print(f"[L1Metrics] Saved to {path}")
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    demo()
