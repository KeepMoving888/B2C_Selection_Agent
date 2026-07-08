#!/usr/bin/env python3
"""
deploy/generate_report_generation_comparison.py
===============================================
汇总 AWQ 实测报告生成时间与基于历史 awq_metrics.json 估算的 FP16 时间，
生成对比图表与 Markdown 报告。

输入：
  - output/report_generation_benchmark/awq_report_results.json
  - models/qwen2.5-7b-ecommerce-awq-v3/report/awq_metrics.json

输出：
  - output/report_generation_benchmark/01_report_latency_comparison.png
  - output/report_generation_benchmark/02_report_speed_comparison.png
  - output/report_generation_benchmark/03_report_tokens_comparison.png
  - output/report_generation_benchmark/report_generation_comparison.md
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUTPUT_DIR = Path("output/report_generation_benchmark")
AWQ_RESULT = OUTPUT_DIR / "awq_report_results.json"
AWQ_METRICS = Path("/mnt/e/models/qwen2.5-7b-ecommerce-awq-v3/report/awq_metrics.json")


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    awq = load_json(AWQ_RESULT)
    metrics = load_json(AWQ_METRICS)

    awq_lat = awq["summary"]["avg_latency_s"]
    awq_speed = awq["summary"]["avg_tokens_per_sec"]
    awq_tokens = awq["summary"]["avg_completion_tokens"]

    # 基于历史简单推理延迟比例，估算 FP16 merged 完整报告生成时间
    merged_simple_lat = metrics["merged_latency_s"]
    awq_simple_lat = metrics["awq_latency_s"]
    ratio = merged_simple_lat / awq_simple_lat

    estimated_merged_lat = awq_lat * ratio
    estimated_merged_speed = awq_speed / ratio
    estimated_merged_tokens = awq_tokens  # 相同 prompt 下生成长度应相近

    # 1. 报告生成延迟对比
    categories = ["Merged FP16\n(estimated)", "AWQ INT4\n(measured)"]
    latencies = [estimated_merged_lat, awq_lat]

    plt.figure(figsize=(7, 5))
    bars = plt.bar(categories, latencies, color=["#3b82f6", "#16a34a"])
    for bar, val in zip(bars, latencies):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{val:.2f}s", ha="center", va="bottom", fontsize=12)
    plt.ylabel("Avg Report Generation Latency (s)", fontsize=12)
    plt.title("Full Product Selection Report: FP16 vs AWQ", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "01_report_latency_comparison.png", dpi=150)
    plt.close()

    # 2. 生成速度对比
    speeds = [estimated_merged_speed, awq_speed]
    plt.figure(figsize=(7, 5))
    bars = plt.bar(categories, speeds, color=["#3b82f6", "#16a34a"])
    for bar, val in zip(bars, speeds):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{val:.1f} tokens/s", ha="center", va="bottom", fontsize=12)
    plt.ylabel("Avg Generation Speed (tokens/s)", fontsize=12)
    plt.title("Report Generation Speed: FP16 vs AWQ", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "02_report_speed_comparison.png", dpi=150)
    plt.close()

    # 3. 平均生成 token 数
    tokens = [estimated_merged_tokens, awq_tokens]
    plt.figure(figsize=(7, 5))
    bars = plt.bar(categories, tokens, color=["#3b82f6", "#16a34a"])
    for bar, val in zip(bars, tokens):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{val:.0f} tokens", ha="center", va="bottom", fontsize=12)
    plt.ylabel("Avg Completion Tokens", fontsize=12)
    plt.title("Report Output Length: FP16 vs AWQ", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "03_report_tokens_comparison.png", dpi=150)
    plt.close()

    # 4. Markdown 报告
    report = f"""# 选品分析报告生成时间对比

## 1. 测试说明

- **AWQ INT4**：在 WSL2 + vLLM 0.7.3 上实测，使用 5 个真实选品 prompts，每个 prompt 重复 3 次，`max_tokens=1024`。
- **Merged FP16**：当前 E:\\models\\qwen2.5-7b-ecommerce-merged 的 safetensors 文件不完整，无法直接加载。FP16 数据为基于历史 `awq_metrics.json` 中简单推理延迟比例的估算值：
  - Merged 简单推理延迟: {merged_simple_lat:.3f}s
  - AWQ 简单推理延迟: {awq_simple_lat:.3f}s
  - 估算比例: {ratio:.2f}x

## 2. 核心对比

| Metric | Merged FP16 (estimated) | AWQ INT4 (measured) | Improvement |
|--------|-------------------------|---------------------|-------------|
| Avg Report Generation Latency | {estimated_merged_lat:.2f} s | {awq_lat:.2f} s | {ratio:.2f}x faster |
| Avg Generation Speed | {estimated_merged_speed:.1f} tokens/s | {awq_speed:.1f} tokens/s | {ratio:.2f}x faster |
| Avg Completion Tokens | {estimated_merged_tokens:.0f} tokens | {awq_tokens:.0f} tokens | similar |
| Success Rate | 100% (assumed) | 100% | - |

## 3. 实测 AWQ 细节

| Prompt | Avg Latency | Avg Tokens | Avg Speed |
|--------|-------------|------------|-----------|
"""
    for pr in awq["prompt_results"]:
        report += f"| {pr['prompt']} | {pr['avg_latency_s']:.2f}s | {pr['avg_completion_tokens']:.0f} | {pr['avg_tokens_per_sec']:.1f} tokens/s |\n"

    report += f"""

## 4. 对比图

![Report Latency](01_report_latency_comparison.png)

![Report Speed](02_report_speed_comparison.png)

![Report Tokens](03_report_tokens_comparison.png)

## 5. 结论

- **AWQ INT4 实测生成一份完整选品分析报告平均约 {awq_lat:.2f}s**，生成速度约 {awq_speed:.1f} tokens/s。
- **估算 Merged FP16 生成同一份报告平均约 {estimated_merged_lat:.2f}s**，AWQ 约快 **{ratio:.2f} 倍**。
- 实际 FP16 完整报告生成时间需要等 E:\\models\\qwen2.5-7b-ecommerce-merged 文件完整迁移后重新实测。
"""

    with open(OUTPUT_DIR / "report_generation_comparison.md", "w", encoding="utf-8") as f:
        f.write(report)

    print("[Report] Saved comparison charts and report to output/report_generation_benchmark/")


if __name__ == "__main__":
    main()
