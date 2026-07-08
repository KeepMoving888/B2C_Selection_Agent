#!/usr/bin/env python3
"""生成三模型（Base / Merged / AWQ）垂直领域偏好对对比图表。"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

# 设置中文字体，避免图表标题乱码
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False


def main():
    result_file = Path("output/qwen2.5-7b-orpo-ecommerce-v1/model_comparison_results.json")
    report_dir = Path("E:/models/qwen2.5-7b-ecommerce-awq-v3/report")
    report_dir.mkdir(parents=True, exist_ok=True)

    with open(result_file, "r", encoding="utf-8") as f:
        results = json.load(f)

    models = ["Base", "Merged FP16", "AWQ INT4"]
    margins = [
        results["base"]["avg_margin"],
        results["merged"]["avg_margin"],
        results["quantized"]["avg_margin"],
    ]
    accuracies = [
        results["base"]["accuracy"] * 100,
        results["merged"]["accuracy"] * 100,
        results["quantized"]["accuracy"] * 100,
    ]

    # Margin chart
    plt.figure(figsize=(8, 5))
    colors = ["#94a3b8", "#3b82f6", "#16a34a"]
    bars = plt.bar(models, margins, color=colors)
    plt.ylabel("Average Margin (rejected NLL - chosen NLL)", fontsize=11)
    plt.title("垂直领域偏好对 Average Margin 对比（越大越好）", fontsize=13, fontweight="bold")
    for bar, val in zip(bars, margins):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{val:.4f}",
            ha="center",
            va="bottom",
            fontsize=11,
        )
    plt.tight_layout()
    plt.savefig(report_dir / "04_preference_margin_comparison.png", dpi=150)
    plt.close()

    # Accuracy chart
    plt.figure(figsize=(8, 5))
    bars = plt.bar(models, accuracies, color=colors)
    plt.ylabel("Accuracy (%)", fontsize=11)
    plt.ylim(0, 105)
    plt.title("垂直领域偏好对 Accuracy 对比", fontsize=13, fontweight="bold")
    for bar, val in zip(bars, accuracies):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{val:.1f}%",
            ha="center",
            va="bottom",
            fontsize=11,
        )
    plt.tight_layout()
    plt.savefig(report_dir / "05_preference_accuracy_comparison.png", dpi=150)
    plt.close()

    print(f"[INFO] 对比图表已保存到 {report_dir}")


if __name__ == "__main__":
    main()
